# NIA – Generador Narrativo IA

Plugin para [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) que permite crear relatos interactivos en español utilizando modelos de lenguaje locales o un endpoint remoto opcional, además de narrar las historias mediante Piper-TTS.

## Características

- Generación de historias guiada por género, tono, palabras clave y personajes.
- Soporte para modo offline mediante `llama.cpp` y modelos GGUF ligeros.
- Cliente para endpoints remotos personalizables.
- Narración con Piper-TTS en español.
- Gestión de partidas guardadas y reanudación del progreso.
- Descarga automática de modelos y voces en la primera ejecución.

## Instalación

1. Copia el repositorio a tu Steam Deck o descarga el paquete ZIP generado por CI.
2. Ejecuta el instalador:

   ```bash
   bash installer.sh
   ```

   El script detectará Steam Deck/Decky Loader, descargará los artefactos necesarios y desplegará el plugin en `~/homebrew/plugins/nia-decky`.

3. Abre el menú de Decky Loader y activa "NIA – Generador Narrativo IA".

### Parámetros del instalador

```
bash installer.sh [--zip URL_O_RUTA] [--force]
```

- `--zip`: permite especificar una URL o ruta local del paquete ZIP del plugin.
- `--force`: fuerza la reinstalación incluso si ya existe una copia.

## Archivos y datos

- Configuración: `~/.local/share/nia-decky/config.json`
- Modelos LLM: `~/.local/share/nia-decky/models/`
- Voces Piper: `~/.local/share/nia-decky/piper/`
- Partidas guardadas: `~/.local/share/nia-decky/saves/`
- Logs: `~/.local/share/nia-decky/logs/nia.log`
- El icono `assets/images/logo.png` se genera automáticamente a partir de `assets/images/logo.base64` durante el empaquetado o la instalación para evitar almacenar binarios en el repositorio.

## Endpoint remoto

En la pestaña **Ajustes** puedes habilitar el modo remoto, indicando la URL y token de autorización. El endpoint debe aceptar peticiones `POST` con cuerpo JSON:

```json
{
  "prompt": "<texto>",
  "stream": true
}
```

Y responder con fragmentos JSON que contengan `token` o `text` y opcionalmente `done`.

## Desinstalación

```
bash uninstall.sh [--purge]
```

El parámetro `--purge` elimina también los datos descargados.

## Licencias y modelos

- Los binarios de `llama.cpp` y Piper se descargan dinámicamente desde sus proyectos oficiales (ver `bin/`). Consulta las licencias respectivas antes de distribuir.
- Los modelos y voces provienen de terceros; ajusta las URL en `defaults/config.example.json` según tus fuentes confiables.

## Desarrollo

- Instala dependencias con `pnpm install`.
- Ejecuta `pnpm build` para generar `dist/index.js`.
- `pnpm lint` y `pnpm typecheck` validan calidad y tipos.
- `pnpm pack` produce un ZIP listo para instalar.

## Créditos

Creado por TuNombre/Org. Basado en Decky Loader y herramientas de código abierto.
