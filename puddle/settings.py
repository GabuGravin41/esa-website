import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-unsafe-default-key-change-me')
DEBUG = config('DEBUG', default=False, cast=bool)

# Security headers and hosts
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS', 
    default='localhost,127.0.0.1,.onrender.com',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://esa-ku.com',
    *config(
        'CSRF_TRUSTED_ORIGINS',
        default='http://localhost,http://127.0.0.1',
        cast=lambda v: [s.strip() for s in v.split(',')]
    )
]

# Security headers
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Local apps
    'core',
    'accounts',
    
    # Third-party apps
    'crispy_forms',
    'crispy_tailwind',
    'allauth',
    'allauth.account',
    'widget_tweaks',
]

# Development-only apps
if DEBUG:
    try:
        import django_browser_reload
        INSTALLED_APPS += ['django_browser_reload']
    except ImportError:
        pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.LoginRedirectMiddleware',  # Handle login redirects gracefully
    'core.middleware.ErrorHandlingMiddleware',  # Custom error handling
    'allauth.account.middleware.AccountMiddleware',
]

# Add browser reload middleware only in development
if DEBUG:
    try:
        import django_browser_reload
        MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')
    except ImportError:
        pass

ROOT_URLCONF = 'puddle.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'puddle.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases



# Default to SQLite for development
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'  # or 'mandatory' for production
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core/static'),
]

# Media files (Uploaded files)
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Whitenoise configuration
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Storage configuration
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# django-allauth registration settings
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"  # Emails will be printed to console in development
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# Authentication settings
LOGIN_URL = 'account_login'  # Custom login URL for @login_required decorator
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Payment API Settings
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', default='')
MPESA_PASSKEY = config('MPESA_PASSKEY', default='')
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL', default='')

# PayPal Settings
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID', default='')
PAYPAL_SECRET = config('PAYPAL_SECRET', default='')
PAYPAL_MODE = config('PAYPAL_MODE', default='sandbox')

# Email settings
# Choose the appropriate email backend based on environment
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='esa.kenyattauniv@gmail.com')

# Configure a timeout (in seconds) for email sending
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=30, cast=int)

# Email display name format: "ESA-KU <esa.kenyattauniv@gmail.com>"
if DEFAULT_FROM_EMAIL and '@' in DEFAULT_FROM_EMAIL and not DEFAULT_FROM_EMAIL.startswith('ESA-KU'):
    DEFAULT_FROM_EMAIL = f'ESA-KU <{DEFAULT_FROM_EMAIL}>'

# Define the site URL for use in emails (used for links in emails)
SITE_URL = config('SITE_URL', default='http://localhost:8000' if DEBUG else 'https://esa-ku.com')

# Error Handling
ADMINS = [('Admin', config('ADMIN_EMAIL', default='esa.kenyattauniv@gmail.com'))]
SERVER_EMAIL = config('SERVER_EMAIL', default='esa.kenyattauniv@gmail.com')

# Logging Configuration
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
        'level': 'WARNING',
    },
}

# ======================
# SECURITY
# ======================
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_SAVE_EVERY_REQUEST = True


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ALLAUTH_UI_THEME = "light"
LOGIN_REDIRECT_URL = "/"

DEFAULT_USER_ID = 1

# # M-Pesa Daraja API Settings
# MPESA_ENVIRONMENT = 'sandbox'
# MPESA_CONSUMER_KEY = 'UhAvV2Jp7EkeybZ6XGmCbb3K24E36HGOslh4EH24H5T822p3'
# MPESA_CONSUMER_SECRET = '9dYJFaeO7QrQp6S6ung6WE7QXjfnCq4TNhmGcKTUKlAHJ8NvS6A8vBIShXPGO4jR'

# MPESA_SHORTCODE = '174379'  
# MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
# MPESA_CALLBACK_URL = 'https://esa-website-2.onrender.com/'

# M-Pesa Daraja API Settings
MPESA_ENVIRONMENT = config('MPESA_ENVIRONMENT', default='sandbox')
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = config('MPESA_SHORTCODE')
MPESA_PASSKEY = config('MPESA_PASSKEY')
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL')
MPESA_REFERENCE = config('MPESA_REFERENCE', default='ESA-KU')
MPESA_SIMULATE_IN_DEV = config('MPESA_SIMULATE_IN_DEV', default=True, cast=bool)

# PayPal Settings
PAYPAL_ENVIRONMENT = 'sandbox'  # Change to 'production' for live environment
PAYPAL_CLIENT_ID = 'your_client_id'
PAYPAL_CLIENT_SECRET = 'your_client_secret'