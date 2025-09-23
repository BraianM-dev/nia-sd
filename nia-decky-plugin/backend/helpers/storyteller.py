import random
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, Iterable, List, Optional

from . import llm_local, llm_remote


@dataclass
class StoryChunk:
  text: str
  done: bool = False
  error: Optional[str] = None


class Storyteller:
  def __init__(self, settings_provider, logger):
    self._settings_provider = settings_provider
    self._logger = logger

  async def generate(self, params: Dict) -> List[Dict[str, Optional[str]]]:
    chunks: List[Dict[str, Optional[str]]] = []
    async for chunk in self._iter_chunks(params):
      payload = {"text": chunk.text, "done": chunk.done, "error": chunk.error}
      chunks.append(payload)
    if not chunks:
      chunks.append({"text": "", "done": True, "error": "No se generó texto"})
    return chunks

  async def _iter_chunks(self, params: Dict) -> AsyncGenerator[StoryChunk, None]:
    settings = self._settings_provider()
    mode = settings.get("mode", "offline")
    self._logger.info("Story generation requested mode=%s", mode)

    template = self._build_prompt(params)

    generator: Optional[AsyncGenerator[str, None]] = None
    error: Optional[str] = None

    if mode == "remote" and settings.get("remote", {}).get("enabled"):
      try:
        generator = llm_remote.generate_stream(
          prompt=template,
          endpoint=settings["remote"].get("endpoint"),
          auth=settings["remote"].get("auth"),
          timeout=settings["remote"].get("timeout", 15),
        )
      except Exception as exc:  # noqa: BLE001
        error = f"Fallo remoto: {exc}"
        self._logger.exception("Remote generation failed")

    if generator is None and mode in {"offline", "remote"}:
      try:
        generator = llm_local.generate_stream(
          prompt=template,
          model_path=settings.get("model", {}).get("path"),
          temperature=settings.get("model", {}).get("temperature", 0.8),
          top_p=settings.get("model", {}).get("top_p", 0.9),
          ctx=settings.get("model", {}).get("ctx", 2048),
          seed=params.get("seed"),
        )
      except Exception as exc:  # noqa: BLE001
        error = f"Fallo local: {exc}"
        self._logger.exception("Local generation failed")

    if generator is None:
      self._logger.warning("Falling back to template mode")
      for chunk in self._template_story(params):
        yield chunk
      if error:
        yield StoryChunk(text="", done=True, error=error)
      return

    buffer = ""
    last_emit = time.monotonic()
    try:
      async for token in generator:  # type: ignore[arg-type]
        buffer += token
        now = time.monotonic()
        if len(buffer) > 120 or now - last_emit > 1.0:
          yield StoryChunk(text=buffer, done=False, error=error)
          buffer = ""
          last_emit = now
      if buffer:
        yield StoryChunk(text=buffer, done=False, error=error)
      yield StoryChunk(text="", done=True, error=error)
    except Exception as exc:  # noqa: BLE001
      self._logger.exception("Error streaming story")
      yield StoryChunk(text=buffer, done=True, error=f"Error durante generación: {exc}")

  def _build_prompt(self, params: Dict) -> str:
    genre = params.get("genre", "aventura")
    tone = params.get("tone", "exploratorio")
    keywords = params.get("keywords", [])
    characters = params.get("characters", [])
    length = params.get("length", "medium")

    instructions = [
      "Eres un narrador interactivo para Steam Deck.",
      f"Género: {genre}.",
      f"Tono: {tone}.",
    ]
    if keywords:
      instructions.append("Palabras clave: " + ", ".join(keywords) + ".")
    if characters:
      instructions.append("Personajes principales: " + ", ".join(characters) + ".")
    instructions.append("Escribe en español neutro, con párrafos cortos.")
    if length == "short":
      instructions.append("Limita la historia a 3 párrafos.")
    elif length == "long":
      instructions.append("Extiende la narración a 6 párrafos con giros narrativos.")
    instructions.append("Introduce decisiones implícitas para continuar más adelante.")

    prompt = "\n".join(instructions) + "\nComienza la narración ahora:\n"
    self._logger.debug("Prompt construido: %s", prompt)
    return prompt

  def _template_story(self, params: Dict) -> Iterable[StoryChunk]:
    random.seed(params.get("seed"))
    genre = params.get("genre", "aventura")
    tone = params.get("tone", "misterioso")
    characters = params.get("characters", ["Alex"])
    keywords = params.get("keywords", ["destino", "puertas"])
    intro = random.choice([
      "La lluvia tamborileaba sobre la cubierta mientras",
      "Las luces del vagón parpadearon justo cuando",
      "Una melodía antigua resonó en la plaza cuando",
    ])
    conflict = random.choice([
      "un mensaje cifrado apareció en el dispositivo portátil.",
      "una sombra tomó forma entre la niebla.",
      "la brújula marcó un rumbo imposible.",
    ])
    guide = random.choice([
      "Recuerda observar el entorno y elegir a tu aliado con cuidado.",
      "La próxima decisión cambiará la confianza del grupo.",
      "Escucha el murmullo de la ciudad para descubrir la pista oculta.",
    ])
    hero = ", ".join(characters[:3])
    text = (
      f"{intro} {hero} comprendió que el género {genre} podía volverse tangible. "
      f"Con un tono {tone.lower()}, cada paso resonaba con {', '.join(keywords[:3])}. "
      f"Entonces {conflict} {guide}"
    )
    yield StoryChunk(text=text, done=False, error="Modo plantillas activo")
    yield StoryChunk(text="", done=True, error="Modo plantillas activo")
