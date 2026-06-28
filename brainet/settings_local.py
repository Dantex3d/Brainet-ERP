"""
Local settings for development and testing.
This file extends settings.py and overrides specific settings for local development.
"""

# Import all settings from base settings
from .settings import *
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# DEBUG & SECURITY - Override for Local Development
# =========================================================
DEBUG = True
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '0.0.0.0']

# Use a simple test secret key
SECRET_KEY = 'test-secret-key-for-development-and-testing-only'

# =========================================================
# DATABASE - Use SQLite for Testing
# =========================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =========================================================
# EMAIL - Use Console Backend for Testing
# =========================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =========================================================
# CACHE - Use Dummy Cache for Testing
# =========================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# =========================================================
# PASSWORD VALIDATION - Simplified for Testing
# =========================================================
AUTH_PASSWORD_VALIDATORS = []

# =========================================================
# LOGGING - Minimal for Testing
# =========================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
