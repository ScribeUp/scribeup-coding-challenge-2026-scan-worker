from django.test import TestCase

from partners import bank_api
from scans.models import ScanJob
from scans.pipeline import run_scan

from . import factories


def bank_transaction_count(member) -> int:
    count, cursor = 0, None
    while True:
        page = bank_api.list_transactions(member.client.slug, member.external_id, cursor=cursor, page_size=500)
        count += len(page["data"])
        cursor = page["next_cursor"]
        if not cursor:
            return count


class RunScanTests(TestCase):
    def setUp(self):
        factories.seed()

    def test_scan_saves_transactions_and_subscriptions(self):
        member = factories.member("acme")
        job = ScanJob.objects.create(member=member)

        run_scan(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, ScanJob.Status.SUCCEEDED)
        self.assertEqual(member.transactions.count(), bank_transaction_count(member))
        self.assertGreater(member.subscriptions.count(), 0)
