# NIA — Narrador inteligente asistido

NIA es un plugin de Decky Loader para Steam Deck/SteamOS. Detecta juegos activos mediante procesos del usuario y manifiestos locales de Steam. También puede reconocer instalaciones de Heroic, GOG, Epic o Lutris si están dentro de una carpeta detectada o configurada. El panel lateral permite registrar eventos y generar narración breve, vinculada al juego y a la sesión.

## Estado de la versión 0.2

- Detección pasiva del juego activo, sin inyección ni lectura de memoria.
- Inventario local de títulos Steam y carpetas de juegos adicionales.
- Registro por juego en SQLite de sesiones, muertes, checkpoints, objetivos y victorias.
- Generación breve con Ollama local, endpoint compatible con OpenAI o comentario contextual sin LLM.
- Personalidad amable, sarcástica, grosera con humor o épica.
- Historial por juego enviado al modelo para reducir repeticiones.
- Piper opcional, desactivado por defecto.
- OCR, análisis de audio y lectura de entradas desactivados.

La posición exacta, el nivel, la vida y las muertes no están disponibles de forma genérica para todos los juegos. En esta versión, las muertes, checkpoints y objetivos se registran con los botones del panel. El diseño permite agregar adaptadores específicos por juego más adelante.

## Instalación

1. Instala Decky Loader en SteamOS.
2. Descarga nia-decky-latest.zip de la sección Releases del repositorio.
3. En modo Escritorio, abre Decky Settings → Developer → Install plugin from ZIP file y selecciona el paquete.
4. Abre el menú lateral de Decky. En Ajustes, configura Ollama o deja seleccionado el comentario contextual local.

El ZIP contiene plugin.json, main.py, dist/index.js, backend, recursos y licencia en el nivel que espera Decky. El instalador opcional installer.sh acepta un ZIP o una copia local construida. No instala Decky, no descarga modelos ni elimina datos de configuración. Con --force, conserva una copia de la instalación anterior.

## Conectar Ollama

Por defecto NIA prueba http://127.0.0.1:11434 con el modelo qwen2.5:3b. El modelo debe estar instalado y Ollama debe estar activo en la Steam Deck. Si Ollama corre en otra computadora, configura la dirección de esa computadora y habilita allí el acceso desde la red local.

Para usar una API compatible con OpenAI, selecciona ese proveedor, indica la URL completa del endpoint chat/completions, el modelo y una API key. La key queda en la configuración local de NIA y no aparece en los logs. NIA envía una solicitud breve por evento; no genera texto periódicamente.

## Voz opcional

La reproducción requiere Piper, un modelo de voz ONNX y un reproductor de audio de SteamOS (pw-play, paplay o aplay). NIA no instala binarios ni descarga modelos de voz automáticamente. La voz se puede activar y ajustar desde el panel; sin voz, la narración queda como texto.

## Consumo, datos y límites

La detección revisa procesos y carpetas cada 8 a 60 segundos (12 por defecto). Las consultas al modelo ocurren al marcar un evento o al activar el comentario al inicio de una partida. Un modelo de Ollama en otra máquina se ejecuta fuera de la Steam Deck; NIA envía solo el contexto mínimo del juego activo, el evento, las estadísticas registradas y narraciones recientes.

La base de datos, configuración, partidas y logs se guardan bajo ~/.local/share/nia-decky/. Los metadatos de Steam se consultan bajo demanda para un juego activo y quedan en caché. Sin conexión o sin un modelo disponible, funciona el comentario contextual local.

NIA no puede deducir universalmente las escenas internas ni contar muertes automáticamente. Para eso se necesitarán adaptadores por juego, APIs expuestas por el juego o integraciones opcionales como OCR. NIA no lee memoria, capturas, teclado ni mouse.

## Desarrollo

Desde la carpeta nia-decky-plugin:

```bash
pnpm install
pnpm build
pnpm typecheck
pnpm lint
pnpm test
```

La interfaz usa TypeScript/React con @decky/ui y @decky/api; Decky ejecuta el backend Python de main.py. El ZIP incluye los archivos de distribución requeridos por Decky.
