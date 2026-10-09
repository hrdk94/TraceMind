# Runbook: Database Connectivity Issues

## Symptoms
- The application cannot connect to the database.
- Connection attempts are refused or time out.
- Database queries fail intermittently.
- Requests fail when the connection pool is exhausted.

## Potential causes
1. The database server is unavailable or not accepting connections.
2. The connection string contains an incorrect host, port, or database name.
3. Database credentials are incorrect or have expired.
4. Network rules or firewalls block database traffic.
5. The connection pool is exhausted due to high traffic or leaked connections.

## Investigation steps
1. Identify the affected service and database.
2. Check database health and availability.
3. Verify the connection string, host, port, and database name.
4. Confirm credentials and authentication settings without exposing secrets.
5. Check network connectivity and firewall rules.
6. Inspect connection pool usage, active connections, and timeout logs.
7. Correlate failed requests using their trace IDs.

## Remediation
- Restore the database service if it is unavailable.
- Correct invalid connection settings or credentials.
- Update firewall and network rules when connectivity is blocked.
- Investigate leaked or long-running connections.
- Adjust connection pool limits only after confirming saturation and database capacity.
- Configure appropriate connection and query timeouts.
- Retry transient failures with bounded retries and backoff.

## Evidence required
A connection failure alone does not identify its root cause.
Use database health checks, connection error messages, configuration
validation, and correlated logs to confirm the failure mechanism.
Never include passwords, tokens, or other secrets in diagnostic logs.