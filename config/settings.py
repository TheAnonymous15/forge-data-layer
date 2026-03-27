# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Settings
=======================================
Django settings for the centralized data layer microservice.
"""
import os
from pathlib import Path
from datetime import timedelta

import dj_database_url
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment
DATA_LAYER_ENV = os.getenv('DATA_LAYER_ENV', 'development')
IS_PRODUCTION = DATA_LAYER_ENV == 'production'

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

# API Service ↔ Data Layer Signing (Shared Secret)
# Must match the API Service's API_DATA_LAYER_SECRET
API_DATA_LAYER_SECRET = os.getenv('API_DATA_LAYER_SECRET', 'ff_api_data_layer_secret_2026_secure')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    'data.forgeforthafrica.com',
    'www.data.forgeforthafrica.com',
]

if DEBUG:
    ALLOWED_HOSTS.append('*')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',


    'core',
    # Core
    # Data Layer Apps
    'api_service',
    'data_layer',
    'authentication',
    'users',
    'profiles',
    'organizations',
    'opportunities',
    'applications',
    'tokens',
    'audit',
    'media',
    'administration',
    'analytics',
    'communications',
    'intelligence',
    'matching',
    'security',
    'storage',
    'website',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Data layer signature verification
    'config.middleware.DataLayerSignatureMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database Configuration
# In development/dev mode, use test database to protect production data
# In production, use the real database

IS_DEV_MODE = DATA_LAYER_ENV.lower() in ('development', 'dev', '1', 'true')

if IS_DEV_MODE:
    # Development: Use test database
    TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', f'sqlite:///{BASE_DIR}/test_data_layer.sqlite3')
    DATABASE_URL = TEST_DATABASE_URL
    print(f"[Data Layer] Running in DEVELOPMENT mode - using TEST database")
else:
    # Production: Use real database
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/data_layer.sqlite3')
    print(f"[Data Layer] Running in PRODUCTION mode - using PRODUCTION database")

DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Keep reference to both databases for potential switching
PRODUCTION_DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/data_layer.sqlite3')
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', f'sqlite:///{BASE_DIR}/test_data_layer.sqlite3')

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:8000').split(',')
]
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
    'SIGNING_KEY': os.getenv('JWT_SECRET_KEY', SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF Spectacular (API Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'ForgeForth Africa - Data Layer API',
    'DESCRIPTION': 'Centralized data service for all ForgeForth Africa platform operations',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'TAGS': [
        {'name': 'users', 'description': 'User management operations'},
        {'name': 'profiles', 'description': 'Talent profile operations'},
        {'name': 'organizations', 'description': 'Organization operations'},
        {'name': 'opportunities', 'description': 'Opportunity/Job operations'},
        {'name': 'applications', 'description': 'Application operations'},
        {'name': 'tokens', 'description': 'Token management (verification, reset, etc.)'},
        {'name': 'audit', 'description': 'Audit log operations'},
    ],
}

# Redis Cache
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Service Authentication
DATA_LAYER_API_KEY = os.getenv('DATA_LAYER_API_KEY', 'dev-api-key')
DATA_LAYER_SIGNING_KEY = os.getenv('DATA_LAYER_SIGNING_KEY', 'data-layer-signing-key-dev')
REQUIRE_DATA_LAYER_SIGNING = os.getenv('REQUIRE_DATA_LAYER_SIGNING', 'False').lower() in ('true', '1', 'yes')
ALLOWED_SERVICE_IDS = [
    s.strip() for s in os.getenv('ALLOWED_SERVICE_IDS', 'api-service').split(',')
]

# Logging
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'data_layer.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'data_layer': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'DEBUG'),
            'propagate': False,
        },
    },
}

# Security settings for production
if IS_PRODUCTION:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# =============================================================================
# Email Configuration
# =============================================================================
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'mail.forgeforthafrica.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'ForgeForth Africa <mailer@forgeforthafrica.com>')
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', 'info@forgeforthafrica.com')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@forgeforthafrica.com')

# For development, optionally use console backend
if DEBUG and not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =============================================================================
# Service URLs for Email Links
# =============================================================================
TALENT_PORTAL_URL = os.getenv('TALENT_PORTAL_URL', 'http://localhost:9003')
MAIN_WEBSITE_URL = os.getenv('MAIN_WEBSITE_URL', 'https://forgeforthafrica.com')
API_SERVICE_URL = os.getenv('API_SERVICE_URL', 'http://localhost:9001')
