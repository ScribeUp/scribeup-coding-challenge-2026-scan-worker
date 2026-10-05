import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-only-not-a-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "config.urls"
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "jobqueue",
    "scans",
]

_db = urlparse(os.environ.get("DATABASE_URL", "postgres://scan:scan@localhost:5433/scan"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db.path.lstrip("/"),
        "USER": _db.username,
        "PASSWORD": _db.password,
        "HOST": _db.hostname,
        "PORT": _db.port or 5432,
    }
}

# Scan queue. In production this is an SQS queue behind an Elastic Beanstalk
# worker environment (see context/production.md).
SCAN_QUEUE = "scans"
SCAN_VISIBILITY_TIMEOUT_SECONDS = 6  # scaled down for local runs
# Like SQS's redrive policy. Matches production (sqsd MaxRetries = 10).
JOBQUEUE_REDRIVE_POLICY = {"scans": {"max_receive_count": 10, "dead_letter_queue": "scans-dlq"}}

# Partner APIs. Locally these are the fake partners in bin/ (see partners/README.md).
PARTNERS_URL = os.environ.get("PARTNERS_URL", "http://127.0.0.1:8899")
VENDOR_API_KEY = os.environ.get("VENDOR_API_KEY", "sk_test_scanworker_local")

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "scans.logging.JsonFormatter"}},
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "worker.log"),
            "formatter": "json",
        },
    },
    "loggers": {
        "scans": {"handlers": ["file"], "level": "INFO"},
        "jobqueue": {"handlers": ["file"], "level": "INFO"},
    },
}
