#!/usr/bin/env bash
# One-time setup for Linux/macOS.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Backend: creating virtualenv and installing deps"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env

echo "==> Frontend: installing deps"
cd frontend && npm install && cd ..
[ -f frontend/.env.local ] || cp frontend/.env.local.example frontend/.env.local

echo "Done. Start the backend with scripts/dev_backend.sh and the frontend with scripts/dev_frontend.sh"
