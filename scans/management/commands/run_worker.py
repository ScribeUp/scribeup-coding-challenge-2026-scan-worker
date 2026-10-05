from django.core.management.base import BaseCommand

from scans import worker


class Command(BaseCommand):
    help = "Run a single scan worker until interrupted (Ctrl-C)."

    def handle(self, *args, **options):
        try:
            worker.run()
        except KeyboardInterrupt:
            pass
