
from pathlib import Path

from tracemind.ingestion.log_reader import load_logs


def investigate_incident(file_path: str | Path) -> dict:
    df = load_logs(file_path)

    if df.empty:
        return {
            "root_cause": "Insufficient data",
            "confidence": 0.0,
            "evidence": [],
            "recommendations": [
                "Collect more backend logs before investigating."
            ],
        }

    failures = df[df["statusCode"] >= 500]

    if failures.empty:
        return {
            "root_cause": "No server-side failures detected",
            "confidence": 0.95,
            "evidence": ["No HTTP 5xx responses found in the logs."],
            "recommendations": [
                "Continue monitoring request failures and latency."
            ],
        }

    evidence = []
    recommendations = []
    root_cause = "Unknown server-side failure"
    confidence = 0.50

    if "errorType" in failures:
        errors = failures["errorType"].dropna().astype(str)

        if errors.str.contains(
            "DatabaseUnavailable|DatabaseConnection|MongoNetwork",
            case=False,
            regex=True,
        ).any():
            root_cause = (
                "Database connectivity failure is the leading hypothesis."
            )
            confidence = 0.90

            evidence.append(
                "A failed request contains a database-related error type."
            )
            recommendations.extend([
                "Check database availability and connection health.",
                "Inspect database connection strings and credentials.",
                "Review connection pool saturation and database timeouts.",
            ])

    if "dependency" in failures:
        dependencies = failures["dependency"].dropna().unique().tolist()
        if dependencies:
            evidence.append(
                f"Failing request references dependency: "
                f"{', '.join(map(str, dependencies))}."
            )

    if not evidence:
        evidence.append(
            f"Observed {len(failures)} request(s) with HTTP status 500 or above."
        )
        recommendations.append(
            "Inspect the exception details and correlated service logs."
        )

    return {
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence": evidence,
        "recommendations": recommendations,
    }
