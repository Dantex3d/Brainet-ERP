#!/usr/bin/env bash
set -o errexit

python manage.py migrate
python manage.py createsuperuser --noinput || true
gunicorn brainet.wsgi:application --bind 0.0.0.0:8000