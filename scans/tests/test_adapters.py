from datetime import datetime, timezone
from decimal import Decimal

from django.test import SimpleTestCase

from scans import adapters


class AdapterTests(SimpleTestCase):
    def test_acme_debit(self):
        row = {"id": "tx_1", "description": "NETFLIX.COM", "amount": "15.49", "type": "debit", "posted_date": "2026-09-03"}
        self.assertEqual(adapters.acme(row), {
            "external_id": "tx_1",
            "description": "NETFLIX.COM",
            "amount": Decimal("15.49"),
            "posted_at": datetime(2026, 9, 3, tzinfo=timezone.utc),
        })

    def test_acme_credit_is_negative(self):
        row = {"id": "tx_2", "description": "PAYROLL", "amount": "2400.00", "type": "credit", "posted_date": "2026-09-05"}
        self.assertEqual(adapters.acme(row)["amount"], Decimal("-2400.00"))

    def test_globex(self):
        row = {"transactionId": "tx_3", "memo": "SPOTIFY USA", "amt": 11.99, "postedAt": "2026-09-03T14:22:00Z"}
        self.assertEqual(adapters.globex(row), {
            "external_id": "tx_3",
            "description": "SPOTIFY USA",
            "amount": Decimal("11.99"),
            "posted_at": datetime(2026, 9, 3, 14, 22, tzinfo=timezone.utc),
        })
