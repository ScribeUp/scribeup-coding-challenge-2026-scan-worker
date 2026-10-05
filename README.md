# Scan Worker Exercise

Thanks for spending time on this. It should take **2–3 hours**. Please don't go over 3.

## The scenario

When a bank member turns on ScribeUp inside their banking app, we run a **scan**: a background job that pulls their transaction history from the bank, asks an enrichment vendor which merchant each transaction belongs to, detects recurring subscriptions, and saves them.

The scan worker has a backlog of production tickets (see `TICKETS.md`). You won't get through all of them in the time, and we don't expect you to. We want to see what you pick, how you find the real problem, how you fix it safely, and how you explain it.

## Setup (about 10 minutes)

You need Python 3.12+, Docker, and macOS or Linux. On Windows, use WSL2 and clone the repo from inside WSL (into your Linux home directory, not `/mnt/c`), so the scripts keep their Unix line endings and permissions.

```
docker compose up -d     # Postgres on localhost:5433
python -m venv .venv && source .venv/bin/activate
make setup               # install deps, start the fake partners, migrate, seed 3 clients and ~30 members
make scan-all            # scan every member with 3 workers, then print a summary
make test
```

`make reset` wipes the database and logs and re-seeds. `make scan-all` stops after 90 seconds if the queue hasn't drained. Worker logs go to `logs/worker.log` (one JSON object per line).

The bank and the enrichment vendor are played locally by `bin/fakes`, a small HTTP service that `make` starts in the background (see `partners/README.md`). If macOS refuses to run it after downloading a zip, run `xattr -d com.apple.quarantine bin/fakes-*`.

## How the code fits together

```
member activates -> ScanJob queued -> worker receives the message
   -> fetch transactions   (partners/bank_api.py)
   -> enrich merchants     (partners/enrichment_vendor.py)
   -> save transactions
   -> detect subscriptions (scans/detection.py)
   -> save subscriptions
```

| Path | What it is | Can you change it? |
|---|---|---|
| `scans/` | Our code: models, pipeline, worker, adapters, commands, tests | Yes |
| `config/settings.py` | Settings, including queue configuration | Yes |
| `jobqueue/` | A queue that behaves like SQS (read its docstring) | No, it stands in for SQS |
| `partners/` | Clients for the bank and enrichment vendor APIs, and how those APIs behave | No, treat them like vendor SDKs |
| `bin/` | The fake bank and vendor you run locally | No, they're external services |
| `context/` | How production is set up, our vendor contract, and a recent Slack thread | Read it |
| `scans/detection.py` | Subscription detection | No, out of scope |

## What to hand in

1. **Your code changes,** committed as you go so we can see how you worked.
2. **`NOTES.md`** covering:
    - The tickets you picked, in order, and why.
    - For each ticket you worked on: the root cause, your fix, and how you verified it.
    - What you'd do next with the rest, and in what order.
    - Anything in your changes you'd want a second reviewer on.
    - Where AI helped, and anywhere it was wrong.
    - Roughly how long you spent.
3. **`CLIENT_UPDATE.md`:** a short note (one or two paragraphs) to Acme Credit Union's IT lead about SCAN-101. They're technical, but they don't know our system.

## Ground rules

- **Use AI tools** the way you normally would. Be ready to walk us through any line you submit.
- Database migrations are fine. Assume the tables already hold production data.

## How we'll review it

- We'll run your branch with `make scan-all` against **a different data set and failure profile** than the one in this repo. Fix the failure modes in general, not just the cases you can see.
- Then we'll have a follow up conversation. You'll walk us through your choices, we'll ask about running this in production.

## Submitting

Clone this repo and push your work to a new private repo of your own, then share it with us (or send a zip, including `.git`). Please don't use GitHub's Fork button: forks of a public repo are public, so other candidates could find your solution.
