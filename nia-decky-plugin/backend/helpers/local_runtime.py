"""Managed, low-priority llama.cpp runtime for SteamOS/Decky."""
from __future__ import annotations

import asyncio
import hashlib
import os
import platform
import secrets
import shutil
import socket
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, Tuple
from urllib.request import Request, urlopen


# Pinned upstream assets. Both digests are published by their upstream projects.
LLAMA_VERSION = "b11559"
LLAMA_URL = (
    "https://github.com/ggml-org/llama.cpp/releases/download/b11559/"
    "llama-b11559-bin-ubuntu-x64.tar.gz"
)
LLAMA_SHA256 = "a454867b975dec288f731c6d3589f132b0e356f7dbad8d711f48d231ee67d7d9"
MODEL_REVISION = "a615a81362316d7b9f5a7a9c4313adfdf9b54588"
MODEL_FILE = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/"
    + MODEL_REVISION + "/" + MODEL_FILE
)
MODEL_SHA256 = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
MODEL_MIN_BYTES = 1_000_000_000
MODEL_MAX_BYTES = 1_300_000_000
ARCHIVE_MAX_BYTES = 40_000_000


class DownloadCancelled(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract_tar(archive_path: Path, destination: Path) -> None:
    """Extract only regular files, directories and contained relative symlinks."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        symlinks = []
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("El archivo del motor contiene una ruta no segura")
            target = destination.joinpath(*relative.parts)
            resolved = target.resolve(strict=False)
            if resolved != destination and destination not in resolved.parents:
                raise ValueError("El archivo del motor intenta salir de su carpeta")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError("No se pudo leer un archivo del motor")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                os.chmod(target, member.mode & 0o755)
            elif member.issym():
                link = PurePosixPath(member.linkname)
                if link.is_absolute() or ".." in link.parts:
                    raise ValueError("El archivo del motor contiene un enlace no seguro")
                symlinks.append((target, member.linkname))
            else:
                raise ValueError("El archivo del motor contiene un tipo de archivo no admitido")
        for target, link_name in symlinks:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(link_name, target)


class LocalRuntime:
    """Downloads pinned upstream assets and owns one loopback llama-server."""

    def __init__(self, data_dir: Path, logger: Any = None) -> None:
        self.root = Path(data_dir) / "llm"
        self.engine_dir = self.root / ("llama.cpp-" + LLAMA_VERSION)
        self.model_dir = self.root / "models"
        self.model_path = self.model_dir / MODEL_FILE
        self.logger = logger
        self._state_lock = threading.RLock()
        self._server_lock = threading.Lock()
        self._install_cancel = threading.Event()
        self._install_task: Optional[asyncio.Task] = None
        self._install_state: Dict[str, Any] = {
            "installing": False, "progress": 0, "message": "Motor local sin instalar", "error": "",
        }
        self._process: Optional[subprocess.Popen] = None
        self._log_handle: Any = None
        self._endpoint = ""
        self._api_key = ""
        self.root.mkdir(parents=True, exist_ok=True)

    def _server_binary(self) -> Optional[Path]:
        if not self.engine_dir.exists():
            return None
        for candidate in self.engine_dir.rglob("llama-server"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _resolve_model(self, custom_path: str = "") -> Tuple[Optional[Path], str]:
        if str(custom_path or "").strip():
            candidate = Path(os.path.expanduser(str(custom_path).strip()))
            if candidate.is_file() and candidate.suffix.lower() == ".gguf":
                return candidate, "custom"
            return None, "custom"
        marker = self.model_path.with_suffix(self.model_path.suffix + ".sha256")
        try:
            valid = marker.read_text(encoding="ascii").strip() == MODEL_SHA256
        except OSError:
            valid = False
        if valid and self.model_path.is_file():
            return self.model_path, "managed"
        return None, "managed"

    def status(self, custom_model_path: str = "") -> Dict[str, Any]:
        with self._state_lock:
            state = dict(self._install_state)
        model_path, model_source = self._resolve_model(custom_model_path)
        running = bool(self._process and self._process.poll() is None)
        return {
            **state,
            "engine_installed": self._server_binary() is not None,
            "model_installed": model_path is not None,
            "model_source": model_source,
            "model_size_bytes": model_path.stat().st_size if model_path else 0,
            "server_running": running,
            "runtime_version": LLAMA_VERSION,
            "recommended_model": "Qwen2.5 1.5B Instruct · Q4_K_M",
        }

    def _set_state(self, **values: Any) -> None:
        with self._state_lock:
            self._install_state.update(values)

    async def begin_install(self, custom_model_path: str = "") -> Dict[str, Any]:
        task = self._install_task
        if task is not None and not task.done():
            return self.status(custom_model_path)
        self._install_cancel.clear()
        self._set_state(installing=True, progress=0, error="", message="Preparando instalación…")
        self._install_task = asyncio.create_task(
            asyncio.to_thread(self._install_sync, str(custom_model_path or ""))
        )
        return self.status(custom_model_path)

    def _install_sync(self, custom_model_path: str) -> None:
        try:
            if platform.machine().lower() not in {"x86_64", "amd64"}:
                raise RuntimeError("El motor incluido está preparado para Steam Deck x86_64")
            self.root.mkdir(parents=True, exist_ok=True)
            if self._server_binary() is None:
                self._set_state(progress=2, message="Descargando llama.cpp verificado…")
                archive_part = self.root / "llama.cpp.tar.gz.part"
                self._download_verified(
                    LLAMA_URL, archive_part, LLAMA_SHA256, ARCHIVE_MAX_BYTES,
                    "Motor", 2, 10,
                )
                if self._install_cancel.is_set():
                    raise DownloadCancelled()
                staging = Path(tempfile.mkdtemp(prefix="llama-stage-", dir=str(self.root)))
                try:
                    self._set_state(progress=10, message="Verificando y preparando el motor…")
                    safe_extract_tar(archive_part, staging)
                    server = next((p for p in staging.rglob("llama-server") if p.is_file()), None)
                    if server is None:
                        raise RuntimeError("El paquete no contiene llama-server")
                    os.chmod(server, server.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
                    relative = server.relative_to(staging)
                    if self.engine_dir.exists():
                        shutil.rmtree(self.engine_dir)
                    os.replace(staging, self.engine_dir)
                    installed_server = self.engine_dir / relative
                    os.chmod(installed_server, installed_server.stat().st_mode | stat.S_IXUSR)
                finally:
                    if staging.exists():
                        shutil.rmtree(staging, ignore_errors=True)
                archive_part.unlink(missing_ok=True)

            if custom_model_path:
                model = Path(os.path.expanduser(custom_model_path))
                if not model.is_file() or model.suffix.lower() != ".gguf":
                    raise RuntimeError("La ruta configurada no apunta a un modelo GGUF existente")
            else:
                model, _ = self._resolve_model()
                if model is None:
                    self.model_dir.mkdir(parents=True, exist_ok=True)
                    self._set_state(progress=12, message="Descargando Qwen 1.5B Q4_K_M (aprox. 1,12 GB)…")
                    model_part = self.model_path.with_suffix(self.model_path.suffix + ".part")
                    self._download_verified(
                        MODEL_URL, model_part,
                        MODEL_SHA256, MODEL_MAX_BYTES, "Modelo", 12, 99,
                        min_bytes=MODEL_MIN_BYTES,
                    )
                    os.replace(model_part, self.model_path)
                    marker = self.model_path.with_suffix(self.model_path.suffix + ".sha256")
                    marker.write_text(MODEL_SHA256 + "\n", encoding="ascii")
                    os.chmod(marker, 0o600)
            self._set_state(installing=False, progress=100, error="", message="Motor y modelo local listos")
        except DownloadCancelled:
            self._set_state(installing=False, message="Instalación pausada; se conserva lo descargado para reanudarla")
        except Exception as exc:
            self._set_state(installing=False, error=str(exc)[:240], message="No se pudo completar la instalación")

    def _download_verified(
        self, url: str, partial_path: Path, expected_sha256: str, max_bytes: int,
        label: str, progress_start: int, progress_end: int, min_bytes: int = 1,
    ) -> None:
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        offset = partial_path.stat().st_size if partial_path.exists() else 0
        if offset > max_bytes:
            partial_path.unlink(missing_ok=True)
            offset = 0
        elif offset >= min_bytes and offset and sha256_file(partial_path).lower() == expected_sha256.lower():
            self._set_state(progress=progress_end, message=label + " descargado y verificado")
            return
        headers = {"User-Agent": "NIA-Decky/0.3", "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = "bytes=" + str(offset) + "-"
        request = Request(url, headers=headers)
        try:
            response_context = urlopen(request, timeout=30)
        except Exception as exc:
            # A server can reject a stale byte range with 416. Discard that
            # partial file once and start cleanly; ordinary network failures
            # still preserve it for the next retry.
            if offset and getattr(exc, "code", None) == 416:
                partial_path.unlink(missing_ok=True)
                return self._download_verified(
                    url, partial_path, expected_sha256, max_bytes, label,
                    progress_start, progress_end, min_bytes,
                )
            raise
        with response_context as response:
            status = int(getattr(response, "status", response.getcode()) or 200)
            append = offset > 0 and status == 206
            if not append:
                offset = 0
            total = int(response.headers.get("Content-Length") or 0) + offset
            if total > max_bytes:
                raise RuntimeError(label + " excede el límite de descarga configurado")
            digest = hashlib.sha256()
            if append:
                with partial_path.open("rb") as existing:
                    for previous in iter(lambda: existing.read(1024 * 1024), b""):
                        digest.update(previous)
            mode = "ab" if append else "wb"
            downloaded = offset
            with partial_path.open(mode) as output:
                while True:
                    if self._install_cancel.is_set():
                        raise DownloadCancelled()
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise RuntimeError(label + " excede el límite de descarga configurado")
                    output.write(chunk)
                    digest.update(chunk)
                    if total:
                        ratio = min(1.0, downloaded / total)
                        progress = progress_start + int((progress_end - progress_start) * ratio)
                        self._set_state(
                            progress=progress,
                            message=label + ": " + str(round(downloaded / 1_000_000)) + " / "
                            + str(round(total / 1_000_000)) + " MB",
                        )
                output.flush()
                os.fsync(output.fileno())
        if partial_path.stat().st_size < min_bytes:
            raise RuntimeError(label + " quedó incompleto; revisa la conexión e inténtalo de nuevo")
        if digest.hexdigest().lower() != expected_sha256.lower():
            partial_path.unlink(missing_ok=True)
            raise RuntimeError("La verificación SHA-256 de " + label + " no coincidió")
        if label == "Motor":
            os.chmod(partial_path, 0o600)
    def remove(self) -> Dict[str, Any]:
        task = self._install_task
        if task is not None and not task.done():
            raise RuntimeError("Espera a que termine la instalación antes de eliminar el motor")
        self.stop_server()
        shutil.rmtree(self.engine_dir, ignore_errors=True)
        self.model_path.unlink(missing_ok=True)
        self.model_path.with_suffix(self.model_path.suffix + ".sha256").unlink(missing_ok=True)
        self.model_path.with_suffix(self.model_path.suffix + ".part").unlink(missing_ok=True)
        (self.root / "llama.cpp.tar.gz.part").unlink(missing_ok=True)
        (self.root / "llama-server.log").unlink(missing_ok=True)
        self._set_state(installing=False, progress=0, error="", message="Motor local eliminado")
        return self.status()

    @staticmethod
    def _free_loopback_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def openai_endpoint(self, settings: Dict[str, Any], custom_model_path: str = "") -> Tuple[str, str]:
        """Start/return the private local OpenAI-compatible endpoint."""
        with self._server_lock:
            model_path, _ = self._resolve_model(custom_model_path)
            binary = self._server_binary()
            if model_path is None:
                raise RuntimeError("Instala el motor y modelo local desde Ajustes de NIA")
            if binary is None:
                raise RuntimeError("Falta llama-server; instala el motor local desde Ajustes de NIA")
            if self._process is None or self._process.poll() is not None:
                self._start_server(binary, model_path, settings)
            self._wait_until_ready()
            return self._endpoint + "/v1/chat/completions", self._api_key

    def _start_server(self, binary: Path, model_path: Path, settings: Dict[str, Any]) -> None:
        threads = max(1, min(4, int(settings.get("threads", 2))))
        context = max(1024, min(4096, int(settings.get("context_size", 2048))))
        idle = max(30, min(600, int(settings.get("idle_sleep_seconds", 90))))
        port = self._free_loopback_port()
        self._api_key = secrets.token_urlsafe(24)
        self._endpoint = "http://127.0.0.1:" + str(port)
        command = [
            str(binary), "--model", str(model_path), "--host", "127.0.0.1", "--port", str(port),
            "--ctx-size", str(context), "--threads", str(threads), "--threads-batch", str(threads),
            "--parallel", "1", "--n-gpu-layers", "0", "--sleep-idle-seconds", str(idle),
            "--no-webui", "--api-key", self._api_key,
        ]
        nice = shutil.which("nice")
        if nice:
            command = [nice, "-n", "10"] + command
        log_path = self.root / "llama-server.log"
        self._log_handle = log_path.open("wb")
        try:
            self._process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=self._log_handle, stderr=subprocess.STDOUT,
                close_fds=True, start_new_session=True,
            )
        except Exception:
            self._log_handle.close()
            self._log_handle = None
            raise

    def _wait_until_ready(self) -> None:
        process = self._process
        if process is None:
            raise RuntimeError("No se pudo iniciar llama-server")
        health_url = self._endpoint + "/health"
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("llama-server terminó durante el arranque; revisa el espacio libre y el modelo")
            try:
                with urlopen(Request(health_url, headers={"User-Agent": "NIA-Decky/0.3"}), timeout=2) as response:
                    if int(response.status) == 200:
                        return
            except Exception:
                pass
            time.sleep(0.4)
        raise TimeoutError("llama-server tardó más de 90 segundos en cargar el modelo")

    def stop_server(self) -> None:
        process = self._process
        self._process = None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if self._log_handle:
            try:
                self._log_handle.close()
            except OSError:
                pass
            self._log_handle = None

    def close(self) -> None:
        self._install_cancel.set()
        self.stop_server()
