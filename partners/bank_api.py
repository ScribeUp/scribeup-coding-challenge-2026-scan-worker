"""Client for each client's banking platform API.

    GET /bank/v1/{client}/members/{member_id}/transactions?cursor=...&page_size=...

Treat this like a vendor SDK: use it, don't change it. See partners/README.md
for how the API behaves.
"""

from __future__ import annotations

import requests

from . import _http


class BankAPIError(Exception):
    def __init__(self, status: int, message: str = "", retry_after: float | None = None):
        super().__init__(f"{status} {message}".strip())
        self.status = status
        self.retry_after = retry_after


def list_transactions(
    client: str,
    member_external_id: str,
    cursor: str | None = None,
    page_size: int | None = None,
    timeout: float = 30,
) -> dict:
    """Return one page of a member's transactions, newest first:

        {
          "account": {"account_number": "...", "holder_email": "..."},
          "data": [<client-formatted rows>],
          "next_cursor": "..." or None,
        }

    Raises BankAPIError for any non-200 response. On a 429, `retry_after` is
    how many seconds the bank asks you to wait.
    """
    params = {}
    if cursor:
        params["cursor"] = cursor
    if page_size:
        params["page_size"] = page_size
    try:
        resp = _http.session().get(
            _http.url(f"/bank/v1/{client}/members/{member_external_id}/transactions"), params=params, timeout=timeout
        )
    except requests.Timeout as e:
        raise BankAPIError(504, "Timed out") from e
    except requests.ConnectionError as e:
        raise BankAPIError(503, f"Can't reach the bank API at {_http.url('')}") from e
    if resp.status_code != 200:
        raise BankAPIError(resp.status_code, _http.error_message(resp), retry_after=_http.retry_after(resp))
    return resp.json()
