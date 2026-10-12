#!/usr/bin/env bash
set -euo pipefail
ZIP_SOURCE=""
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --zip) ZIP_SOURCE="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "Uso: $0 [--zip ARCHIVO] [--force]" >&2; exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/plugin.json" ]]; then
  SOURCE_DIR="$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/nia-decky-plugin/plugin.json" ]]; then
  SOURCE_DIR="$SCRIPT_DIR/nia-decky-plugin"
else
  SOURCE_DIR=""
fi
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
if [[ -n "$ZIP_SOURCE" ]]; then
  unzip -q "$ZIP_SOURCE" -d "$TMP_DIR/unpacked"
  SOURCE_DIR="$(find "$TMP_DIR/unpacked" -type f -name plugin.json -printf '%h\n' | head -n1)"
fi
if [[ -z "$SOURCE_DIR" || ! -s "$SOURCE_DIR/dist/index.js" ]]; then
  echo "No se encontró un plugin construido. Ejecuta pnpm install y pnpm build primero." >&2
  exit 1
fi
HOME_DIR="${HOME:?No se encontró HOME}"
PLUGIN_DIR="$HOME_DIR/homebrew/plugins/nia-decky"
if [[ ! -d "$HOME_DIR/homebrew/plugins" ]]; then
  echo "Decky Loader no está instalado en este usuario. Instala Decky Loader y vuelve a ejecutar." >&2
  exit 1
fi
if [[ -e "$PLUGIN_DIR" && "$FORCE" -ne 1 ]]; then
  echo "NIA ya existe en $PLUGIN_DIR. Usa --force para reemplazarla." >&2
  exit 1
fi
STAGE="$TMP_DIR/nia-decky"
mkdir -p "$STAGE"
for path in dist assets backend bin defaults; do cp -a "$SOURCE_DIR/$path" "$STAGE/"; done
for path in plugin.json package.json main.py LICENSE README.md; do cp -a "$SOURCE_DIR/$path" "$STAGE/"; done
if [[ -e "$PLUGIN_DIR" ]]; then
  mv "$PLUGIN_DIR" "$PLUGIN_DIR.backup.$(date +%Y%m%d%H%M%S)"
fi
mv "$STAGE" "$PLUGIN_DIR"
echo "NIA instalado en $PLUGIN_DIR"
echo "La configuración y el historial se guardan en ~/.local/share/nia-decky"
