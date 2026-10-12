# NIA — narrador inteligente asistido

NIA es un compañero narrativo para videojuegos. La versión activa está en [`nia-decky-plugin`](nia-decky-plugin/) y se instala como plugin de Decky Loader en Steam Deck/SteamOS.

## Qué hace

- Detecta juegos activos de Steam y ejecutables en carpetas de juegos configuradas.
- Guarda sesiones, eventos y narraciones por juego.
- Genera comentarios breves con un motor local llama.cpp, OpenAI API, Grok, DeepSeek, Gemini, Ollama u otro endpoint compatible.
- Permite cambiar tono y personalidad, y puede usar Piper para reproducir voz si el usuario instala sus recursos.
- Incluye respuestas contextuales locales si un LLM no está disponible.

El motor local funciona en Modo Juego sin Ollama. Descarga llama.cpp y Qwen2.5 1.5B Q4_K_M desde Ajustes, verifica las sumas SHA-256, no instala paquetes del sistema y usa CPU con límites configurables. El LLM se llama al inicio opcional de sesión o cuando se registra un evento, no con una consulta constante.

## Límites de detección

No hay una interfaz común para leer el nivel, ubicación, salud o muertes internas de todos los juegos. NIA registra muertes, checkpoints, objetivos y victorias desde el panel; el registro automático requiere una integración por juego o una fuente pública de datos. NIA no inyecta código ni lee memoria del juego, capturas ni entradas.

## Instalación y desarrollo

Consulta la [guía completa del plugin](nia-decky-plugin/README.md). En `nia-decky-plugin`:

```bash
pnpm install
pnpm build
pnpm typecheck
pnpm lint
pnpm test
```

La UI está escrita en TypeScript/React con las bibliotecas de Decky. El backend usa Python y SQLite. El modelo local no se incluye en el ZIP; su instalación es voluntaria y se inicia desde el panel lateral.

`nia` es un prototipo de escritorio anterior. `nia-sd` es el repositorio de desarrollo del plugin Decky.
