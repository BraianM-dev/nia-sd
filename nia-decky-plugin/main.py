import asyncio
import json
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.helpers.storage import (
  atomic_write_json,
  delete_save,
  ensure_default_config,
  get_config_path,
  get_logs_dir,
  get_saves_dir,
  list_files_sorted,
  load_save,
  write_save,
)
from backend.helpers.storyteller import Storyteller
from backend.helpers import tts

ROOT = Path(__file__).resolve().parent
DEFAULTS_PATH = ROOT / "defaults" / "config.example.json"


class Plugin:
  def __init__(self):
    self.logger: logging.Logger = logging.getLogger("nia-decky")
    self.settings: Dict[str, Any] = {}
    self.storyteller = Storyteller(self._get_settings, self.logger)
    self._tasks: List[asyncio.Task] = []

  async def _main(self):
    self._setup_logging()
    self.logger.info("Inicializando plugin NIA")
    defaults = self._load_defaults()
    self.settings = ensure_default_config(defaults)
    await self._ensure_resources()

  async def _unload(self):
    for task in self._tasks:
      task.cancel()
    await asyncio.gather(*self._tasks, return_exceptions=True)
    self.logger.info("Plugin descargado")

  def _get_settings(self) -> Dict[str, Any]:
    return dict(self.settings)

  async def settings_get(self) -> Dict[str, Any]:
    return self._get_settings()

  async def settings_set(self, settings: Dict[str, Any]) -> Dict[str, Any]:
    self.settings = settings
    atomic_write_json(get_config_path(), settings)
    await self._ensure_resources()
    return self._get_settings()

  async def story_generate(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    self.logger.info("Generando historia con parámetros: %s", params)
    return await self.storyteller.generate(params)

  async def save_list(self) -> List[Dict[str, Any]]:
    saves: List[Dict[str, Any]] = []
    for path in list_files_sorted(get_saves_dir()):
      try:
        data = json.loads(path.read_text(encoding="utf-8"))
        saves.append(
          {
            "id": path.stem,
            "title": data.get("title", path.stem),
            "created_at": data.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": data.get("updated_at", datetime.utcnow().isoformat()),
            "size": path.stat().st_size,
          }
        )
      except json.JSONDecodeError:
        self.logger.warning("Archivo de save corrupto: %s", path)
    return saves

  async def save_load(self, id: str) -> Optional[Dict[str, Any]]:
    data = load_save(id)
    if not data:
      return None
    return {"metadata": {"id": id, "title": data.get("title", id)}, "content": data.get("content", "")}

  async def save_delete(self, id: str) -> bool:
    return delete_save(id)

  async def save_create(self, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    save_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    now = datetime.utcnow().isoformat()
    payload = {
      "id": save_id,
      "title": title,
      "content": content,
      "created_at": now,
      "updated_at": now,
      "metadata": metadata or {},
    }
    path = write_save(save_id, payload)
    return {
      "id": save_id,
      "title": title,
      "created_at": now,
      "updated_at": now,
      "size": path.stat().st_size,
    }

  async def tts_speak(self, text: str, voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
    config_voice = self.settings.get("tts", {}).get("path")
    voice_path = voice or config_voice
    if not voice_path:
      raise RuntimeError("No hay voz configurada")
    speed = float(self.settings.get("tts", {}).get("speed", 1.0))
    output = await tts.synthesize(text, voice_path, speed)
    return {"path": f"file://{output}"}

  async def verify_resources(self) -> Dict[str, Any]:
    details: List[str] = []
    status = "ok"
    try:
      await self._ensure_model(details)
    except Exception as exc:  # noqa: BLE001
      status = "degraded"
      details.append(f"Modelo: {exc}")
    try:
      await self._ensure_voice(details)
    except Exception as exc:  # noqa: BLE001
      status = "degraded"
      details.append(f"Voz: {exc}")
    return {"status": status, "details": details or ["Recursos disponibles"]}

  def _setup_logging(self):
    logs_dir = get_logs_dir()
    log_file = logs_dir / "nia.log"
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(fmt)
    self.logger.setLevel(logging.INFO)
    self.logger.addHandler(handler)

  def _load_defaults(self) -> Dict[str, Any]:
    if DEFAULTS_PATH.exists():
      with DEFAULTS_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)
    return {
      "mode": "offline",
      "model": {},
      "tts": {},
      "remote": {"enabled": False},
      "status": "ok",
    }

  async def _ensure_resources(self):
    details: List[str] = []
    await self._ensure_model(details)
    await self._ensure_voice(details)
    if details:
      self.logger.info("Estado de recursos: %s", details)

  async def _ensure_model(self, details: List[str]):
    model_info = self.settings.get("model", {})
    model_path = model_info.get("path")
    url = model_info.get("gguf_url")
    checksum = model_info.get("checksum", "")
    if not model_path or not url:
      details.append("Modelo no configurado")
      return
    destination = Path(os.path.expanduser(model_path))
    if destination.exists():
      details.append("Modelo disponible")
      return
    destination.parent.mkdir(parents=True, exist_ok=True)
    await self._download(url, destination, checksum)
    details.append("Modelo descargado")

  async def _ensure_voice(self, details: List[str]):
    tts_info = self.settings.get("tts", {})
    path = tts_info.get("path")
    url = tts_info.get("voice_url")
    checksum = tts_info.get("checksum", "")
    if not path or not url:
      details.append("Voz no configurada")
      return
    destination = Path(os.path.expanduser(path))
    if destination.exists():
      details.append("Voz disponible")
      return
    await tts.download_file(url, destination, checksum)
    details.append("Voz descargada")

  async def _download(self, url: str, destination: Path, checksum: str = ""):
    try:
      import aiohttp
    except ImportError as exc:  # pragma: no cover
      raise RuntimeError("aiohttp no disponible para descargar modelo") from exc
    import hashlib

    tmp_path = destination.with_suffix(".part")
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as response:
        response.raise_for_status()
        with tmp_path.open("wb") as fh:
          async for chunk in response.content.iter_chunked(1024 * 256):
            fh.write(chunk)
    if checksum:
      sha = hashlib.sha256()
      with tmp_path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
          sha.update(block)
      if sha.hexdigest() != checksum.lower():
        tmp_path.unlink(missing_ok=True)
        raise ValueError("Checksum inválido para modelo LLM")
    tmp_path.rename(destination)
