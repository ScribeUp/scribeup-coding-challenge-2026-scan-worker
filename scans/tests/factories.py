import io

from django.core.management import call_command

from scans.models import Member


def seed() -> None:
    call_command("seed", stdout=io.StringIO())


def member(client: str = "acme", index: int = 0) -> Member:
    return Member.objects.select_related("client").get(client__slug=client, external_id=f"{client[:3]}-{1000 + index}")
