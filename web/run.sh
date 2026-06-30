#!/usr/bin/env bash
# Lanza el servidor Django de jazz21 (puerto 8000 por defecto).
#
# Setup (una vez, desde la raíz del repo, env jazz21 activo):
#   pip install -r web/requirements.txt
#   cd web && python manage.py migrate
#   JAZZ21_ADMIN_PASSWORD=… python manage.py seed_admin
#
# Arrancar servidor:
#   bash web/run.sh          # desde la raíz del repo
#   bash run.sh              # si ya estás en web/
#   python manage.py runserver # equivalente estando en web/
set -e
PORT=${1:-8000}
cd "$(dirname "$0")"
python manage.py runserver "$PORT"
