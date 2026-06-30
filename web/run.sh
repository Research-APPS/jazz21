#!/usr/bin/env bash
# Lanza el servidor Django de jazz21.
# Uso desde la raíz del repo (con el env jazz21 activo):
#   bash web/run.sh          → puerto 8000
#   bash web/run.sh 8765     → puerto personalizado
set -e
PORT=${1:-8000}
cd "$(dirname "$0")"
python manage.py runserver "$PORT"
