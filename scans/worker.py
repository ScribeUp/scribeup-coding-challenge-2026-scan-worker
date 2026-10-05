"""Scan worker loop: receive a message, run the scan, delete the message."""

import logging
import threading
import time

from django.conf import settings
from django.db import connections

from jobqueue import client as jobqueue

from .pipeline import run_scan

log = logging.getLogger("scans.worker")


def run(stop: threading.Event | None = None) -> None:
    try:
        while not (stop and stop.is_set()):
            message = jobqueue.receive(settings.SCAN_QUEUE, visibility_timeout=settings.SCAN_VISIBILITY_TIMEOUT_SECONDS)
            if message is None:
                time.sleep(0.2)
                continue
            job_id = message.body["job_id"]
            try:
                run_scan(job_id)
            except Exception:
                # Leave the message on the queue. It becomes visible again after
                # the visibility timeout and gets retried.
                log.exception("scan failed", extra={"job_id": job_id})
                continue
            jobqueue.delete(message)
    finally:
        connections.close_all()
