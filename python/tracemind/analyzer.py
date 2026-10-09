from pathlib import Path

import pandas as pd

from tracemind.ingestion.log_reader import load_logs


def analyze_incident(file_path: str | Path) -> dict:
    df = load_logs(file_path)

    if df.empty:
        return {
            "event_count": 0,
            "failed_requests": 0,
            "error_types": {},
            "services": [],
            "latency_ms": {"mean": None, "p95": None, "max": None},
        }

    failed = df[df["statusCode"] >= 500]

    error_types = (
        failed["errorType"].fillna("Unknown").value_counts().to_dict()
        if "errorType" in failed
        else {}
    )

    latency = df["latencyMs"].dropna()

    return {
        "event_count": int(len(df)),
        "failed_requests": int(len(failed)),
        "error_types": error_types,
        "services": sorted(
            df["service"].dropna().unique().tolist()
        ) if "service" in df else [],
        "latency_ms": {
            "mean": round(float(latency.mean()), 2) if len(latency) else None,
            "p95": round(float(latency.quantile(0.95)), 2)
            if len(latency) else None,
            "max": round(float(latency.max()), 2) if len(latency) else None,
        },
    }