# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Override template options for development debugging
TEMPLATES[0]['OPTIONS'].update({
    'debug': True,
    #'string_if_invalid': 'INVALID_VARIABLE_%s',
})

INSTALLED_APPS += [ 'tt.testing' ]

STATIC_ROOT = '/tmp/tt/static'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Since the API status gets polled frequently, this gums up the
    # terminal and make developing and debugging everything else more
    # unpleasant.
    #
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
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'tt.apps.console': {
            'handlers': ['console' ],
            'level': 'INFO',
            'propagate': False,
        },
        'tt': {
            'handlers': ['console' ],
            'level': 'INFO',
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',  # Changed from DEBUG to INFO to reduce verbose variable lookup messages
            'propagate': False,
        },
    },
}

BASE_URL_FOR_EMAIL_LINKS = 'http:/127.0.0.1:8411/'

# Uncomment to suppress email sending and write to console.
#
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SUPPRESS_MONITORS = False

# ====================
# Development Testing Injection Points
# Enable/disable these here for frontend testing

# For testing UI error display of the various attribute editing form errors.
DEBUG_INJECT_ATTRIBUTE_FORM_ERRORS = False
