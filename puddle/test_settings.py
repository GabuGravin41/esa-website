import os
import pytest
from pathlib import Path
from django.test import TestCase
from django.conf import settings
from decouple import config

class TestDjangoSettings(TestCase):
    def test_base_settings(self):
        """Test basic Django settings configuration"""
        assert settings.BASE_DIR == Path(__file__).resolve().parent.parent
        assert isinstance(settings.SECRET_KEY, str)
        assert isinstance(settings.DEBUG, bool)
        assert isinstance(settings.ALLOWED_HOSTS, list)

    def test_security_settings(self):
        """Test security-related settings"""
        if not settings.DEBUG:
            assert settings.SECURE_SSL_REDIRECT is True
            assert settings.SESSION_COOKIE_SECURE is True
            assert settings.CSRF_COOKIE_SECURE is True

        assert settings.SECURE_BROWSER_XSS_FILTER is True
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
        assert settings.X_FRAME_OPTIONS == 'DENY'

    def test_database_settings(self):
        """Test database configuration"""
        assert 'default' in settings.DATABASES
        db_config = settings.DATABASES['default']
        assert 'ENGINE' in db_config
        assert 'NAME' in db_config

    def test_static_media_settings(self):
        """Test static and media files configuration"""
        assert settings.STATIC_URL == '/static/'
        assert settings.STATIC_ROOT == settings.BASE_DIR / 'staticfiles'
        assert settings.MEDIA_URL == '/media/'
        assert settings.MEDIA_ROOT == settings.BASE_DIR / 'media'

    def test_installed_apps(self):
        """Test installed applications"""
        required_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'core',
            'accounts',
            'crispy_forms',
            'allauth'
        ]
        for app in required_apps:
            assert app in settings.INSTALLED_APPS

    def test_middleware(self):
        """Test middleware configuration"""
        required_middleware = [
            'django.middleware.security.SecurityMiddleware',
            'whitenoise.middleware.WhiteNoiseMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ]
        for middleware in required_middleware:
            assert middleware in settings.MIDDLEWARE

    def test_authentication_settings(self):
        """Test authentication-related settings"""
        assert settings.LOGIN_URL == 'account_login'
        assert settings.LOGIN_REDIRECT_URL == '/'
        assert settings.LOGOUT_REDIRECT_URL == '/'
        assert settings.ACCOUNT_EMAIL_REQUIRED is True
        
        auth_backends = [
            'django.contrib.auth.backends.ModelBackend',
            'allauth.account.auth_backends.AuthenticationBackend',
        ]
        for backend in auth_backends:
            assert backend in settings.AUTHENTICATION_BACKENDS

    def test_mpesa_configuration_values(self):
        """Test M-Pesa settings have valid values"""
        assert settings.MPESA_ENVIRONMENT in ['sandbox', 'production']
        assert isinstance(settings.MPESA_CONSUMER_KEY, str)
        assert len(settings.MPESA_CONSUMER_KEY) > 0
        assert isinstance(settings.MPESA_CONSUMER_SECRET, str) 
        assert len(settings.MPESA_CONSUMER_SECRET) > 0
        assert isinstance(settings.MPESA_SHORTCODE, str)
        assert len(settings.MPESA_SHORTCODE) > 0
        assert isinstance(settings.MPESA_PASSKEY, str)
        assert len(settings.MPESA_PASSKEY) > 0
        assert isinstance(settings.MPESA_CALLBACK_URL, str)
        assert settings.MPESA_CALLBACK_URL.startswith('http')
