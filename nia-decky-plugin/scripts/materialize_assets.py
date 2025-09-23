#!/usr/bin/env python3
"""Utility to recreate binary assets from text-safe sources."""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path


def decode_logo(images_dir: Path) -> None:
    base64_file = images_dir / "logo.base64"
    if not base64_file.exists():
        return
    png_path = images_dir / "logo.png"
    data_lines = []
    for line in base64_file.read_text(encoding="utf-8").splitlines():
        striped = line.strip()
        if not striped or striped.startswith("#"):
            continue
        data_lines.append(striped)
    if not data_lines:
        raise SystemExit(f"No base64 data found in {base64_file}")
    png_path.write_bytes(base64.b64decode("".join(data_lines)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "assets" / "images",
        help="Directory containing the base64 assets",
    )
    args = parser.parse_args()
    decode_logo(args.root)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - packaging helper
        print(f"materialize_assets failed: {exc}", file=sys.stderr)
        raise
