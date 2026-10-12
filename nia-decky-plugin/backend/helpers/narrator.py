"""Short, event-triggered game narration with bounded local/remote inference."""
from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Callable, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .context_store import NiaStore
from .metadata import fetch_steam_metadata

_PERSONA = {
    "amable": "cálido, atento y alentador",
    "sarcastico": "irónico y mordaz, con humor, sin atacar a la persona",
    "grosero": "malhablado y cómico, con insultos suaves al juego o a la situación; nunca uses insultos discriminatorios",
    "epico": "épico, solemne y cinematográfico",
}
_EVENT_LABELS = {
    "session_start": "inicio de sesión",
    "death": "muerte o caída",
    "checkpoint": "checkpoint alcanzado",
    "objective": "objetivo o descubrimiento",
    "victory": "victoria",
    "commentary": "intervención solicitada por el jugador",
}
_PROVIDER_DEFAULTS = {
    "openai": {"endpoint": "https://api.openai.com/v1/chat/completions", "model": "gpt-6-luna"},
    "grok": {"endpoint": "https://api.x.ai/v1/chat/completions", "model": "grok-4.7"},
    "deepseek": {"endpoint": "https://api.deepseek.com/chat/completions", "model": "deepseek-v4-flash"},
    "gemini": {
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-3.8-flash",
    },
}
_TEMPLATES = {
    "session_start": [
        "Se abre la sesión de «{title}». NIA ya tiene el contexto: {context}.",
        "Arranca «{title}». La partida queda registrada; por ahora, el único dato seguro es este: {context}.",
        "«{title}» vuelve a escena. NIA seguirá el ritmo de esta sesión y guardará los momentos que marques.",
    ],
    "death": [
        "Otra caída en «{title}»: llevas {deaths} caídas registradas. El narrador toma nota; todavía puedes convertir el tropiezo en una historia.",
        "La cuenta de «{title}» suma {deaths} caídas. El juego se llevó esta ronda, pero NIA ya tiene material para juzgar la revancha.",
        "«{title}» te puso a prueba otra vez: {deaths} muertes registradas. Respira, vuelve y haz que la próxima escena cambie el tono.",
    ],
    "checkpoint": [
        "Checkpoint en «{title}». Van {checkpoints} marcados; al menos el progreso ya no depende de la memoria.",
        "Queda guardado un nuevo punto de control en «{title}» ({checkpoints} registrados). NIA deja constancia antes de que el juego intente complicarte el regreso.",
    ],
    "objective": [
        "Anotado en «{title}»: {detail}. NIA lo incorpora a la crónica como un avance de la partida.",
        "«{title}» suma un nuevo hito: {detail}. La historia ya tiene una pista concreta de lo que acabas de lograr.",
    ],
    "victory": [
        "Victoria registrada en «{title}». NIA cierra este capítulo con el dato que cuenta: lo terminaste.",
        "«{title}» cayó. Queda anotada la victoria; esta vez el juicio del narrador es sencillo: misión cumplida.",
    ],
    "commentary": [
        "En «{title}» llevas {minutes} minutos de sesión. {context} NIA seguirá la partida a partir de los eventos que marques.",
        "NIA revisa «{title}»: {context} No inventaré una misión ni una ubicación que el juego no haya expuesto.",
    ],
}


class NiaNarrator:
    def __init__(self, settings_provider: Callable[[], Dict[str, Any]], store: NiaStore,
                 local_runtime: Any = None) -> None:
        self.settings_provider = settings_provider
        self.store = store
        self.local_runtime = local_runtime
        self._metadata_checked = set()

    async def narrate(self, game: Dict[str, Any], event: Dict[str, Any], session_started: float) -> Dict[str, Any]:
        return await asyncio.to_thread(self._narrate_sync, game, event, session_started)

    def _narrate_sync(self, game: Dict[str, Any], event: Dict[str, Any], session_started: float) -> Dict[str, Any]:
        settings = self.settings_provider()
        narrator = settings.get("narrator", {})
        game_id = str(game.get("id", game.get("session_key", "unknown")))
        profile = settings.get("game_profiles", {}).get(game_id, {})
        if isinstance(profile, dict) and profile.get("persona") in _PERSONA:
            narrator = {**narrator, "persona": profile["persona"]}
        metadata = self.store.get_metadata(game_id)
        if metadata is None and game.get("appid") and game_id not in self._metadata_checked:
            self._metadata_checked.add(game_id)
            metadata = fetch_steam_metadata(str(game["appid"]), narrator.get("timeout", 3))
            if metadata:
                self.store.put_metadata(game_id, metadata)
        metadata = metadata or {}
        stats = self.store.game_stats(game_id)
        minutes = max(0, int((__import__("time").time() - session_started) / 60))
        context = self._build_context(game, event, metadata, stats, minutes)
        provider = narrator.get("provider", "local-llama")
        error = ""
        text = ""
        if provider in {"ollama", "openai-compatible", "local-llama", "openai", "grok", "deepseek", "gemini"}:
            try:
                request_config = dict(narrator)
                request_config["local_runtime"] = settings.get("local_runtime", {})
                request_config["model_path"] = settings.get("model", {}).get("path", "")
                text = self._request_model(request_config, game, event, metadata, stats, minutes)
            except Exception as exc:
                error = str(exc)[:240]
        if not text:
            text = self._fallback(game, event, metadata, stats, minutes, session_started, narrator.get("persona"))
            if not error:
                error = "Usando comentario local contextual"
        if not self.store.add_narration(game_id, str(event.get("type", "commentary")), text):
            text = self._fallback(
                game, event, metadata, stats, minutes,
                session_started + int(__import__("time").time()), narrator.get("persona"),
            )
            self.store.add_narration(game_id, str(event.get("type", "commentary")), text)
            error = "Se evitó repetir la última narración"
        return {
            "text": text, "status": error or "Generado",
            "game_id": game_id, "event_type": str(event.get("type", "commentary")),
            "source": metadata.get("source", ""),
        }

    def _build_context(self, game: Dict[str, Any], event: Dict[str, Any],
                       metadata: Dict[str, Any], stats: Dict[str, int], minutes: int) -> Dict[str, Any]:
        return {
            "game": str(game.get("title") or "Juego activo")[:120],
            "platform": str(game.get("platform") or "desconocida")[:60],
            "session_minutes": minutes,
            "event": str(event.get("type", "commentary")),
            "event_detail": str(event.get("detail", ""))[:300],
            "deaths_recorded": stats.get("deaths", 0),
            "checkpoints_recorded": stats.get("checkpoints", 0),
            "objectives_recorded": stats.get("objectives", 0),
            "game_description": str(metadata.get("summary", ""))[:800],
            "genres": metadata.get("genres", [])[:8],
            "recent_narration": self.store.recent_narrations(str(game.get("id")), 6),
        }

    def _request_model(self, config: Dict[str, Any], game: Dict[str, Any], event: Dict[str, Any],
                       metadata: Dict[str, Any], stats: Dict[str, int], minutes: int) -> str:
        provider = str(config.get("provider", "ollama"))
        endpoint = str(config.get("endpoint", "")).strip()
        model = str(config.get("model", "")).strip()
        token = str(config.get("api_key", "")).strip()
        if provider in _PROVIDER_DEFAULTS:
            preset = _PROVIDER_DEFAULTS[provider]
            endpoint = endpoint or preset["endpoint"]
            model = model or preset["model"]
            if not token:
                raise RuntimeError("Falta la clave API del proveedor seleccionado")
        elif provider == "local-llama":
            if not self.local_runtime:
                raise RuntimeError("El motor local de NIA no está inicializado")
            endpoint, token = self.local_runtime.openai_endpoint(
                config.get("local_runtime", {}), str(config.get("model_path", "")),
            )
            model = model or "local-qwen"
        if not endpoint or not model:
            raise RuntimeError("Configura el endpoint y el modelo del narrador")
        persona = _PERSONA.get(str(config.get("persona", "amable")), _PERSONA["amable"])
        context = self._build_context(game, event, metadata, stats, minutes)
        system = (
            "Eres NIA, un narrador compañero de videojuegos. "
            "Escribe en español rioplatense natural, en una o dos frases cortas. "
            "Ajusta el tono a: " + persona + ". "
            "Usa solo los datos del contexto; no inventes nivel, ubicación, misión, vida, muerte ni avance. "
            "Si faltan datos, habla de la sesión y de los eventos registrados. "
            "Evita repetir las narraciones recientes y no interrumpas con preguntas largas."
        )
        user = json.dumps(context, ensure_ascii=False)
        timeout = 90 if provider == "local-llama" else max(2, min(60, int(config.get("timeout", 8))))
        body: Dict[str, Any]
        headers = {"Content-Type": "application/json", "User-Agent": "NIA-Decky/0.4"}
        if provider == "ollama":
            if not endpoint.rstrip("/").endswith("/api/chat"):
                endpoint = endpoint.rstrip("/") + "/api/chat"
            body = {
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
                "options": {
                    "temperature": max(0.1, min(1.5, float(config.get("temperature", 0.7)))),
                    "num_predict": max(32, min(180, int(config.get("max_tokens", 96)))),
                    "top_p": 0.9,
                },
                "keep_alive": "2m",
            }
        else:
            body = {
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": max(0.1, min(1.5, float(config.get("temperature", 0.7)))),
                "stream": False,
            }
            token_limit = max(32, min(180, int(config.get("max_tokens", 96))))
            body["max_completion_tokens" if provider == "openai" else "max_tokens"] = token_limit
            if token:
                headers["Authorization"] = "Bearer " + token
        request = Request(endpoint, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(256 * 1024).decode("utf-8", errors="replace"))
        if provider == "ollama":
            text = payload.get("message", {}).get("content", "")
        else:
            choices = payload.get("choices", [])
            text = choices[0].get("message", {}).get("content", "") if choices else ""
        cleaned = " ".join(str(text).strip().split())
        if not cleaned:
            raise RuntimeError("El modelo respondió sin texto")
        return cleaned[:1600]

    def _fallback(self, game: Dict[str, Any], event: Dict[str, Any], metadata: Dict[str, Any],
                  stats: Dict[str, int], minutes: int, seed: float, persona: Optional[str] = None) -> str:
        event_type = str(event.get("type", "commentary"))
        title = str(game.get("title") or "Juego activo")
        detail = str(event.get("detail") or "un momento de la partida")[:160]
        context = str(metadata.get("summary") or game.get("platform") or "la sesión actual")
        options = _TEMPLATES.get(event_type, _TEMPLATES["commentary"])
        index = abs(hash((game.get("id"), event_type, int(seed), stats.get(event_type, 0)))) % len(options)
        tone = persona or str(self.settings_provider().get("narrator", {}).get("persona", "amable"))
        text = options[index].format(
            title=title, deaths=stats.get("deaths", 0),
            checkpoints=stats.get("checkpoints", 0), objectives=stats.get("objectives", 0),
            minutes=minutes, detail=detail, context=context,
        )
        if tone == "sarcastico":
            text = text.replace("NIA ya tiene el contexto", "NIA ya tiene el contexto, aunque el juego se empeñe en ocultarlo")
        elif tone == "grosero":
            text += " La partida viene jodida, pero todavía no está cerrada."
        elif tone == "epico":
            text = "La crónica canta: " + text.replace("NIA", "el cronista")
        return text[:1000]

    async def probe(self) -> Dict[str, Any]:
        settings = self.settings_provider()
        config = settings.get("narrator", {})
        provider = config.get("provider", "ollama")
        if provider == "template":
            return {"ok": True, "message": "El narrador contextual local está disponible"}
        if provider == "local-llama":
            if not self.local_runtime:
                return {"ok": False, "message": "El motor local de NIA no está inicializado"}
            runtime = self.local_runtime.status(str(settings.get("model", {}).get("path", "")))
            if runtime["engine_installed"] and runtime["model_installed"]:
                return {"ok": True, "message": "llama.cpp y el modelo local están instalados"}
            return {"ok": False, "message": "Instala llama.cpp y el modelo local desde Ajustes"}
        endpoint = str(config.get("endpoint", "")).strip()
        if provider in _PROVIDER_DEFAULTS:
            endpoint = endpoint or _PROVIDER_DEFAULTS[provider]["endpoint"]
        if not endpoint:
            return {"ok": False, "message": "Falta configurar el endpoint"}
        try:
            if provider == "ollama":
                base = endpoint.rstrip("/")
                if base.endswith("/api/chat"):
                    base = base[:-9]
                request = Request(base + "/api/tags", headers={"User-Agent": "NIA-Decky/0.4"})
                await asyncio.to_thread(lambda: urlopen(request, timeout=3).read(4096))
            else:
                if provider in _PROVIDER_DEFAULTS and not str(config.get("api_key", "")).strip():
                    return {"ok": False, "message": "Guarda la clave API del proveedor seleccionado"}
                return {"ok": True, "message": "Endpoint configurado; se probará al narrar"}
            return {"ok": True, "message": "Ollama responde"}
        except (OSError, URLError, TimeoutError):
            return {"ok": False, "message": "No se pudo conectar; NIA usará el comentario local"}

