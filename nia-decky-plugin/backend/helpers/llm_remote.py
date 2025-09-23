import asyncio
import json
from typing import AsyncGenerator, Iterable, Optional

try:
  import aiohttp
except ImportError:  # pragma: no cover
  aiohttp = None  # type: ignore


async def generate_stream(
  prompt: str,
  endpoint: Optional[str],
  auth: Optional[str] = None,
  timeout: int = 15,
) -> AsyncGenerator[str, None]:
  if not endpoint:
    raise RuntimeError("No se definió endpoint remoto")
  if aiohttp is None:
    raise RuntimeError("aiohttp no disponible en el entorno")

  headers = {"Content-Type": "application/json"}
  if auth:
    headers["Authorization"] = auth

  session_timeout = aiohttp.ClientTimeout(total=None, sock_connect=timeout, sock_read=timeout)
  async with aiohttp.ClientSession(timeout=session_timeout) as session:
    async with session.post(endpoint, headers=headers, json={"prompt": prompt, "stream": True}) as response:
      response.raise_for_status()
      async for chunk in response.content.iter_any():
        if not chunk:
          continue
        try:
          data = json.loads(chunk.decode("utf-8"))
          token = data.get("token") or data.get("text") or ""
          yield token
          if data.get("done"):
            break
        except json.JSONDecodeError:
          yield chunk.decode("utf-8", errors="ignore")
      await asyncio.sleep(0)
