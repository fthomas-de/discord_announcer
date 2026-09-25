# flake8: noqa

# Every setting in base.py can be overloaded by redefining it here.
from .base import *

# These are required for Django to function properly. Don't touch.
ROOT_URLCONF = "testauth.urls"
WSGI_APPLICATION = "testauth.wsgi.application"
SECRET_KEY = "t$@h+j#yqhmuy$x7$fkhytd&drajgfsb-6+j9pqn*vj0)gq&-2"

STATIC_ROOT = "/var/www/testauth/static/"
SITE_NAME = "testauth"
SITE_URL = "http://127.0.0.1:8000"
DEBUG = False

# corptools and eve_sde: the app reads corptools' wallet divisions, stations
# and item types, and corptools' token helper chooses the token. The example
# plugin named a package "example" here, so nothing ever ran.
INSTALLED_APPS += [
    "modeltranslation",
    "allianceauth.theme.bootstrap",
    "corptools",
    "eve_sde",
    "discord_announcer",
]

# sqlite of its own, never a real Alliance Auth database - the dev instance's
# aa_dev holds corptools data that cannot be fetched again. The test runner
# puts the test database in memory.
DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.path.join(BASE_DIR, "discord_announcer_testauth.sqlite3"),
}

ESI_SSO_CLIENT_ID = "dummy"
ESI_SSO_CLIENT_SECRET = "dummy"
ESI_SSO_CALLBACK_URL = "http://localhost:8000"
# Required since AA 5.x: CCP demands a maintainer contact for ESI requests.
# Placeholder only - this file is public. Override locally if you hit ESI live.
ESI_USER_CONTACT_EMAIL = "test@example.com"

REGISTRATION_VERIFY_EMAIL = False
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = ""

# workarounds to suppress warnings
LOGGING = None
STATICFILES_DIRS = []

CSRF_TRUSTED_ORIGINS = [SITE_URL]

# AA ships a hashing manifest storage, but this test project never runs
# collectstatic - every {% static %} would raise "Missing staticfiles manifest
# entry". DEBUG is no escape hatch here: the test runner forces DEBUG=False.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
