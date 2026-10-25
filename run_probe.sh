#!/usr/bin/env bash
set -e; cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./setup.sh first"; exit 1; }
.venv/bin/python probe_heic.py "$@"
