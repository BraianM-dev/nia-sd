"""Optional Piper speech playback through the SteamOS audio session."""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple


def _find_piper(configured: str = "") -> Optional[str]:
    if configured:
        path = Path(os.path.expandvars(os.path.expanduser(configured)))
        if path.is_file() and os.access(str(path), os.X_OK):
            return str(path)
    return shutil.which("piper")


def _find_player() -> Optional[str]:
    for program in ("pw-play", "paplay", "aplay"):
        found = shutil.which(program)
        if found:
            return found
    return None


async def synthesize(text: str, voice_path: str, speed: float = 1.0,
                     binary_path: str = "") -> dict:
    voice = Path(os.path.expandvars(os.path.expanduser(voice_path))) if voice_path else None
    if not voice or not voice.is_file():
        raise FileNotFoundError("Selecciona un modelo de voz Piper .onnx válido")
    piper = _find_piper(binary_path)
    if not piper:
        raise FileNotFoundError("Piper no está instalado o la ruta configurada no es ejecutable")
    player = _find_player()
    if not player:
        raise FileNotFoundError("No se encontró pw-play, paplay ni aplay para reproducir el audio")
    with tempfile.NamedTemporaryFile(prefix="nia-", suffix=".wav", delete=False) as output:
        output_path = Path(output.name)
    try:
        command = [
            piper, "--model", str(voice), "--output_file", str(output_path),
            "--length_scale", str(max(0.5, min(2.0, float(speed)))),
        ]
        process = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, error = await process.communicate(input=text[:3000].encode("utf-8"))
        if process.returncode:
            message = error.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError("Piper no pudo sintetizar la voz: " + message)
        playback = await asyncio.create_subprocess_exec(
            player, str(output_path), stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, error = await playback.communicate()
        if playback.returncode:
            message = error.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError("No se pudo reproducir el audio: " + message)
        return {"playing": True, "player": Path(player).name}
    finally:
        output_path.unlink(missing_ok=True)


async def download_file(url: str, destination: Path, checksum: str = "") -> Path:
    raise RuntimeError("La descarga automática de binarios y modelos está desactivada; usa una fuente verificada e instala los recursos manualmente")
