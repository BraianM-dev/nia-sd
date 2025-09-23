# Modelos descargables

Este directorio no almacena los modelos por defecto para mantener el repositorio liviano. Durante la instalación o la primera ejecución el plugin descargará automáticamente:

- **Modelo LLM** cuantizado (formato GGUF) de aproximadamente 3-4B parámetros en calidad Q4, optimizado para ejecución en la Steam Deck sin GPU dedicada.
- **Modelo de voz Piper-TTS** en español (variante neutral) compatible con el binario `piper` incluido en `bin/`.

Los archivos se guardarán en `~/.local/share/nia-decky/models/` y `~/.local/share/nia-decky/piper/` respectivamente. Consulta `defaults/config.example.json` para modificar las URL de descarga si cuentas con espejos propios.

Cada descarga verifica integridad mediante checksum SHA256 y se reintenta automáticamente en caso de cortes de conexión.
