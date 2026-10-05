"""Shared HTTP plumbing for the partner clients."""

from __future__ import annotations

import threading

import requests
from django.conf import settings

_local = threading.local()


def session() -> requests.Session:
    """One keep-alive session per thread (requests sessions aren't thread-safe)."""
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def url(path: str) -> str:
    return settings.PARTNERS_URL.rstrip("/") + path


def error_message(resp: requests.Response) -> str:
    try:
        return resp.json().get("error", "")
    except ValueError:
        return resp.text[:200]


def retry_after(resp: requests.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None
