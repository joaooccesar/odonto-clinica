#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/configure.py
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
if ! .venv/bin/python manage.py shell -c "from accounts.models import User; import sys; sys.exit(0 if User.objects.filter(is_superuser=True,is_active=True).exists() else 1)"; then
  .venv/bin/python manage.py createsuperuser
fi
.venv/bin/python manage.py runserver 127.0.0.1:8000
