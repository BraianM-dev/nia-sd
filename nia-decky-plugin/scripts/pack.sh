#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
NAME="nia-decky"
VERSION="${1:-$(node -p "require('./package.json').version")}" 
OUTDIR="$ROOT/out"
mkdir -p "$OUTDIR"
ARCHIVE="$OUTDIR/${NAME}-v${VERSION}.zip"
rm -f "$ARCHIVE"

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

mkdir -p "$STAGING"
cp -a "$ROOT/dist" "$STAGING/"
cp -a "$ROOT/assets" "$STAGING/"
cp -a "$ROOT/backend" "$STAGING/"
cp -a "$ROOT/bin" "$STAGING/"
cp -a "$ROOT/defaults" "$STAGING/"
cp -a "$ROOT/plugin.json" "$ROOT/package.json" "$ROOT/main.py" "$ROOT/LICENSE" "$STAGING/"

python "$ROOT/scripts/materialize_assets.py" "$STAGING/assets/images"

( cd "$STAGING" && zip -r "$ARCHIVE" . )

echo "Paquete generado en $ARCHIVE"
