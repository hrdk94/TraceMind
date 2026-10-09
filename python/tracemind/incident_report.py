from pathlib import Path

from tracemind.analyzer import analyze_incident
from tracemind.investigator import investigate_incident
from tracemind.anomaly import detect_latency_anomalies
from tracemind.retrieval import search_runbooks


def build_incident_report(file_path: str | Path) -> dict:
    """Build a unified, evidence-based incident report."""
    analysis = analyze_incident(file_path)
    investigation = investigate_incident(file_path)
    latency = detect_latency_anomalies(file_path)

    failed_requests = analysis["failed_requests"]
    anomaly_count = latency["anomalies_detected"]
    latency_stats = analysis["latency_ms"]

    # Retrieve runbook guidance from observed incident signals.
    search_terms = []

    if failed_requests:
        search_terms.append(
            "HTTP 500 server errors and database connectivity failure"
        )
        search_terms.extend(
            str(error_type)
            for error_type in analysis["error_types"]
        )

    if anomaly_count:
        search_terms.append(
            "slow request latency and downstream dependency timeouts"
        )

    if not search_terms:
        search_terms.append("general backend troubleshooting")

    knowledge = search_runbooks(" ".join(search_terms), top_k=3)

    # Determine incident status and severity.
    incident_detected = failed_requests > 0 or anomaly_count > 0

    if failed_requests > 0:
        severity = "high"
    elif anomaly_count > 0:
        severity = "medium"
    else:
        severity = "none"

    # Start with recommendations produced by the existing investigator.
    recommendations = list(investigation.get("recommendations", []))

    if failed_requests > 0:
        recommendations.extend(
            [
                "Check database availability and connection health.",
                "Inspect database connection settings and credentials.",
                "Review connection pool saturation and database timeouts.",
            ]
        )

    if anomaly_count > 0:
        recommendations.append(
            "Investigate slow requests and inspect dependency latency."
        )

    # Construct conclusions conservatively.
    if not incident_detected:
        summary = "No incident detected in the available logs."
        root_cause = "No clear failure identified in the available evidence."
        confidence = 0.0
        evidence = []
    elif failed_requests > 0:
        summary = (
            f"Detected {failed_requests} failed request(s) "
            f"and {anomaly_count} latency anomalie(s)."
        )

        root_cause = investigation.get(
            "root_cause",
            "Request failures detected; the underlying cause "
            "requires further investigation.",
        )
        confidence = float(investigation.get("confidence", 0.7))
        evidence = list(investigation.get("evidence", []))

        error_types = analysis["error_types"]
        if error_types:
            evidence.append(
                f"Observed failure types: {error_types}."
            )

        if anomaly_count:
            evidence.append(
                f"{anomaly_count} successful requests exceeded "
                "the configured latency anomaly criteria."
            )
    else:
        summary = (
            f"Detected a latency incident with "
            f"{anomaly_count} anomalous request(s)."
        )
        root_cause = (
            "Unusually slow request processing was observed; "
            "the underlying cause has not been confirmed."
        )
        confidence = 0.70
        evidence = [
            f"{anomaly_count} requests exceeded the latency "
            "anomaly criteria.",
            (
                "Median latency among normal requests: "
                f"{latency['baseline_ms']} ms."
            ),
        ]

    # Add latency statistics as evidence when measurements are available.
    if latency_stats["mean"] is not None:
        evidence.append(
            f"Mean latency across logged requests: "
            f"{latency_stats['mean']} ms."
        )
        evidence.append(
            f"95th-percentile latency across logged requests: "
            f"{latency_stats['p95']} ms."
        )
        evidence.append(
            f"Maximum latency across logged requests: "
            f"{latency_stats['max']} ms."
        )

    # Return both the original structure and explicit dashboard-friendly
    # metric fields. Existing API consumers can keep using old fields.
    return {
        "incident_detected": incident_detected,
        "severity": severity,
        "summary": summary,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence": list(dict.fromkeys(evidence)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "knowledge": [
            {
                "source": item["source"],
                "section": item["heading"],
                "relevance": item["score"],
                "guidance": item["text"],
            }
            for item in knowledge
        ],
        "metrics": {
            "event_count": analysis["event_count"],
            "failed_requests": failed_requests,
            "error_types": analysis["error_types"],
            "services": analysis["services"],
            "latency_baseline_ms": latency["baseline_ms"],
            "latency_anomalies": anomaly_count,
            "latency_anomalies_detail": latency["anomalies"],
            "latency_ms": latency_stats,
            "latency_mean_ms": latency_stats["mean"],
            "latency_median_ms": latency_stats["median"],
            "latency_p95_ms": latency_stats["p95"],
            "latency_max_ms": latency_stats["max"],
        },
    }