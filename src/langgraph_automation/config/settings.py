"""Django project settings.

This module is the single configuration entrypoint for the control plane.
"""

from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[3]

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-placeholder"),
    LANGGRAPH_AUTOMATION_REQUIRE_LOGIN=(bool, False),
    LANGGRAPH_AUTOMATION_EXECUTION_MODE=(str, "inline"),
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
    "langgraph_automation.apps.automation.apps.AutomationConfig",
    "langgraph_automation.apps.web.apps.WebConfig",
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

ROOT_URLCONF = "langgraph_automation.config.urls"
WSGI_APPLICATION = "langgraph_automation.config.wsgi.application"
ASGI_APPLICATION = "langgraph_automation.config.asgi.application"

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
LANGGRAPH_AUTOMATION = env("LANGGRAPH_AUTOMATION", default='{"version": 1}')
LANGGRAPH_AUTOMATION_CONFIG_FILE = env("LANGGRAPH_AUTOMATION_CONFIG_FILE", default="")
LANGGRAPH_AUTOMATION_REQUIRE_LOGIN = env("LANGGRAPH_AUTOMATION_REQUIRE_LOGIN")
LANGGRAPH_AUTOMATION_EXECUTION_MODE = env("LANGGRAPH_AUTOMATION_EXECUTION_MODE")
LOGIN_URL = "/admin/login/"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "src" / "langgraph_automation" / "apps" / "web" / "templates"],
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
