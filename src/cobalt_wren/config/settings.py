"""Django project settings.

This module is the single configuration entrypoint for the control plane.
"""

from __future__ import annotations

import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[3]

_LEGACY_ENV_ALIASES = {
    "COBALT_WREN": "LANGGRAPH_AUTOMATION",
    "COBALT_WREN_CONFIG_FILE": "LANGGRAPH_AUTOMATION_CONFIG_FILE",
    "COBALT_WREN_REQUIRE_LOGIN": "LANGGRAPH_AUTOMATION_REQUIRE_LOGIN",
    "COBALT_WREN_EXECUTION_MODE": "LANGGRAPH_AUTOMATION_EXECUTION_MODE",
    "COBALT_WREN_DIAGNOSTIC_RETENTION_DAYS": "LANGGRAPH_AUTOMATION_DIAGNOSTIC_RETENTION_DAYS",
}
for current_name, legacy_name in _LEGACY_ENV_ALIASES.items():
    if current_name not in os.environ and legacy_name in os.environ:
        os.environ[current_name] = os.environ[legacy_name]

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-placeholder"),
    COBALT_WREN_REQUIRE_LOGIN=(bool, False),
    COBALT_WREN_EXECUTION_MODE=(str, "inline"),
    COBALT_WREN_DIAGNOSTIC_RETENTION_DAYS=(int, 7),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
LLM_API_KEY = env("LLM_API_KEY", default="")
LLM_BASE_URL = env("LLM_BASE_URL", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cobalt_wren.apps.automation.apps.AutomationConfig",
    "cobalt_wren.apps.web.apps.WebConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cobalt_wren.config.urls"
WSGI_APPLICATION = "cobalt_wren.config.wsgi.application"
ASGI_APPLICATION = "cobalt_wren.config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# Reserved for a future filesystem-backed artifact backend.
ARTIFACT_ROOT = env("ARTIFACT_ROOT", default=str(BASE_DIR / "artifacts"))
# Deployment-owned package config for startup composition.
COBALT_WREN = env("COBALT_WREN", default='{"version": 1}')
COBALT_WREN_CONFIG_FILE = env("COBALT_WREN_CONFIG_FILE", default="")
COBALT_WREN_REQUIRE_LOGIN = env("COBALT_WREN_REQUIRE_LOGIN")
COBALT_WREN_EXECUTION_MODE = env("COBALT_WREN_EXECUTION_MODE")
COBALT_WREN_DIAGNOSTIC_RETENTION_DAYS = env("COBALT_WREN_DIAGNOSTIC_RETENTION_DAYS")
LOGIN_URL = "/admin/login/"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "src" / "cobalt_wren" / "apps" / "web" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
