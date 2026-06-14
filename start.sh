#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi
if [ ! -f data/index.json ]; then
  echo "Building index..."
  ./.venv/bin/python scripts/build_index.py
fi
echo ""
echo "AEF Self-Study running at http://127.0.0.1:8000"
echo "Press Ctrl+C to stop."
echo ""
exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
