#!/usr/bin/env bash
set -euo pipefail

PURGE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge)
      PURGE=1
      shift
      ;;
    *)
      echo "Uso: $0 [--purge]" >&2
      exit 1
      ;;
  esac
done

PLUGIN_DIR="$HOME/homebrew/plugins/nia-decky"
DATA_DIR="$HOME/.local/share/nia-decky"

if [[ -d "$PLUGIN_DIR" ]]; then
  rm -rf "$PLUGIN_DIR"
  echo "Plugin eliminado de $PLUGIN_DIR"
else
  echo "Plugin no encontrado en $PLUGIN_DIR"
fi

if [[ $PURGE -eq 1 ]]; then
  read -r -p "Esto eliminará también datos descargados en $DATA_DIR. ¿Continuar? [y/N] " reply
  if [[ "${reply,,}" == "y" ]]; then
    rm -rf "$DATA_DIR"
    echo "Datos purgados."
  else
    echo "Purgado cancelado."
  fi
fi
