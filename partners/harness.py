"""Local-only helpers for the fake partners: seeding the database, and starting
a private copy for tests. Nothing here exists in production.
"""

from __future__ import annotations

import atexit
import os
import socket
import subprocess
import time
from pathlib import Path

import requests
from django.conf import settings

from . import _http

FAKES = Path(__file__).resolve().parent.parent / "bin" / "fakes"


def health() -> dict | None:
    """The fake partners' status, or None if they aren't running."""
    try:
        resp = requests.get(_http.url("/healthz"), timeout=2)
        return resp.json() if resp.status_code == 200 else None
    except requests.RequestException:
        return None


def members() -> dict:
    """The clients and members the fake bank knows about (what our onboarding would have created)."""
    resp = requests.get(_http.url("/_harness/members"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def hooli_history() -> list[dict]:
    """Hooli's existing rows, as the current code stored them when Hooli went live."""
    resp = requests.get(_http.url("/_harness/hooli-history"), timeout=60)
    resp.raise_for_status()
    return resp.json()["members"]


def start(profile: str = "test") -> str:
    """Start a private copy of the fake partners on a free port and point PARTNERS_URL at it."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [str(FAKES)],
        env={**os.environ, "FAKES_PORT": str(port), "FAKES_PROFILE": profile},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(proc.terminate)
    settings.PARTNERS_URL = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 10
    while health() is None:
        if proc.poll() is not None or time.monotonic() > deadline:
            raise RuntimeError(f"Fake partners didn't start (tried {FAKES})")
        time.sleep(0.05)
    return settings.PARTNERS_URL
