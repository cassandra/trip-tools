#!/bin/bash

echo "Initial Django admin initialization."
cd /src

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser and groups..."
python manage.py tt_createsuperuser
python manage.py tt_creategroups

echo "Syncing settings..."
python manage.py sync_settings

echo "Starting supervisord..."
exec "$@"
