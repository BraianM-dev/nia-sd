import asyncio
import hashlib
import os
from pathlib import Path
from typing import Optional

try:
  import aiohttp
except ImportError:  # pragma: no cover
  aiohttp = None  # type: ignore

from .storage import get_data_dir

ROOT = Path(__file__).resolve().parents[2]
BIN_PATH = ROOT / "bin" / "piper"


async def ensure_binary() -> Path:
  if not BIN_PATH.exists():
    raise FileNotFoundError(f"Binary {BIN_PATH} not found. Se esperaba wrapper de descarga.")
  if not os.access(BIN_PATH, os.X_OK):
    BIN_PATH.chmod(0o755)
  return BIN_PATH


async def download_file(url: str, destination: Path, checksum: str = "") -> Path:
  destination.parent.mkdir(parents=True, exist_ok=True)
  if destination.exists():
    if checksum and not verify_checksum(destination, checksum):
      destination.unlink()
    else:
      return destination

  if aiohttp is None:
    raise RuntimeError("aiohttp no disponible para descargar voz")

  async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
      response.raise_for_status()
      with destination.open("wb") as fh:
        async for chunk in response.content.iter_chunked(1024 * 256):
          fh.write(chunk)

  if checksum and not verify_checksum(destination, checksum):
    destination.unlink(missing_ok=True)
    raise ValueError("Checksum de voz Piper inválido")

  return destination


def verify_checksum(path: Path, checksum: str) -> bool:
  if not checksum:
    return True
  sha = hashlib.sha256()
  with path.open("rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
      sha.update(chunk)
  return sha.hexdigest() == checksum.lower()


async def synthesize(text: str, voice_path: str, speed: float = 1.0) -> Path:
  binary = await ensure_binary()
  voice_file = Path(os.path.expanduser(voice_path))
  if not voice_file.exists():
    raise FileNotFoundError(f"Voz Piper no encontrada: {voice_file}")

  output_dir = get_data_dir() / "tts"
  output_dir.mkdir(parents=True, exist_ok=True)
  output_file = output_dir / "nia_output.wav"

  cmd = [
    str(binary),
    "--model",
    str(voice_file),
    "--output_file",
    str(output_file),
    "--text",
    text,
    "--length_scale",
    str(max(0.5, min(2.0, speed))),
  ]

  process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  stdout, stderr = await process.communicate()
  if process.returncode != 0:
    raise RuntimeError(f"Piper falló: {stderr.decode('utf-8', errors='ignore')}")

  return output_file
