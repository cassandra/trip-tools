#!/bin/bash
#
# Set up the E2E test database.
#
# Uses a pre-migrated template database for speed. If the template doesn't
# exist, creates it after running migrations.
#
# Usage: ./setup-db.sh
#

set -e

E2E_DB="/tmp/tt-e2e-test.sqlite3"
TEMPLATE_DB="/tmp/tt-e2e-template.sqlite3"
SETTINGS="tt.settings.e2e"

cd "$(dirname "$0")/../../src"

# Remove existing test database
rm -f "$E2E_DB"

# If template exists, copy it (much faster than running migrations)
if [ -f "$TEMPLATE_DB" ]; then
    cp "$TEMPLATE_DB" "$E2E_DB"
fi

# Run migrations (fast if template was current, creates DB if no template)
DJANGO_SETTINGS_MODULE=$SETTINGS python manage.py migrate --run-syncdb --verbosity=0

# If no template existed, save this as the new template
if [ ! -f "$TEMPLATE_DB" ]; then
    cp "$E2E_DB" "$TEMPLATE_DB"
fi

# Seed test data
DJANGO_SETTINGS_MODULE=$SETTINGS python manage.py seed_e2e_data --quiet
