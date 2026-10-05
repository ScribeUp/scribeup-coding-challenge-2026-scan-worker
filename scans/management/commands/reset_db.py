from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from jobqueue.models import Message, Request
from scans.models import Client, Member, ScanJob, Subscription, Transaction


class Command(BaseCommand):
    help = "Delete all data, clear the logs, and re-seed."

    def handle(self, *args, **options):
        tables = [m._meta.db_table for m in (Subscription, Transaction, ScanJob, Member, Client, Message, Request)]
        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
        (settings.LOG_DIR / "worker.log").write_text("")
        call_command("seed", stdout=self.stdout)
