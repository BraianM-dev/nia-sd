# NIA Decky 0.4.0 — narrador de videojuegos

NIA es un plugin para Decky Loader en Steam Deck/SteamOS. Detecta el juego activo, guarda el contexto de cada sesión y crea comentarios breves con un modelo local, un proveedor de API o un narrador contextual que no usa LLM.

## Motor local recomendado

NIA incluye un instalador opcional para llama.cpp y Qwen2.5 1.5B Instruct Q4_K_M. No depende de Ollama ni de que Ollama siga ejecutándose al entrar en Modo Juego. En Ajustes → Motor de narración, elige **NIA local · llama.cpp** y pulsa **Descargar e instalar**.

- Descarga el motor CPU de llama.cpp y un modelo GGUF de aproximadamente 1,12 GB solo después de pulsar el botón.
- Comprueba las sumas SHA-256 publicadas por los proyectos upstream antes de instalar ambos archivos.
- Instala los recursos en el directorio de datos de NIA, sin `sudo`, paquetes del sistema ni cambios a SteamOS.
- Ejecuta llama-server solo cuando NIA necesita narrar, enlazado a `127.0.0.1` y protegido con una clave aleatoria.
- Por defecto limita la inferencia a 2 hilos, contexto de 2048 tokens y prioridad baja. llama.cpp descarga los pesos de la RAM tras 90 segundos sin uso.
- Comprueba el espacio libre antes de descargar. Una descarga se puede cancelar y reanudar; también se puede indicar una ruta a otro GGUF compatible.

La inferencia local usa CPU y puede tardar más que una API remota; consume CPU mientras genera. Los límites reducen el impacto, pero no garantizan cero cambios en FPS. NIA no genera narraciones en segundo plano de forma periódica: consulta al modelo cuando se inicia un juego (si esa opción está activada) o cuando se registra un evento.

## Proveedores de IA

Desde Ajustes se puede elegir:

| Proveedor | Endpoint preconfigurado | Modelo inicial editable |
| --- | --- | --- |
| NIA local | llama.cpp incluido | Qwen2.5 1.5B Q4_K_M |
| Ollama | Local o en otra máquina | `qwen2.5:3b` |
| OpenAI API | Chat Completions | `gpt-6-luna` |
| xAI Grok API | Chat Completions | `grok-4.7` |
| DeepSeek API | Chat Completions | `deepseek-v4-flash` |
| Google Gemini API | Compatibilidad OpenAI | `gemini-3.8-flash` |
| Compatible con OpenAI | Endpoint configurable | Modelo configurable |
| Contextual sin LLM | Sin endpoint | Sin modelo |

Cada proveedor remoto requiere una clave API del servicio elegido. La clave se guarda en la configuración local con permisos de usuario y se borra del formulario al cambiar de proveedor para evitar mandarla por error al siguiente. El contenido narrado y el contexto de partida se envían al proveedor seleccionado. El uso de OpenAI API se factura aparte de ChatGPT Plus/Pro; lo mismo aplica a las API de otros proveedores y sus planes de chat.

Los endpoints y modelos se pueden editar. Si el proveedor cambia su catálogo, se puede elegir otro modelo compatible sin actualizar NIA. Para usar Ollama de una computadora distinta, escribe su dirección de red; una configuración previa de Ollama en `localhost` se migra al motor local incluido.

## Perfiles por juego\n\nDesde el panel lateral se puede guardar una personalidad y una voz Piper `.onnx` por juego activo. Los campos vacíos heredan el ajuste predeterminado. El perfil se guarda localmente con el resto de la configuración.\n\n## Partidas, progreso y detección

NIA detecta procesos de juegos y manifiestos locales de Steam. Puede buscar ejecutables en carpetas que agregues, por ejemplo bibliotecas usadas por Heroic, GOG, Epic o Lutris. No necesita que el juego se ejecute mediante una sola tienda para poder aparecer en el catálogo, aunque cada launcher guarda sus instalaciones de forma distinta.

El plugin registra sesiones, muertes, checkpoints, objetivos y victorias en SQLite. Los eventos se marcan desde el panel. No existe una API universal que permita a Decky conocer el nivel, la ubicación, la vida o las muertes internas de cada juego; para automatizar esos datos hacen falta adaptadores específicos por juego o datos públicos de una API/achievement. NIA no inyecta código, no lee memoria del proceso, capturas, teclado ni mouse.

Las narraciones recientes se pasan como contexto para reducir repeticiones. Si no hay conexión, una clave, un modelo instalado o el servidor falla, NIA sigue respondiendo con frases contextuales locales.

## Voz opcional

Se puede activar Piper y configurar una voz desde el panel. La instalación de Piper y la descarga de su voz se hacen manualmente: se necesita un binario Piper ejecutable, un modelo `.onnx` y un reproductor disponible en SteamOS (`pw-play`, `paplay` o `aplay`). Sin esos recursos, NIA sigue mostrando texto y no intenta reproducir audio.

## Instalación como plugin Decky

1. Instala Decky Loader en SteamOS.
2. Descarga `nia-decky-latest.zip` de Releases o usa el artefacto ZIP generado por CI.
3. En modo Escritorio, abre Decky Settings → Developer → Install plugin from ZIP file y selecciona el ZIP.
4. En el panel lateral, abre Ajustes, elige el motor y la personalidad y, para narrar con LLM local, pulsa **Descargar e instalar**.

Los archivos del modelo no se incluyen en el ZIP. Se descargan dentro de los datos de NIA solo cuando el usuario lo decide. La configuración, los datos, la base de datos y los logs quedan bajo `~/.local/share/nia-decky/` (o `$XDG_DATA_HOME/nia-decky/`). La clave API se escribe con permisos `0600`.

## Desarrollo

Desde esta carpeta:

```bash
pnpm install
pnpm build
pnpm typecheck
pnpm lint
pnpm test
```

La interfaz usa TypeScript/React con `@decky/ui` y `@decky/api`; Decky ejecuta el backend Python. `scripts/pack.sh` crea el ZIP instalable de Decky.
