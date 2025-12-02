"""
Django settings for DistribucionApp project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv   # IMPORTAR DOTENV SIEMPRE

BASE_DIR = Path(__file__).resolve().parent.parent

# cargar .env desde la raíz del proyecto (donde está manage.py)
load_dotenv(BASE_DIR / ".env")

# ==========================
# CONFIGURACIÓN BÁSICA
# ==========================

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-insegura")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".app.github.dev",        # Codespaces
    ".githubpreview.dev",     # Codespaces
]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://localhost:8000",      # ← AÑADE ESTA
    "https://*.app.github.dev",
    "https://*.githubpreview.dev",
]


# ==========================
# APLICACIONES INSTALADAS
# ==========================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rutas',   # tu app
]

# ==========================
# MIDDLEWARE
# ==========================

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ==========================
# URLS Y TEMPLATES
# ==========================

ROOT_URLCONF = 'DistribucionApp.urls'

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

WSGI_APPLICATION = 'DistribucionApp.wsgi.application'

# ==========================
# BASE DE DATOS
# ==========================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ==========================
# VALIDADORES DE PASSWORD
# ==========================

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

# ==========================
# INTERNACIONALIZACIÓN
# ==========================

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'

USE_I18N = True
USE_TZ = True

# ==========================
# ARCHIVOS ESTÁTICOS
# ==========================

STATIC_URL = '/static/'

# ==========================
# DEFAULT PRIMARY KEY
# ==========================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================
# GOOGLE MAPS API
# ==========================

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

