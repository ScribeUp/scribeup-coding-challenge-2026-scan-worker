from django.db import models


class Client(models.Model):
    """A bank, credit union or fintech that embeds ScribeUp."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    adapter = models.CharField(max_length=50, help_text="Which bank API format this client uses")

    def __str__(self) -> str:
        return self.name


class Member(models.Model):
    """An end user at one of our clients."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="members")
    external_id = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["client", "external_id"], name="uniq_member_per_client"),
        ]

    def __str__(self) -> str:
        return f"{self.client.slug}/{self.external_id}"


class ScanJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED"
        RUNNING = "RUNNING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="scan_jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)


class Transaction(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="transactions")
    external_id = models.CharField(max_length=100, help_text="The bank's transaction id")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Positive = money out")
    posted_at = models.DateTimeField()
    merchant_name = models.CharField(max_length=200, null=True, blank=True, help_text="From the enrichment vendor")
    created_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="subscriptions")
    merchant = models.CharField(max_length=200)
    cadence = models.CharField(max_length=20)
    typical_amount = models.DecimalField(max_digits=12, decimal_places=2)
    last_charged_at = models.DateTimeField()
    next_predicted_at = models.DateTimeField()
    confidence = models.FloatField()
    is_active = models.BooleanField()
    occurrences = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
