from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
import smtplib
# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env at project root (development only)
load_dotenv(BASE_DIR / '.env')

# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-development-key"
)

DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    "brainetanalytics.co.ke",
    "www.brainetanalytics.co.ke",
    "brainet.up.railway.app",
    "brainet-erp.vercel.app",
    "localhost",
    "127.0.0.1",
]
    
CSRF_TRUSTED_ORIGINS = [
    "https://brainetanalytics.co.ke",
    "https://www.brainetanalytics.co.ke",
    "https://brainet.up.railway.app",
]

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
    'django.contrib.sitemaps',

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
# EMAIL / NOTIFICATIONS
# =========================================================

SITE_NAME = os.environ.get('SITE_NAME', 'Brainet Analytics')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'info@brainetanalytics.co.ke')
DEFAULT_FROM_EMAIL = "info@brainetanalytics.co.ke"
SERVER_EMAIL = "info@brainetanalytics.co.ke"
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')



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
# REMOTE MEDIA (S3) - optional
# If you want uploaded files to be stored on S3/GCS, set USE_S3=True or
# provide AWS_STORAGE_BUCKET_NAME and related env vars. Install
# `django-storages[boto3]` and `boto3` and configure the environment variables.
# =========================================================
USE_S3 = os.environ.get('USE_S3', 'False') == 'True' or bool(os.environ.get('AWS_STORAGE_BUCKET_NAME'))
if USE_S3:
    # Only add 'storages' app when S3 is enabled to avoid import errors when not installed
    INSTALLED_APPS.append('storages')
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', None)
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN') or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    MEDIA_URL = os.environ.get('MEDIA_URL') or f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
else:
    # Use local MEDIA_ROOT / MEDIA_URL (defined above)
    pass

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
    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True