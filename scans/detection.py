"""Subscription detection. OUT OF SCOPE for this exercise: please don't change it.

Takes a list of transactions for a single user and returns the recurring
subscriptions inferred from them. Pure function, no DB access, which keeps the
algorithm easy to test and easy to swap for a faster implementation later.

Approach:
  1. Normalize merchant names so variants (Netflix vs NETFLIX.COM) collapse.
  2. Group transactions by normalized merchant.
  3. For each group, look at the gaps between consecutive charges.
     If those gaps cluster tightly around 7 / 30 / 365 days, it's recurring.
  4. Use the median amount as the "typical" amount (robust to price changes
     and free-trial $0 first charges).
  5. Predict the next charge by adding the median interval to the most
     recent charge.
  6. Flag as inactive if the most recent charge is more than 1.5 cadences ago
     (probably cancelled).

Known limitations (not part of this exercise):
  - Doesn't handle quarterly / semi-annual cadences.
  - Merchant normalization is naive regex.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median, stdev


MIN_OCCURRENCES = 3                 # need at least 3 charges to call it recurring
MAX_INTERVAL_CV = 0.35              # coefficient of variation cutoff for "regular"
INACTIVE_AFTER_CADENCES = 1.5       # how many cadences past last charge = cancelled

# (label, target_days, tolerance_days)
CADENCE_BUCKETS = [
    ("weekly", 7, 2),
    ("monthly", 30, 5),
    ("yearly", 365, 20),
]

_SUFFIX_RE = re.compile(r"\b(inc|llc|com|co|corp|ltd)\b\.?")
_PUNCT_RE = re.compile(r"[.,\-_]")


@dataclass(frozen=True)
class DetectedSubscription:
    merchant: str
    cadence: str                       # "weekly" | "monthly" | "yearly"
    typical_amount: Decimal
    last_charged_at: datetime
    next_predicted_at: datetime
    confidence: float                  # 0..1, higher = more regular intervals
    is_active: bool
    occurrences: int

    def to_dict(self) -> dict:
        return {
            "merchant": self.merchant,
            "cadence": self.cadence,
            "typical_amount": str(self.typical_amount),
            "last_charged_at": self.last_charged_at.isoformat(),
            "next_predicted_at": self.next_predicted_at.isoformat(),
            "confidence": round(self.confidence, 2),
            "is_active": self.is_active,
            "occurrences": self.occurrences,
        }


def _normalize(merchant: str) -> str:
    n = merchant.lower()
    n = _PUNCT_RE.sub(" ", n)
    n = _SUFFIX_RE.sub("", n)
    return " ".join(n.split())


def _classify_cadence(intervals_days: list[float]) -> tuple[str, float] | None:
    """Return (label, median_days) if the intervals cluster around a known cadence."""
    if len(intervals_days) < MIN_OCCURRENCES - 1:
        return None
    med = median(intervals_days)
    # Reject if intervals are too jittery to be a real subscription.
    if len(intervals_days) >= 2 and med > 0:
        cv = stdev(intervals_days) / med
        if cv > MAX_INTERVAL_CV:
            return None
    for label, target, tolerance in CADENCE_BUCKETS:
        if abs(med - target) <= tolerance:
            return label, med
    return None


def detect_subscriptions(transactions, now: datetime | None = None) -> list[DetectedSubscription]:
    """Return the list of detected recurring subscriptions for a user.

    `transactions` is any iterable of objects with `merchant_name`, `amount`,
    and `posted_at` attributes. Transactions without a merchant are ignored.
    """
    now = now or datetime.now(timezone.utc)

    groups: dict[str, list] = defaultdict(list)
    for t in transactions:
        if not t.merchant_name or t.amount <= 0:
            # Skip unidentified transactions, and $0 charges (free trials etc.)
            # which mess with the median amount and aren't a real charge.
            continue
        groups[_normalize(t.merchant_name)].append(t)

    detected: list[DetectedSubscription] = []

    for txns in groups.values():
        if len(txns) < MIN_OCCURRENCES:
            continue
        txns.sort(key=lambda t: t.posted_at)
        # Banks occasionally report the same charge twice; count it once.
        seen, unique = set(), []
        for t in txns:
            key = (t.posted_at.date(), t.amount)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        txns = unique
        if len(txns) < MIN_OCCURRENCES:
            continue

        intervals = [
            (txns[i].posted_at - txns[i - 1].posted_at).total_seconds() / 86400
            for i in range(1, len(txns))
        ]
        classified = _classify_cadence(intervals)
        if classified is None:
            continue
        cadence_label, median_interval = classified

        # Use the most-frequent merchant string as the canonical display name.
        canonical = Counter(t.merchant_name for t in txns).most_common(1)[0][0]

        typical_amount = median(t.amount for t in txns)
        last = txns[-1]
        next_predicted = last.posted_at + timedelta(days=median_interval)

        days_since_last = (now - last.posted_at).total_seconds() / 86400
        is_active = days_since_last <= median_interval * INACTIVE_AFTER_CADENCES

        cv = stdev(intervals) / median_interval if median_interval and len(intervals) > 1 else 0
        confidence = max(0.0, 1.0 - cv)

        detected.append(DetectedSubscription(
            merchant=canonical,
            cadence=cadence_label,
            typical_amount=typical_amount,
            last_charged_at=last.posted_at,
            next_predicted_at=next_predicted,
            confidence=confidence,
            is_active=is_active,
            occurrences=len(txns),
        ))

    detected.sort(key=lambda s: (not s.is_active, -s.occurrences))
    return detected
