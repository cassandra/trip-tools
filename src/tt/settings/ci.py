# -*- coding: utf-8 -*-
"""
CI/Testing settings - inherits from development with SQLite database.

Use this for fast test runs: DJANGO_SETTINGS_MODULE=tt.settings.ci
"""
from .development import *

# Override database to use SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ENV.DATABASES_NAME_PATH, 'tt.sqlite3'),
    }
}

# Suppress email sending during tests - write to console instead
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Suppress background monitoring tasks during tests
SUPPRESS_MONITORS = True

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
    },
}
