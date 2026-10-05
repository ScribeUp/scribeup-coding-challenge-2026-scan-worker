"""Client for the enrichment vendor, which tells us which merchant a raw bank
transaction belongs to.

    POST /vendor/v1/enrich

Treat this like a vendor SDK: use it, don't change it. See partners/README.md
for how the API behaves and context/vendor-contract.md for what we agreed to.
"""

from __future__ import annotations

import requests
from django.conf import settings

from . import _http


class VendorError(Exception):
    def __init__(self, status: int, message: str = "", retry_after: float | None = None):
        super().__init__(f"{status} {message}".strip())
        self.status = status
        self.retry_after = retry_after


def enrich(items: list[dict], timeout: float | None = None) -> list[dict]:
    """Enrich a batch of transactions.

    `items`: [{"id": str, "description": str, "amount": str}, ...]
    Returns one result per item, in the same order:
        [{"id": str, "merchant": str or None}, ...]
    `merchant` is None when the transaction isn't a merchant purchase (ATM,
    payroll) or the vendor doesn't recognize it.

    Raises VendorError for any non-200 response, or a 504 if `timeout`
    (seconds) passes first. With no timeout, waits as long as the vendor takes.
    """
    try:
        resp = _http.session().post(
            _http.url("/vendor/v1/enrich"),
            json={"items": items},
            headers={"Authorization": f"Bearer {settings.VENDOR_API_KEY}"},
            timeout=timeout,
        )
    except requests.Timeout as e:
        raise VendorError(504, "Gateway Timeout") from e
    except requests.ConnectionError as e:
        raise VendorError(503, f"Can't reach the vendor at {_http.url('')}") from e
    if resp.status_code != 200:
        raise VendorError(resp.status_code, _http.error_message(resp), retry_after=_http.retry_after(resp))
    return resp.json()["results"]
