# partners/

Clients for the two external services a scan depends on. Treat them like
vendor SDKs: use them, don't change them.

Locally both services are played by one small program, `bin/fakes`, which
`make setup` starts in the background on `127.0.0.1:8899` (`make fakes` starts
it again if it isn't running; `make stop-fakes` stops it). It's a stand-in for
systems we don't control, so it's a binary rather than source. Tests start
their own copy on a free port with small data and no faults (`scans/tests/__init__.py`).

## Bank API (`bank_api.py`)

`GET /bank/v1/{client}/members/{member_id}/transactions?cursor=...&page_size=...`

- Paginated, newest first. Pass `next_cursor` from one page to get the next;
  it's `null` on the last page.
- `page_size` defaults to 100. The maximum is 500; larger values are capped.
- Every page includes the member's `account` block (account number and email).
- Each client's banking platform returns rows in its own format:

| Client | Row format |
|---|---|
| `acme` | `{"id", "description", "amount": "15.49", "type": "debit" or "credit", "posted_date": "2026-09-03"}` |
| `globex` | `{"transactionId", "memo", "amt": 15.49 (negative = money in), "postedAt": "2026-09-03T14:22:00Z"}` |
| `hooli` | `{"txn_id", "merchant_descriptor", "amount_cents": 1549 (negative = money in), "timestamp": 1788445320}` |

- Under load it returns `429` with a `Retry-After` header (seconds).
- It occasionally returns `5xx`.

## Enrichment vendor (`enrichment_vendor.py`)

`POST /vendor/v1/enrich` with `Authorization: Bearer <VENDOR_API_KEY>` and
`{"items": [{"id", "description", "amount"}, ...]}`.

- Returns `{"results": [{"id", "merchant"}, ...]}` in the same order.
  `merchant` is `null` for non-merchant rows (ATM, payroll) or descriptions it
  doesn't recognize. The same description always gets the same answer.
- At most 5,000 items per request; larger requests get `413`.
- Latency grows with batch size, with occasional slow spikes.
- It has outages, during which it returns `503`.
- Too many requests in flight on one API key get `429` with `Retry-After`.

Limits, pricing and data rules are in `context/vendor-contract.md`.
