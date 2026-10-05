# Production setup

Notes from the platform runbook. Locally, `jobqueue/` and `make scan-all` stand in for this, with the timeouts scaled down.

## Scan workers

- Scans run in an Elastic Beanstalk **worker environment** with 2 instances (autoscaling to 6). On each instance, the `sqsd` daemon reads the `scans` SQS queue and POSTs each message to the app over HTTP, up to 4 at a time (`HttpConnections: 4`). So 8 scans run at once on a normal day, and up to 24 when we scale out.
- The app doesn't talk to SQS for this queue. It answers sqsd's POST:
  - `200`: sqsd deletes the message.
  - Anything else, or no answer within `InactivityTimeout` (299s): the message stays on the queue and becomes visible again after `ErrorVisibilityTimeout` (60s).
- sqsd holds the receipt handle, so the app can't delete a message early or call `ChangeMessageVisibility`. It can read the receive count from the `X-Aws-Sqsd-Receive-Count` header.
- `VisibilityTimeout`: 300s. `MaxRetries`: 10, then the message moves to `scans-dlq`.
- The app can send new messages to any queue (`SendMessage`, with `DelaySeconds` up to 900).

## Scan volume

- Members are scanned when they activate and again every night, to pick up new transactions. About 180,000 members get the nightly rescan.
- Activations come in bursts when a client launches to a new group of members.

## Database

- RDS Postgres 16. `scans_transaction` holds about 38M rows, `scans_subscription` 1.1M, `scans_member` 420k.
- Migrations run during deploy, before the new code starts. Anything that locks `scans_transaction` for more than a few seconds stalls every running scan.

## Logs

- Worker logs ship to our log provider and are kept for 15 months. Support, Client Success and two contractors have read access.
- Logs are currently under a legal hold (see `slack-eng-scan.md`).
