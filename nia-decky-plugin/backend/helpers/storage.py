import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_ID = "nia-decky"


def get_data_dir() -> Path:
  base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
  path = base / APP_ID
  path.mkdir(parents=True, exist_ok=True)
  return path


def get_config_path() -> Path:
  config_dir = get_data_dir()
  return config_dir / "config.json"


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
  with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent)) as tmp:
    json.dump(data, tmp, indent=2, ensure_ascii=False)
    tmp.flush()
    os.fsync(tmp.fileno())
  os.replace(tmp.name, path)


def read_json(path: Path) -> Dict[str, Any]:
  if not path.exists():
    return {}
  with path.open("r", encoding="utf-8") as fh:
    return json.load(fh)


def list_files_sorted(directory: Path) -> List[Path]:
  if not directory.exists():
    return []
  return sorted([p for p in directory.iterdir() if p.is_file()])


@dataclass
class SaveMetadata:
  id: str
  title: str
  created_at: str
  updated_at: str
  size: int


def load_save(save_id: str) -> Optional[Dict[str, Any]]:
  path = get_saves_dir() / f"{save_id}.json"
  if not path.exists():
    return None
  with path.open("r", encoding="utf-8") as fh:
    return json.load(fh)


def write_save(save_id: str, data: Dict[str, Any]) -> Path:
  path = get_saves_dir() / f"{save_id}.json"
  atomic_write_json(path, data)
  return path


def delete_save(save_id: str) -> bool:
  path = get_saves_dir() / f"{save_id}.json"
  if path.exists():
    path.unlink()
    return True
  return False


def remove_data_dir() -> None:
  path = get_data_dir()
  if path.exists():
    shutil.rmtree(path)


def ensure_default_config(defaults: Dict[str, Any]) -> Dict[str, Any]:
  config_path = get_config_path()
  if not config_path.exists():
    atomic_write_json(config_path, defaults)
    return defaults
  config = read_json(config_path)
  merged = {**defaults, **config}
  if merged != config:
    atomic_write_json(config_path, merged)
  return merged
