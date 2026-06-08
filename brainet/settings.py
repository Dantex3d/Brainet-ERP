from pathlib import Path
import os
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-development-key"
)

DEBUG = os.environ.get("DEBUG", "False") == "False"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    ".onrender.com,localhost,127.0.0.1"
).split(",")

# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    # Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your Apps
    'users',
    'schools',
    'teachers',
    'students',
    'exams',
    'reports',
    'classes',
    'assignments',
    'subjects',
]

# =========================================================
# CUSTOM USER MODEL
# =========================================================

AUTH_USER_MODEL = 'users.CustomUser'

# =========================================================
# URLS / WSGI
# =========================================================

ROOT_URLCONF = 'brainet.urls'
WSGI_APPLICATION = 'brainet.wsgi.application'

# =========================================================
# AUTHENTICATION
# =========================================================

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/teachers/dashboard/'

# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    "schools.middleware.SchoolActivationMiddleware",

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'brainet' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True
USE_TZ = True

# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# =========================================================
# MEDIA FILES
# =========================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =========================================================
# DEFAULT PRIMARY KEY FIELD
# =========================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================================================
# SECURITY FOR PRODUCTION
# =========================================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
