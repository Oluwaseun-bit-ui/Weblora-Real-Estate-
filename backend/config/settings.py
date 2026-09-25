"""
Django settings for the property discovery & verification platform.

Kept deliberately explicit (rather than magic env parsing everywhere) so the
architecture is easy to audit. Secrets are read from environment variables /
.env (via python-decouple) and never committed.
"""
from pathlib import Path
from celery.schedules import crontab
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core ---------------------------------------------------------------
SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
DJANGO_ENV = config("DJANGO_ENV", default="development")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # 3rd party
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # local apps
    "apps.core",
    "apps.accounts",
    "apps.agencies",
    "apps.properties",
    "apps.sources",
    "apps.verification",
    "apps.leads",
    "apps.live_viewing",
    "apps.web_search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database -------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="realestate"),
        "USER": config("DB_USER", default="realestate"),
        "PASSWORD": config("DB_PASSWORD", default="realestate"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / time ------------------------------------------------------------
LANGUAGE_CODE = "en-us"
# Initial market is Lagos, Nigeria. All datetimes are stored UTC and
# rendered in this timezone; USE_TZ=True keeps everything timezone-aware.
TIME_ZONE = config("TIME_ZONE", default="Africa/Lagos")
USE_I18N = True
USE_TZ = True

# --- Static / media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

USE_S3 = config("USE_S3", default=False, cast=bool)
if USE_S3:
    # Property/agency images live in external object storage, never in
    # Postgres. Any S3-compatible provider works (AWS S3, DO Spaces, R2).
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default=None)
    AWS_DEFAULT_ACL = "public-read"
    AWS_QUERYSTRING_AUTH = False
else:
    MEDIA_URL = "media/"
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("FRONTEND_ORIGIN", default="http://localhost:5173", cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# --- DRF ----------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "300/min",
        "lead_submit": "10/min",
        "live_viewing_request": "20/min",
        "web_search": "20/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Property Discovery & Verification Platform API",
    "DESCRIPTION": "Customer search, agency verification and live viewing API.",
    "VERSION": "0.1.0",
}

# --- Celery -----------------------------------------------------------------
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=DEBUG, cast=bool)
CELERY_BEAT_SCHEDULE = {
    # Each source's own sync_frequency_minutes (default daily) decides
    # whether it's actually due; this just wakes the checker up.
    "sync-due-sources": {
        "task": "apps.sources.tasks.sync_due_sources_task",
        "schedule": crontab(minute=0, hour=2),
    },
}

# --- Web search (Option A: live results from the wider web) ---------------
BRAVE_SEARCH_API_KEY = config("BRAVE_SEARCH_API_KEY", default="")
WEB_SEARCH_RESULT_COUNT = config("WEB_SEARCH_RESULT_COUNT", default=10, cast=int)
WEB_SEARCH_CACHE_SECONDS = config("WEB_SEARCH_CACHE_SECONDS", default=60 * 60, cast=int)

# --- Email --------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@example.com")

# --- Maps (configurable provider; frontend reads MAP_PROVIDER via a
# lightweight /api/config endpoint rather than hard-coding a vendor) --------
MAP_PROVIDER = config("MAP_PROVIDER", default="maplibre")
MAPBOX_ACCESS_TOKEN = config("MAPBOX_ACCESS_TOKEN", default="")
GOOGLE_MAPS_API_KEY = config("GOOGLE_MAPS_API_KEY", default="")

# --- Regulatory verification providers (see apps/verification/providers) ---
ESVARBON_VERIFY_URL = config("ESVARBON_VERIFY_URL", default="https://portal.esvarbon.gov.ng/pages/verify")
ESVARBON_REGISTER_URL = config("ESVARBON_REGISTER_URL", default="https://www.esvarbon.gov.ng/register-of-esvs/")
LASRERA_INFO_URL = config("LASRERA_INFO_URL", default="https://lasrera.lagosstate.gov.ng/")
CAC_PUBLIC_SEARCH_URL = config("CAC_PUBLIC_SEARCH_URL", default="https://search.cac.gov.ng/")

# --- Live viewing provider (see apps/live_viewing/providers) ---------------
LIVE_VIEWING_PROVIDER = config("LIVE_VIEWING_PROVIDER", default="none")
LIVEKIT_API_KEY = config("LIVEKIT_API_KEY", default="")
LIVEKIT_API_SECRET = config("LIVEKIT_API_SECRET", default="")
LIVEKIT_URL = config("LIVEKIT_URL", default="")
AGORA_APP_ID = config("AGORA_APP_ID", default="")
AGORA_APP_CERTIFICATE = config("AGORA_APP_CERTIFICATE", default="")
DAILY_API_KEY = config("DAILY_API_KEY", default="")
TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_API_KEY_SID = config("TWILIO_API_KEY_SID", default="")
TWILIO_API_KEY_SECRET = config("TWILIO_API_KEY_SECRET", default="")

# Live viewing session no-show timeout (minutes) before an accepted booking
# that never went LIVE is auto-marked NO_SHOW.
LIVE_VIEWING_NO_SHOW_TIMEOUT_MINUTES = config("LIVE_VIEWING_NO_SHOW_TIMEOUT_MINUTES", default=20, cast=int)

# --- Logging ------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# --- Security -------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = config("FRONTEND_ORIGIN", default="http://localhost:5173", cast=Csv())

# File upload hardening
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
ALLOWED_UPLOAD_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
