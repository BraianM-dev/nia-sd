#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
VERSION="${1:-$(node -e "console.log(require(process.argv[1]).version)" "$ROOT/package.json")}"
OUTDIR="$ROOT/out"
mkdir -p "$OUTDIR"
ARCHIVE="$OUTDIR/nia-decky-v${VERSION}.zip"
rm -f "$ARCHIVE" "$OUTDIR/nia-decky-latest.zip"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT
for path in dist assets backend bin defaults; do
  [[ -d "$ROOT/$path" ]] || { echo "Falta $path" >&2; exit 1; }
  cp -a "$ROOT/$path" "$STAGING/"
done
for path in plugin.json package.json main.py LICENSE README.md; do
  [[ -f "$ROOT/$path" ]] || { echo "Falta $path" >&2; exit 1; }
  cp -a "$ROOT/$path" "$STAGING/"
done
python3 "$ROOT/scripts/materialize_assets.py" "$STAGING/assets/images"
test -s "$STAGING/dist/index.js"
( cd "$STAGING" && zip -qr "$ARCHIVE" . )
cp "$ARCHIVE" "$OUTDIR/nia-decky-latest.zip"
echo "Paquetes generados: $ARCHIVE y $OUTDIR/nia-decky-latest.zip"
