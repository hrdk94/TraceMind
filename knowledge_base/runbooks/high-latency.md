
# Runbook: High Request Latency

## Symptoms
- Request latency is significantly above its normal baseline.
- API responses become slow even when HTTP status codes are successful.
- Requests may eventually time out.

## Potential causes
1. A slow database query or exhausted connection pool.
2. An overloaded application server.
3. A slow external API or downstream dependency.
4. Network delays or retry storms.

## Investigation steps
1. Identify the affected service and route.
2. Compare current latency with the normal traffic baseline.
3. Correlate slow requests using their trace IDs.
4. Inspect database and downstream dependency timings.
5. Check CPU, memory, connection pool utilization, and timeout logs.

## Remediation
- Optimize slow database queries and add appropriate indexes.
- Adjust connection pool limits only after confirming saturation.
- Set sensible timeouts for downstream calls.
- Apply bounded retries with backoff where appropriate.
- Scale services only when resource saturation is confirmed.

## Evidence required
A latency spike alone does not establish its root cause.
Confirm the responsible dependency using correlated traces,
metrics, or logs before applying a targeted fix.
