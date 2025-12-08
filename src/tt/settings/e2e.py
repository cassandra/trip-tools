# -*- coding: utf-8 -*-
"""
E2E Testing settings - isolated SQLite database for Playwright tests.

Use this for E2E tests: DJANGO_SETTINGS_MODULE=tt.settings.e2e

The database file can be deleted between test runs to reset state.
"""
from .development import *

# E2E tests use a dedicated SQLite database file
# Delete this file to reset test state: rm -f /tmp/tt-e2e-test.sqlite3
E2E_DATABASE_PATH = '/tmp/tt-e2e-test.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': E2E_DATABASE_PATH,
    }
}

# Suppress email sending during tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Suppress background monitoring tasks during tests
SUPPRESS_MONITORS = True

# Password for the test signin endpoint at /testing/signin/
# This endpoint only exists when DEBUG=True (tt.testing app is installed)
E2E_TEST_PASSWORD = 'e2e-test-password'

# Minimal logging for cleaner test output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'tt': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}
