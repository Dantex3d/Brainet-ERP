"""
Local settings for development and testing.
This file extends settings.py and overrides specific settings for local development.
"""

# Import all settings from base settings
from .settings import *
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env from project root if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# DEBUG & SECURITY - Override for Local Development
# =========================================================
DEBUG = True
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '0.0.0.0']

# Prevent local dev from forcing HTTPS
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_PROXY_SSL_HEADER = None

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
# EMAIL - prefer .env values but default to console backend for safety
# =========================================================
SITE_NAME = os.environ.get('SITE_NAME', globals().get('SITE_NAME', 'Brainet'))
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', globals().get('SUPPORT_EMAIL', os.environ.get('DEFAULT_FROM_EMAIL', globals().get('EMAIL_HOST_USER', 'support@brainet.local'))))
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', globals().get('EMAIL_HOST', 'smtp.zoho.com'))
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', globals().get('EMAIL_PORT', 587)))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', str(globals().get('EMAIL_USE_TLS', True))) in ('True', 'true', '1')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', globals().get('EMAIL_HOST_USER'))
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', globals().get('EMAIL_HOST_PASSWORD'))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', globals().get('DEFAULT_FROM_EMAIL', 'no-reply@brainet.local'))
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', globals().get('EMAIL_TIMEOUT', 10)))

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
