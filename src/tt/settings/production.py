# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

INSTALLED_APPS += [ 'storages' ]

# Django 4.2+ uses STORAGES instead of STATICFILES_STORAGE
STORAGES = {
    "default": {

        # Media files (user uploads) e.g., Digital Ocean Spaces
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "access_key": ENV.STORAGE_ACCESS_KEY_ID,
            "secret_key": ENV.STORAGE_SECRET_ACCESS_KEY,
            "bucket_name": ENV.STORAGE_BUCKET_NAME,
            "region_name": ENV.STORAGE_REGION_NAME,
            "endpoint_url": ENV.STORAGE_ENDPOINT_URL,
            "custom_domain": ENV.STORAGE_CUSTOM_DOMAIN,
            "object_parameters": {
                'CacheControl': 'max-age=31536000, immutable',
            },
            "default_acl": 'public-read',
            "querystring_auth": False,
            "file_overwrite": False,
            "location": ENV.STORAGE_LOCATION_PREFIX,
        },
    },
    "staticfiles": {
        # Static files (CSS/JS) -> django-pipeline (served by nginx)
        "BACKEND": "pipeline.storage.PipelineManifestStorage",
    },
}

STATIC_ROOT = '/src/static'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {module} {process:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'tt': {
            'handlers': ['console' ],
            'level': 'INFO',
        },
    },
}

BASE_URL_FOR_EMAIL_LINKS = f'https://{SITE_DOMAIN}'

# Disable DRF Browsable API in production - JSON responses only
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
