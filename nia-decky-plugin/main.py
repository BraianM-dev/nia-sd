"""Decky backend for NIA's lightweight game companion."""
from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from backend.helpers.context_store import NiaStore
from backend.helpers.games import find_running_game, scan_installed_games
from backend.helpers.narrator import NiaNarrator
from backend.helpers.local_runtime import LocalRuntime
from backend.helpers.storage import (
    atomic_write_json, ensure_default_config, get_config_path, get_data_dir,
    get_logs_dir, get_saves_dir, list_files_sorted, load_save, write_save,
    delete_save,
)
from backend.helpers import tts

DEFAULTS = {
    "mode": "remote",
    "model": {"gguf_url": "", "path": "", "checksum": "", "ctx": 2048, "temperature": 0.7, "top_p": 0.9},
    "tts": {"enabled": False, "piper_binary": "", "voice_model": "", "path": "", "voice_url": "", "checksum": "", "speed": 1.0, "voice": ""},
    "remote": {"enabled": False, "endpoint": "", "auth": "", "timeout": 8},
    "narrator": {
        "provider": "local-llama", "endpoint": "", "model": "qwen2.5-1.5b-instruct-q4_k_m",
        "api_key": "", "timeout": 8, "max_tokens": 96, "temperature": 0.7,
        "persona": "amable", "auto_on_start": False, "auto_speak": False,
    },
    "game_detection": {"enabled": True, "scan_interval_seconds": 12, "roots": []},
    "local_runtime": {"threads": 2, "context_size": 2048, "idle_sleep_seconds": 90},
    "status": "ready",
}


class Plugin:
    def __init__(self) -> None:
        self.logger = logging.getLogger("nia-decky")
        self.settings: Dict[str, Any] = {}
        self.store: Optional[NiaStore] = None
        self.narrator: Optional[NiaNarrator] = None
        self.local_runtime: Optional[LocalRuntime] = None
        self._tasks: List[asyncio.Task] = []
        self._active_game: Optional[Dict[str, Any]] = None
        self._session_started = time.time()
        self._event_lock = asyncio.Lock()

    async def _main(self) -> None:
        self._setup_logging()
        self.settings = ensure_default_config(DEFAULTS)
        self._migrate_local_ollama_default()
        self.store = NiaStore(get_data_dir() / "nia.sqlite3")
        self.local_runtime = LocalRuntime(get_data_dir(), self.logger)
        self.narrator = NiaNarrator(self._get_settings, self.store, self.local_runtime)
        self.logger.info("NIA Decky listo; no se descargan modelos ni binarios automáticamente")
        self._tasks.append(asyncio.create_task(self._watch_games()))

    def _migrate_local_ollama_default(self) -> None:
        """Move legacy same-Deck Ollama settings to NIA's bundled runtime.

        Keep an explicitly configured Ollama server on another machine. A
        SteamOS local Ollama service commonly is not running in Game Mode.
        """
        narrator = self.settings.get("narrator", {})
        if narrator.get("provider") != "ollama":
            return
        endpoint = str(narrator.get("endpoint", "")).strip()
        hostname = urlsplit(endpoint if "://" in endpoint else "http://" + endpoint).hostname
        if hostname not in {None, "", "localhost", "127.0.0.1", "::1"}:
            return
        narrator["provider"] = "local-llama"
        narrator["endpoint"] = ""
        narrator["model"] = "qwen2.5-1.5b-instruct-q4_k_m"
        atomic_write_json(get_config_path(), self.settings)
        self.logger.info("Ajuste migrado: Ollama local pasa al motor llama.cpp integrado de NIA")

    async def _unload(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self.local_runtime:
            self.local_runtime.close()
        self.logger.info("NIA detenido")

    def _setup_logging(self) -> None:
        try:
            logs_dir = get_logs_dir()
            log_file = logs_dir / "nia.log"
            if not any(isinstance(handler, logging.handlers.RotatingFileHandler) for handler in self.logger.handlers):
                handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3)
                handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
                self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        except OSError:
            logging.basicConfig(level=logging.INFO)

    def _get_settings(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.settings))

    async def settings_get(self) -> Dict[str, Any]:
        return self._get_settings()

    async def settings_set(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(settings, dict):
            raise ValueError("Los ajustes deben ser un objeto")
        self.settings = self._merge_settings(DEFAULTS, settings)
        detection = self.settings.get("game_detection", {})
        detection["scan_interval_seconds"] = max(8, min(60, int(detection.get("scan_interval_seconds", 12))))
        narrator = self.settings.get("narrator", {})
        narrator["timeout"] = max(2, min(60, int(narrator.get("timeout", 8))))
        narrator["max_tokens"] = max(32, min(180, int(narrator.get("max_tokens", 96))))
        if narrator.get("provider") not in {
            "local-llama", "ollama", "openai", "grok", "deepseek", "gemini",
            "openai-compatible", "template",
        }:
            raise ValueError("Proveedor de narración no válido")
        if narrator.get("persona") not in {"amable", "sarcastico", "grosero", "epico"}:
            narrator["persona"] = "amable"
        roots = detection.get("roots", [])
        if not isinstance(roots, list):
            raise ValueError("Las carpetas adicionales deben ser una lista")
        detection["roots"] = [str(path)[:1024] for path in roots[:50] if str(path).strip()]
        local = self.settings.get("local_runtime", {})
        local["threads"] = max(1, min(4, int(local.get("threads", 2))))
        local["context_size"] = max(1024, min(4096, int(local.get("context_size", 2048))))
        local["idle_sleep_seconds"] = max(30, min(600, int(local.get("idle_sleep_seconds", 90))))
        if not detection.get("enabled", True):
            self._active_game = None
        atomic_write_json(get_config_path(), self.settings)
        if narrator.get("provider") != "local-llama" and self.local_runtime:
            self.local_runtime.stop_server()
        return self._get_settings()

    @staticmethod
    def _merge_settings(defaults: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(defaults)
        for key, value in values.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = Plugin._merge_settings(result[key], value)
            else:
                result[key] = value
        return result

    async def list_games(self) -> List[Dict[str, Any]]:
        roots = self.settings.get("game_detection", {}).get("roots", [])
        return await asyncio.to_thread(scan_installed_games, roots)

    async def game_state(self) -> Dict[str, Any]:
        game = self._active_game
        if not game:
            return {"active_game": None, "message": "No se detectó un juego activo", "scanned_at": time.time()}
        stats = self.store.game_stats(game["id"]) if self.store else {}
        latest = self.store.latest_narration(game["id"]) if self.store else None
        return {
            "active_game": game, "stats": stats, "latest_narration": latest,
            "session_minutes": max(0, int((time.time() - self._session_started) / 60)),
            "scanned_at": time.time(),
        }

    async def _watch_games(self) -> None:
        while True:
            try:
                detection = self.settings.get("game_detection", {})
                if detection.get("enabled", True):
                    games = await asyncio.to_thread(scan_installed_games, detection.get("roots", []))
                    current = await asyncio.to_thread(find_running_game, detection.get("roots", []), games)
                    old_id = self._active_game.get("id") if self._active_game else None
                    new_id = current.get("id") if current else None
                    if new_id != old_id:
                        self._active_game = current
                        self._session_started = time.time()
                        if current and self.store:
                            self.logger.info("Juego activo detectado: %s (%s)", current.get("title"), current.get("platform"))
                            if self.settings.get("narrator", {}).get("auto_on_start"):
                                await self._create_narration("session_start", "Inicio de sesión")
                            else:
                                self.store.record_event(current["id"], "session_start", "Juego detectado automáticamente")
                else:
                    self._active_game = None
                await asyncio.sleep(max(8, min(60, int(detection.get("scan_interval_seconds", 12)))))
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("Error durante la detección de juegos")
                await asyncio.sleep(15)

    async def game_event(self, event_type: str, detail: str = "") -> Dict[str, Any]:
        allowed = {"death", "checkpoint", "objective", "victory", "commentary"}
        if event_type not in allowed:
            raise ValueError("Evento no admitido")
        if not self._active_game:
            state = await self.game_state()
            if not state.get("active_game"):
                return {"text": "", "status": "No hay un juego activo"}
        return await self._create_narration(event_type, str(detail or "")[:300])

    async def narrator_generate(self) -> Dict[str, Any]:
        return await self.game_event("commentary", "")

    async def _create_narration(self, event_type: str, detail: str) -> Dict[str, Any]:
        if not self._active_game or not self.store or not self.narrator:
            return {"text": "", "status": "No hay una partida activa"}
        async with self._event_lock:
            game = dict(self._active_game)
            self.store.record_event(game["id"], event_type, detail)
            result = await self.narrator.narrate(
                game, {"type": event_type, "detail": detail}, self._session_started,
            )
            if self.settings.get("narrator", {}).get("auto_speak") and self.settings.get("tts", {}).get("enabled"):
                try:
                    await self.tts_speak(result["text"])
                except Exception as exc:
                    result["status"] = str(result.get("status", "")) + " · Voz: " + str(exc)[:160]
            return result

    async def tts_speak(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        tts_config = self.settings.get("tts", {})
        if not tts_config.get("enabled"):
            raise RuntimeError("Activa Piper en Ajustes para habilitar la voz")
        voice_path = voice or tts_config.get("voice_model") or tts_config.get("path")
        return await tts.synthesize(
            str(text)[:3000], str(voice_path or ""),
            float(tts_config.get("speed", 1.0)), str(tts_config.get("piper_binary", "")),
        )

    async def verify_resources(self) -> Dict[str, Any]:
        details: List[str] = []
        if self.narrator:
            probe = await self.narrator.probe()
            details.append(str(probe["message"]))
        if self.settings.get("narrator", {}).get("provider") == "local-llama" and self.local_runtime:
            runtime = self.local_runtime.status(str(self.settings.get("model", {}).get("path", "")))
            if not runtime["engine_installed"] or not runtime["model_installed"]:
                details.append("Falta instalar el motor/modelo local desde este panel")
        tts_config = self.settings.get("tts", {})
        if not tts_config.get("enabled"):
            details.append("Voz desactivada")
        elif not tts_config.get("voice_model"):
            details.append("Falta seleccionar el modelo Piper")
        else:
            details.append("La voz se validará al reproducir")
        ok = bool(details) and (not details[0].startswith("No se pudo"))
        return {"status": "ok" if ok else "degraded", "details": details}

    async def local_runtime_status(self, model_path: str = "") -> Dict[str, Any]:
        if not self.local_runtime:
            return {"installing": False, "progress": 0, "message": "Motor local no disponible"}
        selected_path = str(model_path or self.settings.get("model", {}).get("path", ""))
        return self.local_runtime.status(selected_path)

    async def local_runtime_install(self, model_path: str = "") -> Dict[str, Any]:
        if not self.local_runtime:
            raise RuntimeError("El gestor del motor local no está inicializado")
        selected_path = str(model_path or self.settings.get("model", {}).get("path", ""))
        return await self.local_runtime.begin_install(selected_path)

    async def local_runtime_remove(self) -> Dict[str, Any]:
        if not self.local_runtime:
            return {"installing": False, "progress": 0, "message": "Motor local no disponible"}
        return self.local_runtime.remove()

    async def story_generate(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        from backend.helpers.storyteller import Storyteller
        storyteller = Storyteller(self._get_settings, self.logger)
        return await storyteller.generate(params or {})

    async def save_list(self) -> List[Dict[str, Any]]:
        saves: List[Dict[str, Any]] = []
        for path in list_files_sorted(get_saves_dir()):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                saves.append({
                    "id": path.stem, "title": data.get("title", path.stem),
                    "created_at": data.get("created_at", ""), "updated_at": data.get("updated_at", ""),
                    "size": path.stat().st_size,
                })
            except (OSError, json.JSONDecodeError):
                self.logger.warning("Archivo de partida no legible: %s", path.name)
        return saves

    async def save_load(self, id: str) -> Optional[Dict[str, Any]]:
        data = load_save(id)
        if not data:
            return None
        return {"metadata": {"id": id, "title": data.get("title", id)}, "content": data.get("content", "")}

    async def save_delete(self, id: str) -> bool:
        return delete_save(id)

    async def save_create(self, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        save_id = str(time.time_ns())
        payload = {"id": save_id, "title": title[:120], "content": content[:100000],
                   "created_at": now, "updated_at": now, "metadata": metadata or {}}
        path = write_save(save_id, payload)
        return {"id": save_id, "title": payload["title"], "created_at": now, "updated_at": now,
                "size": path.stat().st_size}

