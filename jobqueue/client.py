"""A small queue that behaves like Amazon SQS.

In production the scan queue is SQS feeding an Elastic Beanstalk worker
environment (see context/production.md), so treat this module as
infrastructure you can configure but not change:

- **At-least-once delivery.** Occasionally a message you've received is also
  delivered to another worker while you're still processing it.
- **No ordering guarantee.** Like an SQS standard queue, visible messages come
  back in no particular order.
- **Visibility timeout.** `receive()` hides a message for `visibility_timeout`
  seconds. If it isn't deleted by then, it becomes visible again and another
  worker will receive it.
- **`change_visibility()`** extends (or shortens) the time before a received
  message becomes visible again.
- **Redrive policy.** `settings.JOBQUEUE_REDRIVE_POLICY` moves a message to a
  dead-letter queue after it has been received too many times, like SQS's
  `maxReceiveCount`.
- **Billed per request.** Every call is recorded in `jobqueue_request`, the
  way SQS counts (and bills) API requests.
"""

from __future__ import annotations

import collections
import os
import random
import threading
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone

from .models import Message, Request


# Messages that will be delivered a second time (at-least-once delivery).
_duplicates: collections.deque = collections.deque()
_duplicates_lock = threading.Lock()


def _duplicate_rate() -> float:
    return float(os.environ.get("JOBQUEUE_DUPLICATE_DELIVERY_RATE", "0.2"))


def _record(action: str, queue: str) -> None:
    Request.objects.create(action=action, queue=queue)


def send(body: dict, queue: str, delay_seconds: float = 0) -> Message:
    _record("send", queue)
    return Message.objects.create(queue=queue, body=body, visible_at=timezone.now() + timedelta(seconds=delay_seconds))


def _take_duplicate(queue: str) -> Message | None:
    with _duplicates_lock:
        match = next((item for item in _duplicates if item[0] == queue), None)
        if match is None:
            return None
        _duplicates.remove(match)
    if Message.objects.filter(id=match[1]).update(receive_count=F("receive_count") + 1):
        return Message.objects.get(id=match[1])
    return None


def receive(queue: str, visibility_timeout: float) -> Message | None:
    """Receive the next visible message, or None if there isn't one."""
    _record("receive", queue)
    duplicate = _take_duplicate(queue)
    if duplicate is not None:
        return duplicate
    policy = getattr(settings, "JOBQUEUE_REDRIVE_POLICY", {}).get(queue)
    while True:
        with transaction.atomic():
            now = timezone.now()
            message = (
                Message.objects.select_for_update(skip_locked=True)
                .filter(queue=queue, visible_at__lte=now)
                .order_by("?")
                .first()
            )
            if message is None:
                return None
            if policy and message.receive_count >= policy["max_receive_count"]:
                message.queue = policy["dead_letter_queue"]
                message.save(update_fields=["queue"])
                continue
            message.receive_count += 1
            message.visible_at = now + timedelta(seconds=visibility_timeout)
            message.save(update_fields=["receive_count", "visible_at"])
        if random.random() < _duplicate_rate():
            with _duplicates_lock:
                _duplicates.append((queue, message.id))
        return message


def delete(message: Message) -> None:
    _record("delete", message.queue)
    Message.objects.filter(id=message.id).delete()


def change_visibility(message: Message, timeout_seconds: float) -> None:
    _record("change_visibility", message.queue)
    Message.objects.filter(id=message.id).update(visible_at=timezone.now() + timedelta(seconds=timeout_seconds))


def stats(queue: str) -> dict:
    now = timezone.now()
    messages = Message.objects.filter(queue=queue)
    return {
        "visible": messages.filter(visible_at__lte=now).count(),
        "in_flight": messages.filter(visible_at__gt=now).count(),
    }


def request_counts() -> dict[str, int]:
    """API calls made so far, by action."""
    return dict(Request.objects.values_list("action").annotate(n=Count("id")).order_by("action"))
