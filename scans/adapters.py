"""Map each client's bank API rows to our transaction shape:

    {"external_id": str, "description": str, "amount": Decimal, "posted_at": datetime}

`amount` is in dollars, positive for money out.
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal


def acme(row: dict) -> dict:
    amount = Decimal(row["amount"])
    if row["type"] == "credit":
        amount = -amount
    return {
        "external_id": row["id"],
        "description": row["description"],
        "amount": amount,
        "posted_at": datetime.combine(date.fromisoformat(row["posted_date"]), time.min, tzinfo=timezone.utc),
    }


def globex(row: dict) -> dict:
    return {
        "external_id": row["transactionId"],
        "description": row["memo"],
        "amount": Decimal(str(row["amt"])),
        "posted_at": datetime.fromisoformat(row["postedAt"].replace("Z", "+00:00")),
    }


def hooli(row: dict) -> dict:
    return {
        "external_id": row["txn_id"],
        "description": row["merchant_descriptor"],
        "amount": Decimal(row["amount_cents"]),
        "posted_at": datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
    }


ADAPTERS = {"acme": acme, "globex": globex, "hooli": hooli}


def get(name: str):
    return ADAPTERS[name]
