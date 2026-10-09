
from pathlib import Path

from tracemind.analyzer import analyze_incident
from tracemind.investigator import investigate_incident
from tracemind.anomaly import detect_latency_anomalies
from tracemind.retrieval import search_runbooks


def build_incident_report(file_path: str | Path) -> dict:
    # 1. Analyze logs and calculate metrics first.
    analysis = analyze_incident(file_path)
    investigation = investigate_incident(file_path)
    latency = detect_latency_anomalies(file_path)

    failed_requests = analysis["failed_requests"]
    anomaly_count = latency["anomalies_detected"]

    # 2. Retrieve relevant runbook sections from the incident signals.
    search_terms = []

    if failed_requests > 0:
        search_terms.append("HTTP server errors and database connection failure")
        search_terms.extend(
            str(error_type)
            for error_type in analysis["error_types"]
        )

    if anomaly_count > 0:
        search_terms.append("slow requests dependency latency timeouts")

    if not search_terms:
        search_terms.append("general backend troubleshooting")

    knowledge = search_runbooks(" ".join(search_terms), top_k=3)

    # 3. Determine incident status and severity.
    incident_detected = failed_requests > 0 or anomaly_count > 0

    if failed_requests > 0:
        severity = "high"
    elif anomaly_count > 0:
        severity = "medium"
    else:
        severity = "none"

    recommendations = list(investigation["recommendations"])

    if anomaly_count > 0:
        recommendations.append(
            "Investigate slow requests and inspect dependency latency."
        )

    # 4. Describe the incident without claiming an unverified root cause.
    if not incident_detected:
        summary = "No incident detected in the available logs."
        root_cause = "No clear failure identified."
        confidence = 0.0
        evidence = []
    elif failed_requests > 0:
        summary = (
            f"Detected {failed_requests} failed request(s) "
            f"and {anomaly_count} latency anomalie(s)."
        )
        root_cause = investigation["root_cause"]
        confidence = investigation["confidence"]
        evidence = list(investigation["evidence"])

        if anomaly_count > 0:
            evidence.append(
                f"{anomaly_count} requests were flagged as latency anomalies."
            )
    else:
        summary = (
            f"Detected a latency incident with "
            f"{anomaly_count} anomalous request(s)."
        )
        root_cause = (
            "Unusually slow request processing; the underlying "
            "cause is not yet confirmed."
        )
        confidence = 0.70
        evidence = [
            f"{anomaly_count} requests were flagged as latency anomalies.",
            (
                f"Median latency among normal requests: "
                f"{latency['baseline_ms']} ms."
            ),
        ]

    # 5. Return the complete report.
    return {
        "incident_detected": incident_detected,
        "severity": severity,
        "summary": summary,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence": evidence,
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
        },
    }
