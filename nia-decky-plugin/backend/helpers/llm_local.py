import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from .storage import get_data_dir

ROOT = Path(__file__).resolve().parents[2]
BIN_PATH = ROOT / "bin" / "llama_cpp"


async def ensure_binary() -> Path:
  if not BIN_PATH.exists():
    raise FileNotFoundError(f"Binary {BIN_PATH} not found. Se esperaba wrapper de descarga.")
  if not os.access(BIN_PATH, os.X_OK):
    BIN_PATH.chmod(0o755)
  return BIN_PATH


async def generate_stream(
  prompt: str,
  model_path: Optional[str],
  temperature: float = 0.8,
  top_p: float = 0.9,
  ctx: int = 2048,
  seed: Optional[int] = None,
) -> AsyncGenerator[str, None]:
  binary = await ensure_binary()
  if not model_path:
    raise FileNotFoundError("No se configuró modelo local")
  model_file = Path(os.path.expanduser(model_path))
  if not model_file.exists():
    raise FileNotFoundError(f"Modelo no encontrado en {model_file}")

  cache_dir = get_data_dir() / "cache"
  cache_dir.mkdir(parents=True, exist_ok=True)

  cmd = [
    str(binary),
    "--model",
    str(model_file),
    "--prompt",
    prompt,
    "--ctx",
    str(ctx),
    "--temp",
    str(temperature),
    "--top_p",
    str(top_p),
    "--threads",
    str(max(1, os.cpu_count() or 2)),
    "--n_predict",
    "512",
    "--ignore-eos",
  ]
  if seed is not None:
    cmd.extend(["--seed", str(seed)])

  process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=str(cache_dir),
    limit=1024 * 256,
  )

  async def reader(stream):
    while True:
      chunk = await stream.readline()
      if not chunk:
        break
      yield chunk.decode("utf-8", errors="ignore")

  try:
    async for token in reader(process.stdout):
      yield token
  finally:
    try:
      await asyncio.wait_for(process.wait(), timeout=2)
    except asyncio.TimeoutError:
      process.kill()
      await process.wait()
