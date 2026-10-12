# NIA — Narrador inteligente asistido

NIA es un compañero narrativo para juegos. La versión activa está en la carpeta nia-decky-plugin y se instala como plugin de Decky Loader en Steam Deck/SteamOS.

## Qué hace

- Detecta el juego activo con consultas pasivas a procesos y manifiestos locales.
- Guarda historial y eventos por juego en SQLite.
- Permite registrar muertes, checkpoints, objetivos y victorias desde el panel lateral.
- Genera comentarios breves con Ollama local, un endpoint compatible con OpenAI o un modo contextual sin LLM.
- Ajusta personalidad y voz Piper opcional.
- Limita las consultas a eventos, sin generación periódica ni lectura de memoria del juego.

El proyecto anterior del repositorio nia es un prototipo de escritorio independiente. nia-sd contiene el plugin de Decky y es la base de desarrollo actual.

## Límites de detección

Los juegos no exponen un formato común para informar nivel, ubicación, salud o muertes. La versión actual detecta el proceso y registra eventos que la persona marca desde Decky. Los datos internos y eventos automáticos requieren adaptadores específicos para cada juego.

## Desarrollo e instalación

Consulta la [guía del plugin](nia-decky-plugin/README.md). En el directorio nia-decky-plugin:

```bash
pnpm install
pnpm build
pnpm typecheck
pnpm lint
pnpm test
```

Los paquetes de prueba se publican como artefactos de CI y como ZIP en Releases. Decky carga dist/index.js, plugin.json y el backend Python desde el ZIP.

## Diseño

La interfaz está escrita en TypeScript/React con las bibliotecas oficiales de Decky. El backend usa Python y la biblioteca estándar para escaneo ligero, almacenamiento SQLite, llamadas HTTP y reproducción opcional con Piper. Los modelos no se incluyen ni se descargan automáticamente.
