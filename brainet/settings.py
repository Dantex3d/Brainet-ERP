from pathlib import Path
import importlib
import os
from django.core.exceptions import ImproperlyConfigured

dotenv = importlib.util.find_spec('dotenv')
if dotenv is not None:
    load_dotenv = importlib.import_module('dotenv').load_dotenv
else:
    load_dotenv = lambda *args, **kwargs: None

try:
    dj_database_url = importlib.import_module('dj_database_url')
except ImportError:
    dj_database_url = None

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

# DEBUG mode (default True for development)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    "brainetanalytics.co.ke",
    "www.brainetanalytics.co.ke",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://brainetanalytics.co.ke",
    "https://www.brainetanalytics.co.ke",
]

# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    # Django Apps
    'brainet',
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
    'fees',

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
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1209600  # 2 weeks: used when remember me is selected

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
    "schools.middleware.ErrorReporterMiddleware",

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
    if dj_database_url is not None:
        DATABASES = {
            "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
        }
    else:
        raise ImproperlyConfigured(
            "DATABASE_URL is set but the 'dj_database_url' package is not installed"
        )
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
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@brainetanalytics.co.ke')
DEFAULT_FROM_EMAIL = "no-reply@brainetanalytics.co.ke"
SERVER_EMAIL = "no-reply@brainetanalytics.co.ke"
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')



# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

WHITENOISE_ROOT = BASE_DIR / 'static'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    }
}

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
USE_CLOUDINARY = os.environ.get('USE_CLOUDINARY', 'False') == 'True'
USE_S3 = os.environ.get('USE_S3', 'False') == 'True' or bool(os.environ.get('AWS_STORAGE_BUCKET_NAME'))

if USE_CLOUDINARY:
    INSTALLED_APPS.extend(['cloudinary', 'cloudinary_storage'])
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    STORAGES = {
        'default': {
            'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        }
    }
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
        'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
        'SECURE': True,
    }
    MEDIA_URL = os.environ.get('MEDIA_URL') or (
        f"https://res.cloudinary.com/{CLOUDINARY_STORAGE['CLOUD_NAME']}/image/upload/"
        if CLOUDINARY_STORAGE['CLOUD_NAME'] else '/media/'
    )
elif USE_S3:
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
