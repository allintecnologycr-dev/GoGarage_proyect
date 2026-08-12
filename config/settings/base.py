"""
Django settings for GoGarage — configuración base compartida por dev y prod.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import Csv, config

# config/settings/base.py -> sube 3 niveles para llegar a la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-env")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "storages",
    # Apps propias (dominio)
    "apps.core",
    "apps.clientes",
    "apps.ordenes",
    "apps.inventario",
    "apps.facturacion",
    "apps.publico",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Nota: el taller (tenant) activo NO se resuelve en middleware de Django,
# porque la autenticación JWT de DRF ocurre después del middleware (dentro
# de dispatch()). Se resuelve en la permission class TienerTallerActivo
# (ver apps/core/permissions.py y apps/core/tenancy.py).

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Base de datos
# En producción, DATABASE_URL apunta a Supabase (Postgres administrado).
# En desarrollo, por defecto usa sqlite si no se define DATABASE_URL.
# Nota: se usa config()+parse() (no dj_database_url.config()) porque este
# último lee os.environ directamente, y python-decouple no vuelca el .env
# ahí — con .config() a secas, DATABASE_URL del .env se ignoraba siempre.
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "core.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = config("TIME_ZONE", default="America/Costa_Rica")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Almacenamiento de archivos (fotos de EvidenciaFoto, ver apps/ordenes/models.py).
# En producción usa Supabase Storage (S3-compatible) vía django-storages; si
# SUPABASE_STORAGE_BUCKET_NAME no está configurado (por defecto en desarrollo),
# cae a disco local para no depender de credenciales de Supabase en local.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

SUPABASE_STORAGE_BUCKET_NAME = config("SUPABASE_STORAGE_BUCKET_NAME", default="")

STORAGES = {
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if SUPABASE_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": SUPABASE_STORAGE_BUCKET_NAME,
            "access_key": config("SUPABASE_S3_ACCESS_KEY_ID"),
            "secret_key": config("SUPABASE_S3_SECRET_ACCESS_KEY"),
            "endpoint_url": config("SUPABASE_S3_ENDPOINT_URL"),
            "region_name": config("SUPABASE_S3_REGION_NAME", default="us-east-1"),
            "addressing_style": "path",
            "default_acl": "public-read",
            "querystring_auth": False,
            "file_overwrite": False,
        },
    }
else:
    STORAGES["default"] = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    # Rate limiting específico de los endpoints públicos (apps.publico) para
    # evitar fuerza bruta sobre los tokens (ver docs/ARQUITECTURA.md sección 8).
    "DEFAULT_THROTTLE_RATES": {
        "publico": "30/min",
    },
}

# URL base pública del backend, usada para armar el link que se comparte por
# WhatsApp (apps/ordenes/serializers.py:CotizacionSerializer.get_link_publico).
SITE_PUBLIC_BASE_URL = config("SITE_PUBLIC_BASE_URL", default="http://localhost:8000")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS: orígenes del/los frontend(s) separados que consumen esta API
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:3000", cast=Csv()
)

# Celery + Redis
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Ninguna vista consulta el resultado de una tarea vía AsyncResult (todas
# son fire-and-forget con .delay()); con esto, .delay() no intenta abrir
# una conexión al backend de resultados al encolar — sin esto, si Redis
# está caído, .delay() se queda reintentando esa conexión ~1 minuto antes
# de fallar, colgando la request del usuario que cierra la orden/responde
# la cotización.
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_TIMEOUT = 3
