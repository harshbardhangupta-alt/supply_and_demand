#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
. ../.venv/bin/activate
python -m pytest -q
