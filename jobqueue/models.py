from django.db import models


class Message(models.Model):
    queue = models.CharField(max_length=100, db_index=True)
    body = models.JSONField()
    visible_at = models.DateTimeField(db_index=True)
    receive_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.queue}#{self.id} {self.body}"


class Request(models.Model):
    """One API call to the queue (SQS bills per request)."""

    action = models.CharField(max_length=30)
    queue = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
