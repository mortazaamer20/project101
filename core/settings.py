
from pathlib import Path
import environ
import os

env = environ.Env(
    DEBUG=(bool, False),
    CORS_ALLOW_CREDENTIALS=(bool, False),
    CORS_PREFLIGHT_MAX_AGE=(int, 86400),
)


BASE_DIR = Path(__file__).resolve().parent.parent


environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')



environ.Env.read_env(BASE_DIR / '.env')


X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

DEBUG = env('DEBUG')




DATABASES = {
    'default': env.db(),  # Parses DATABASE_URL
}



APNS_TEAM_ID = os.getenv('APNS_TEAM_ID', 'YOUR_TEAM_ID')  # Not used directly in ApnsConfig
APNS_AUTH_KEY_ID = os.getenv('APNS_KEY_ID', 'YOUR_KEY_ID')
APNS_AUTH_KEY_PATH = os.getenv('APNS_BUNDLE_ID', 'com.example.yourapp')
APNS_BUNDLE_ID = os.getenv('APNS_AUTH_KEY', '/path/to/AuthKey_XXXXXXXXXX.p8')
APNS_USE_SANDBOX = os.getenv('APNS_USE_SANDBOX', 'True') == 'True'  # True for sandbox, False for production



TELEGRAM_CHAT_ID = env('TELEGRAM_CHAT_ID')
TELEGRAM_BOT_TOKEN= env('TELEGRAM_BOT_TOKEN')




TWILIO_ACCOUNT_SID= env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN=env('TWILIO_AUTH_TOKEN')
TWILIO_VERIFY_SERVICE_SID=env('TWILIO_VERIFY_SERVICE_SID')


ALLOWED_HOSTS = []


CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
CORS_EXPOSE_HEADERS = env.list('CORS_EXPOSE_HEADERS')


INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'api',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'drf_yasg',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SITE_ID = 1

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases



# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'ar'

TIME_ZONE = 'Asia/baghdad'

USE_I18N = True

USE_L10N = True

USE_TZ = True



STATIC_URL = '/static/'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}