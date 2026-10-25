#!/usr/bin/env bash
# macOS/Linux equivalent of run_stage1.bat (env setup + index the originals)
set -e; cd "$(dirname "$0")"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
PHOTOS=$(.venv/bin/python -c "from config import photos_root; print(photos_root())")
echo "Indexing originals in: $PHOTOS (read-only; resumable)"
.venv/bin/python album_index.py "$PHOTOS"
