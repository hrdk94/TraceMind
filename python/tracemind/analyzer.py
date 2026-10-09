from pathlib import Path

import pandas as pd

from tracemind.ingestion.log_reader import load_logs


def analyze_incident(file_path: str | Path) -> dict:
    """Calculate request counts, failure counts, and latency statistics."""
    df = load_logs(file_path)

    empty_latency = {
        "mean": None,
        "median": None,
        "p95": None,
        "max": None,
    }

    if df.empty:
        return {
            "event_count": 0,
            "failed_requests": 0,
            "error_types": {},
            "services": [],
            "latency_ms": empty_latency,
        }

    # Handle missing or malformed status codes safely.
    if "statusCode" in df.columns:
        status_codes = pd.to_numeric(
            df["statusCode"], errors="coerce"
        )
        failed = df[status_codes >= 500]
    else:
        failed = df.iloc[0:0]

    if "errorType" in failed.columns:
        error_types = (
            failed["errorType"]
            .fillna("Unknown")
            .replace("", "Unknown")
            .value_counts()
            .to_dict()
        )
        error_types = {
            str(name): int(count)
            for name, count in error_types.items()
        }
    else:
        error_types = {}

    if "latencyMs" in df.columns:
        latency = pd.to_numeric(
            df["latencyMs"], errors="coerce"
        )
        latency = latency[latency.notna() & (latency >= 0)]
    else:
        latency = pd.Series(dtype="float64")

    if len(latency):
        latency_stats = {
            "mean": round(float(latency.mean()), 3),
            "median": round(float(latency.median()), 3),
            "p95": round(float(latency.quantile(0.95)), 3),
            "max": round(float(latency.max()), 3),
        }
    else:
        latency_stats = empty_latency.copy()

    services = (
        sorted(df["service"].dropna().astype(str).unique().tolist())
        if "service" in df.columns
        else []
    )

    return {
        "event_count": int(len(df)),
        "failed_requests": int(len(failed)),
        "error_types": error_types,
        "services": services,
        "latency_ms": latency_stats,
    }