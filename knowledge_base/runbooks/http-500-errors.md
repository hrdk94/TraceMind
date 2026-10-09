# Runbook: HTTP 500 Errors

## Symptoms
- API requests return HTTP 500 Internal Server Error.
- Requests fail unexpectedly despite valid client input.
- Errors occur intermittently or after a deployment.
- Failures may coincide with database or downstream service errors.

## Potential causes
1. Unhandled exceptions in application code.
2. Database queries or external API calls failing.
3. Missing environment variables or incorrect configuration.
4. Invalid assumptions about request data or database records.
5. Resource exhaustion or incompatible changes after deployment.

## Investigation steps
1. Identify the affected service, endpoint, and time window.
2. Record the HTTP status, timestamp, and request trace ID.
3. Find the corresponding request in application logs.
4. Inspect stack traces and exception messages.
5. Check database and downstream dependency failures.
6. Compare recent deployments and configuration changes.
7. Review CPU, memory, and other resource metrics if relevant.
8. Reproduce the failure in a controlled environment using the same inputs.

## Remediation
- Handle expected exceptions and validate inputs appropriately.
- Fix the underlying application bug identified in the stack trace.
- Restore unavailable dependencies or correct their configuration.
- Add appropriate error handling and safe, informative logging.
- Roll back a deployment if evidence links it to the regression.
- Avoid exposing stack traces, credentials, or internal details to API clients.

## Evidence required
An HTTP 500 response indicates a server-side failure but does not
establish the root cause.
Correlate the request trace ID with application logs, stack traces,
dependency timings, and deployment history.
Verify the fix with repeatable regression tests and confirm that
the affected endpoint returns the expected response.