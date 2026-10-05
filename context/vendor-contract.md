# Enrichment vendor: key terms

Summary of our order form with Tagwise, the enrichment vendor, signed March 2026. Finance has the full contract.

- **API keys:** one production key. All limits apply per key, across all of our servers.
- **Concurrency:** at most 4 requests in flight per key. Requests over the limit get `429` with a `Retry-After` header.
- **Batch size:** at most 5,000 items per request. Larger requests get `413`.
- **Pricing:** $0.002 per item in every successful (`200`) response, including repeats of a transaction or description we've sent before. Failed and timed-out requests aren't billed. The committed minimum is $4,000/month.
- **Caching:** we may store and reuse results for up to 30 days. After that, re-enrich before showing the merchant to a member.
- **Data:** send only the transaction id, description and amount. No names, emails or account numbers.
- **SLA:** 99.5% monthly uptime, excluding announced maintenance. They've had several short outages this quarter, usually under a minute, sometimes longer.
