"""The scan pipeline: fetch -> enrich -> save -> detect -> save subscriptions."""

import logging

from django.utils import timezone

from partners import bank_api, enrichment_vendor

from . import adapters
from .detection import detect_subscriptions
from .models import Member, ScanJob, Subscription, Transaction

log = logging.getLogger("scans.pipeline")


def run_scan(job_id: int) -> None:
    job = ScanJob.objects.select_related("member__client").get(id=job_id)
    job.status = ScanJob.Status.RUNNING
    job.started_at = timezone.now()
    job.attempts += 1
    job.save()

    member = job.member
    log.info("scan started", extra={"job_id": job.id, "member_id": member.id, "attempt": job.attempts})

    # Start from a clean slate so results always reflect the latest data.
    Subscription.objects.filter(member=member).delete()

    rows = fetch_transactions(member)
    merchants = enrich(rows)
    save_transactions(member.id, rows, merchants)

    detected = detect_subscriptions(Transaction.objects.filter(member=member, merchant_name__isnull=False))
    for sub in detected:
        Subscription.objects.create(
            member=member,
            merchant=sub.merchant,
            cadence=sub.cadence,
            typical_amount=sub.typical_amount,
            last_charged_at=sub.last_charged_at,
            next_predicted_at=sub.next_predicted_at,
            confidence=sub.confidence,
            is_active=sub.is_active,
            occurrences=sub.occurrences,
        )

    job.status = ScanJob.Status.SUCCEEDED
    job.finished_at = timezone.now()
    job.save()
    log.info(
        "scan finished",
        extra={"job_id": job.id, "member_id": member.id, "transactions": len(rows), "subscriptions": len(detected)},
    )


def fetch_transactions(member: Member) -> list[dict]:
    adapter = adapters.get(member.client.adapter)
    rows = []
    cursor = None
    while True:
        page = bank_api.list_transactions(member.client.slug, member.external_id, cursor=cursor)
        log.info("fetched bank page", extra={"member_id": member.id, "cursor": cursor, "page": page})
        rows.extend(adapter(row) for row in page["data"])
        cursor = page["next_cursor"]
        if not cursor:
            return rows


def enrich(rows: list[dict]) -> dict[str, str | None]:
    """Ask the enrichment vendor which merchant each transaction belongs to."""
    items = [{"id": r["external_id"], "description": r["description"], "amount": str(r["amount"])} for r in rows]
    try:
        results = enrichment_vendor.enrich(items)
    except enrichment_vendor.VendorError as e:
        if e.status >= 500:
            # The vendor is flaky. Don't fail the whole scan over it.
            log.warning("enrichment vendor unavailable, continuing without merchants", extra={"status": e.status})
            return {}
        raise
    return {r["id"]: r["merchant"] for r in results}


def save_transactions(member_id: int, rows: list[dict], merchants: dict) -> None:
    for row in rows:
        member = Member.objects.get(id=member_id)
        if Transaction.objects.filter(member=member, external_id=row["external_id"]).exists():
            continue
        Transaction.objects.create(
            member=member,
            external_id=row["external_id"],
            description=row["description"],
            amount=row["amount"],
            posted_at=row["posted_at"],
            merchant_name=merchants.get(row["external_id"]),
        )
