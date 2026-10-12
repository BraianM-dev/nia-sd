"""User data paths and safe legacy story-save operations."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

APP_ID = "nia-decky"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def get_data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_data_dir() / "config.json"


def get_saves_dir() -> Path:
    path = get_data_dir() / "saves"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    path = get_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent))
    try:
        with handle as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(handle.name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            Path(handle.name).unlink(missing_ok=True)
        except OSError:
            pass


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    return value if isinstance(value, dict) else {}


def list_files_sorted(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".json")


def load_save(save_id: str) -> Optional[Dict[str, Any]]:
    if not _SAFE_ID.fullmatch(str(save_id)):
        return None
    path = get_saves_dir() / (str(save_id) + ".json")
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    return value if isinstance(value, dict) else None


def write_save(save_id: str, data: Dict[str, Any]) -> Path:
    if not _SAFE_ID.fullmatch(str(save_id)):
        raise ValueError("Identificador de partida inválido")
    path = get_saves_dir() / (str(save_id) + ".json")
    atomic_write_json(path, data)
    return path


def delete_save(save_id: str) -> bool:
    if not _SAFE_ID.fullmatch(str(save_id)):
        return False
    path = get_saves_dir() / (str(save_id) + ".json")
    if not path.exists():
        return False
    path.unlink()
    return True


def _merge(defaults: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    for key, value in current.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_default_config(defaults: Dict[str, Any]) -> Dict[str, Any]:
    path = get_config_path()
    try:
        current = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        current = {}
    config = _merge(defaults, current)
    if config != current:
        atomic_write_json(path, config)
    return config
