"""Django settings for the Gomoku project."""

import os
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"{name} must be set")
    return value


def database_config(url: str) -> dict[str, str | int]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ImproperlyConfigured("DATABASE_URL is invalid") from exc
    if (
        parsed.scheme not in ("postgres", "postgresql")
        or port == 0
        or not parsed.hostname
        or not parsed.username
        or not parsed.password
        or not parsed.path.strip("/")
        or parsed.path.count("/") != 1
        or parsed.query
        or parsed.fragment
    ):
        raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL connection URL")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path[1:]),
        "USER": unquote(parsed.username),
        "PASSWORD": unquote(parsed.password),
        "HOST": parsed.hostname,
        "PORT": port or 5432,
    }


SECRET_KEY = required_env("DJANGO_SECRET_KEY")
debug_value = os.environ.get("DEBUG", "False").lower()
if debug_value not in ("true", "false"):
    raise ImproperlyConfigured("DEBUG must be True or False")
DEBUG = debug_value == "true"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = ["app.domain.game.apps.GomokuConfig"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": database_config(required_env("DATABASE_URL"))}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
