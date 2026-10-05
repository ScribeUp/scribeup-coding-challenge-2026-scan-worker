from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from scans.detection import detect_subscriptions

START = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def txn(merchant, amount, day):
    return SimpleNamespace(merchant_name=merchant, amount=Decimal(amount), posted_at=START + timedelta(days=day))


class DetectionTests(SimpleTestCase):
    def test_monthly_charges_are_a_subscription(self):
        txns = [txn("Netflix", "15.49", 30 * i) for i in range(6)]
        subs = detect_subscriptions(txns, now=START + timedelta(days=160))
        self.assertEqual([(s.merchant, s.cadence, s.typical_amount) for s in subs], [("Netflix", "monthly", Decimal("15.49"))])

    def test_irregular_purchases_are_not_a_subscription(self):
        txns = [txn("Chipotle", "12.40", day) for day in [0, 3, 17, 18, 40, 41, 77]]
        self.assertEqual(detect_subscriptions(txns), [])

    def test_transactions_without_a_merchant_are_ignored(self):
        txns = [txn(None, "9.99", 30 * i) for i in range(6)]
        self.assertEqual(detect_subscriptions(txns), [])
