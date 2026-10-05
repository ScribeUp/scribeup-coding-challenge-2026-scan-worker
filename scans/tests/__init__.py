import os

from partners import harness

# Tests get their own copy of the fake partners: small data, no latency, no faults.
os.environ["JOBQUEUE_DUPLICATE_DELIVERY_RATE"] = "0"
harness.start(profile="test")
