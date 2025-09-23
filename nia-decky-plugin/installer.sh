#!/usr/bin/env bash
set -euo pipefail

DEFAULT_ZIP_URL="https://example.org/releases/nia-decky-latest.zip"
ZIP_SOURCE="$DEFAULT_ZIP_URL"
FORCE_INSTALL=0
LOG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --zip)
      ZIP_SOURCE="$2"
      shift 2
      ;;
    --force)
      FORCE_INSTALL=1
      shift
      ;;
    --log)
      LOG="$2"
      shift 2
      ;;
    *)
      echo "Uso: $0 [--zip URL_O_RUTA] [--force]" >&2
      exit 1
      ;;
  esac
done

log() {
  echo "$1"
  if [[ -n "$LOG" ]]; then
    echo "$1" >>"$LOG"
  fi
}

fail() {
  log "[ERROR] $1"
}

HOME_DIR="$HOME"
PLUGIN_DIR="$HOME_DIR/homebrew/plugins/nia-decky"
DATA_DIR="$HOME_DIR/.local/share/nia-decky"
CONFIG_FILE="$DATA_DIR/config.json"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

log "== Instalador NIA – Generador Narrativo IA =="
log "Directorio del plugin: $PLUGIN_DIR"

if [[ -f /etc/os-release ]]; then
  source /etc/os-release
  log "Sistema detectado: ${NAME:-desconocido} ${VERSION_ID:-}" 
fi

ensure_decky() {
  if [[ -d "$HOME_DIR/homebrew" ]]; then
    log "Decky Loader presente."
    return 0
  fi
  log "Decky Loader no encontrado. Intentando instalación..."
  if command -v curl >/dev/null 2>&1; then
    curl -L https://decky.xyz/install.sh | bash || log "No se pudo instalar Decky automáticamente. Instala Decky manualmente."
  else
    log "curl no disponible; omitiendo instalación de Decky."
  fi
}

fetch_zip() {
  local target="$TMP_DIR/plugin.zip"
  if [[ -f "$ZIP_SOURCE" ]]; then
    cp "$ZIP_SOURCE" "$target"
  else
    log "Descargando paquete desde $ZIP_SOURCE"
    if command -v curl >/dev/null 2>&1; then
      curl --fail --location --output "$target" "$ZIP_SOURCE"
    elif command -v wget >/dev/null 2>&1; then
      wget -O "$target" "$ZIP_SOURCE"
    else
      fail "Necesitas curl o wget para descargar el paquete"
      exit 1
    fi
  fi
  echo "$target"
}

extract_zip() {
  local zip_file="$1"
  rm -rf "$PLUGIN_DIR"
  mkdir -p "$PLUGIN_DIR"
  unzip -q "$zip_file" -d "$TMP_DIR/unpack"
  local inner
  inner="$(find "$TMP_DIR/unpack" -maxdepth 1 -mindepth 1 -type d | head -n1)"
  if [[ -z "$inner" ]]; then
    inner="$TMP_DIR/unpack"
  fi
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$inner/" "$PLUGIN_DIR/"
  else
    cp -a "$inner/." "$PLUGIN_DIR/"
  fi
}

copy_defaults() {
  mkdir -p "$DATA_DIR"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$PLUGIN_DIR/defaults/config.example.json" "$CONFIG_FILE"
  fi
}

download_resource() {
  local label="$1" url="$2" dest="$3" checksum="$4"
  [[ -z "$url" ]] && return 0
  dest="${dest/#\~/$HOME_DIR}"
  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"
  if [[ -f "$dest" && -s "$dest" ]]; then
    log "$label ya disponible en $dest"
    return 0
  fi
  log "Descargando $label..."
  local tmp
  tmp="$(mktemp "$TMP_DIR/download.XXXX")"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --output "$tmp" "$url" || { fail "Fallo al descargar $label"; return 1; }
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$tmp" "$url" || { fail "Fallo al descargar $label"; return 1; }
  else
    fail "Necesitas curl o wget para descargar $label"
    return 1
  fi
  if [[ -n "$checksum" ]]; then
    local sha
    sha="$(sha256sum "$tmp" | awk '{print $1}')"
    if [[ "${sha,,}" != "${checksum,,}" ]]; then
      fail "Checksum inválido para $label"
      rm -f "$tmp"
      return 1
    fi
  fi
  mv "$tmp" "$dest"
  log "$label guardado en $dest"
}

prepare_binaries() {
  chmod +x "$PLUGIN_DIR"/bin/* || true
}

materialize_assets() {
  local images_dir="$PLUGIN_DIR/assets/images"
  local base64_file="$images_dir/logo.base64"
  local png_file="$images_dir/logo.png"
  [[ -f "$base64_file" ]] || return 0
  if [[ -f "$png_file" && -s "$png_file" ]]; then
    return 0
  fi
  log "Generando icono PNG desde base64"
  local tmp
  tmp="$(mktemp "$TMP_DIR/logo.XXXX")"
  if command -v base64 >/dev/null 2>&1; then
    grep -v '^#' "$base64_file" | base64 --decode >"$tmp" || {
      fail "No se pudo decodificar el icono"; return 1; }
  else
    python3 - "$base64_file" "$tmp" <<'PY'
import base64, sys
data = []
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line and not line.startswith('#'):
            data.append(line)
with open(sys.argv[2], 'wb') as out:
    out.write(base64.b64decode(''.join(data)))
PY
  fi
  mv "$tmp" "$png_file"
}

summary() {
  log "\n== Resumen =="
  du -sh "$PLUGIN_DIR" "$DATA_DIR" 2>/dev/null || true
  log "Configuración: $CONFIG_FILE"
  log "Plugin instalado. Abre el menú de Decky para iniciar NIA."
}

ensure_decky || true

if [[ -d "$PLUGIN_DIR" && $FORCE_INSTALL -eq 0 ]]; then
  log "El plugin ya está instalado. Usa --force para reinstalar."
else
  zip_file="$(fetch_zip)"
  extract_zip "$zip_file"
fi

materialize_assets || true
copy_defaults

if [[ -f "$CONFIG_FILE" ]]; then
  json_get() {
    local key="$1"
    if command -v jq >/dev/null 2>&1; then
      jq -r "$key // \"\"" "$CONFIG_FILE" 2>/dev/null || echo ""
    else
      python3 - "$CONFIG_FILE" "$key" <<'PY'
import json, sys
path = sys.argv[2]
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    data = json.load(fh)
for part in path.strip('.').split('.'):
    if not part:
        continue
    if isinstance(data, dict):
        data = data.get(part)
    else:
        data = None
        break
if data is None:
    print("")
else:
    print(data)
PY
    fi
  }

  MODEL_URL="$(json_get '.model.gguf_url')"
  MODEL_PATH="$(json_get '.model.path')"
  MODEL_CHECKSUM="$(json_get '.model.checksum')"
  download_resource "Modelo LLM" "$MODEL_URL" "$MODEL_PATH" "$MODEL_CHECKSUM" || log "Modo plantillas disponible si falla el modelo"

  VOICE_URL="$(json_get '.tts.voice_url')"
  VOICE_PATH="$(json_get '.tts.path')"
  VOICE_CHECKSUM="$(json_get '.tts.checksum')"
  download_resource "Voz Piper" "$VOICE_URL" "$VOICE_PATH" "$VOICE_CHECKSUM" || log "TTS usará modo reducido"
fi

prepare_binaries

summary

exit 0
