# Modelos y motores opcionales

NIA no descarga ni inicia modelos al instalarse. Desde Ajustes, el usuario puede iniciar explícitamente la descarga verificada de llama.cpp y Qwen2.5 1.5B Instruct Q4_K_M (aproximadamente 1,12 GB) para narración local en SteamOS/Game Mode. NIA instala el motor en sus propios datos, sin root ni paquetes del sistema. También se puede usar un archivo GGUF local compatible.

Como alternativa, configura Ollama (en otra máquina si no funciona en Game Mode), OpenAI API, xAI Grok, DeepSeek, Gemini u otro endpoint compatible. Los proveedores externos requieren su propia clave API y pueden cobrar por uso; ChatGPT Plus/Pro no incluye el uso de OpenAI API.

La opción Comentario contextual sin LLM no necesita modelo ni conexión. Usa el nombre del juego, el tiempo de sesión y los eventos marcados desde el panel. No afirma conocer ubicaciones, objetivos, muertes ni progreso que el juego no haya expuesto.

Para voz, instala Piper y una voz compatible manualmente, activa Piper en Ajustes e indica las rutas al ejecutable y al modelo ONNX. NIA no descarga ejecutables ni voces automáticamente.
