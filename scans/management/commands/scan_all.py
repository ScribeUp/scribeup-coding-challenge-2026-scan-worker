import statistics
import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db.models.functions import Lower

from jobqueue import client as jobqueue
from partners import harness
from scans import worker
from scans.models import Member, ScanJob, Subscription


class Command(BaseCommand):
    help = "Queue a scan for every member, run workers until the queue is empty, then print a summary."

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=3)
        parser.add_argument("--max-seconds", type=int, default=90)

    def handle(self, *args, workers, max_seconds, **options):
        fakes = harness.health()
        if fakes is None:
            raise CommandError(f"Can't reach the fake partners at {settings.PARTNERS_URL}. Start them with `make fakes`.")
        started = time.monotonic()
        job_ids = [ScanJob.objects.create(member=m).id for m in Member.objects.order_by("id")]
        for job_id in job_ids:
            jobqueue.send({"job_id": job_id}, queue=settings.SCAN_QUEUE)
        self.stdout.write(f"Queued {len(job_ids)} scans ({fakes['profile']} profile), running {workers} workers...")

        stop = threading.Event()
        threads = [
            threading.Thread(target=worker.run, kwargs={"stop": stop}, name=f"worker-{i + 1}", daemon=True)
            for i in range(workers)
        ]
        for t in threads:
            t.start()

        next_report = 5
        while True:
            time.sleep(0.5)
            elapsed = time.monotonic() - started
            queue = jobqueue.stats(settings.SCAN_QUEUE)
            if queue["visible"] + queue["in_flight"] == 0:
                break
            if elapsed >= max_seconds:
                self.stdout.write(self.style.WARNING(f"Stopping after {max_seconds}s with messages still on the queue."))
                break
            if elapsed >= next_report:
                finished = ScanJob.objects.filter(id__in=job_ids, finished_at__isnull=False).count()
                self.stdout.write(f"  {elapsed:4.0f}s  {finished}/{len(job_ids)} scans finished")
                next_report += 5

        stop.set()
        deadline = time.monotonic() + 10
        for t in threads:
            t.join(timeout=max(0, deadline - time.monotonic()))
        self._summary(job_ids, time.monotonic() - started)

    def _summary(self, job_ids, elapsed):
        jobs = ScanJob.objects.filter(id__in=job_ids)
        by_status = ", ".join(
            f"{row['n']} {row['status']}" for row in jobs.values("status").annotate(n=Count("id")).order_by("status")
        )
        durations = sorted(
            (j.finished_at - j.started_at).total_seconds()
            for j in jobs.exclude(started_at=None).exclude(finished_at=None)
        )
        dupes = (
            Subscription.objects.annotate(m=Lower("merchant"))
            .values("member_id", "m")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
        )
        empty = Member.objects.annotate(n=Count("subscriptions")).filter(n=0).count()
        queue = jobqueue.stats(settings.SCAN_QUEUE)
        dlq = settings.JOBQUEUE_REDRIVE_POLICY.get(settings.SCAN_QUEUE, {}).get("dead_letter_queue")
        requests = jobqueue.request_counts()

        self.stdout.write("")
        self.stdout.write(f"Finished in {elapsed:.1f}s")
        self.stdout.write(f"  Scans:      {by_status}")
        if durations:
            p95 = statistics.quantiles(durations, n=20)[-1] if len(durations) > 1 else durations[0]
            self.stdout.write(
                f"  Duration:   p50 {statistics.median(durations):.1f}s  p95 {p95:.1f}s  max {durations[-1]:.1f}s"
            )
        self.stdout.write(f"  Members with no subscriptions: {empty} of {Member.objects.count()}")
        self.stdout.write(
            f"  Duplicate subscriptions: {sum(d['n'] - 1 for d in dupes)} extra rows across "
            f"{len({d['member_id'] for d in dupes})} members"
        )
        self.stdout.write(f"  Queue:      {queue['visible']} visible, {queue['in_flight']} in flight")
        if dlq:
            dead = jobqueue.stats(dlq)
            self.stdout.write(f"  Dead-letter queue ({dlq}): {dead['visible'] + dead['in_flight']} messages")
        self.stdout.write(
            f"  Queue API calls: {sum(requests.values())} ("
            + ", ".join(f"{action} {n}" for action, n in requests.items())
            + ")"
        )
        self.stdout.write(f"  Logs:       {settings.LOG_DIR / 'worker.log'}")
