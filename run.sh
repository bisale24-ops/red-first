#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH=src "${PYTHON:-.venv/bin/python}" -m redfirst.cli "$@"
