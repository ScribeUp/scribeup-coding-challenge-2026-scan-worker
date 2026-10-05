from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand

from partners import harness
from scans.detection import detect_subscriptions
from scans.models import Client, Member, Subscription, Transaction


class Command(BaseCommand):
    help = "Create the clients and members the bank knows about, plus Hooli's existing production data."

    def handle(self, *args, **options):
        roster = harness.members()
        clients = {}
        for c in roster["clients"]:
            clients[c["slug"]], _ = Client.objects.update_or_create(
                slug=c["slug"], defaults={"name": c["name"], "adapter": c["slug"]}
            )
        for m in roster["members"]:
            Member.objects.update_or_create(
                client=clients[m["client"]], external_id=m["external_id"], defaults={"email": m["email"]}
            )
        existing = self._existing_hooli_data(clients["hooli"])
        self.stdout.write(
            f"Seeded {Member.objects.count()} members across {len(clients)} clients "
            f"({existing} Hooli members already have data from earlier scans)."
        )

    def _existing_hooli_data(self, hooli: Client) -> int:
        """Hooli went live a few months ago, so its members were already scanned by the current code."""
        history = {m["external_id"]: m["transactions"] for m in harness.hooli_history()}
        seeded = 0
        for member in hooli.members.all():
            if member.transactions.exists() or not history.get(member.external_id):
                continue
            rows = [
                Transaction(
                    member=member,
                    external_id=t["id"],
                    description=t["description"],
                    amount=Decimal(t["stored_amount"]),
                    posted_at=datetime.fromisoformat(t["posted_at"]),
                    merchant_name=t["merchant"],
                )
                for t in history[member.external_id]
            ]
            Transaction.objects.bulk_create(rows)
            Subscription.objects.bulk_create(
                Subscription(
                    member=member,
                    merchant=s.merchant,
                    cadence=s.cadence,
                    typical_amount=s.typical_amount,
                    last_charged_at=s.last_charged_at,
                    next_predicted_at=s.next_predicted_at,
                    confidence=s.confidence,
                    is_active=s.is_active,
                    occurrences=s.occurrences,
                )
                for s in detect_subscriptions(rows)
            )
            seeded += 1
        return seeded
