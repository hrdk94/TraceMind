from pathlib import Path

import pandas as pd

from tracemind.ingestion.log_reader import load_logs


def detect_latency_anomalies(
    file_path: str | Path,
    min_samples: int = 5,
    z_threshold: float = 2.0,
    latency_floor_ms: float = 100.0,
) -> dict:
    """Detect unusually slow requests using a normal-traffic baseline.

    The absolute latency floor prevents tiny timing variations from being
    flagged when the baseline and median absolute deviation are near zero.
    Failed requests remain available to incident analysis but are not
    automatically classified as latency anomalies.
    """
    df = load_logs(file_path)

    if df.empty or "latencyMs" not in df.columns:
        return {
            "anomalies_detected": 0,
            "baseline_ms": None,
            "anomalies": [],
            "message": "No latency data available.",
        }

    df = df.copy()
    df["latencyMs"] = pd.to_numeric(df["latencyMs"], errors="coerce")
    df = df.dropna(subset=["latencyMs"])
    df = df[df["latencyMs"] >= 0]

    if df.empty:
        return {
            "anomalies_detected": 0,
            "baseline_ms": None,
            "anomalies": [],
            "message": "No valid latency measurements available.",
        }

    # Establish the baseline using successful, normal requests only.
    if "event" in df.columns:
        normal = df[df["event"] == "request_completed"]
    else:
        normal = df.iloc[0:0]

    if len(normal) < min_samples:
        return {
            "anomalies_detected": 0,
            "baseline_ms": None,
            "anomalies": [],
            "message": (
                f"Need at least {min_samples} normal requests "
                "to establish a latency baseline."
            ),
        }

    baseline = float(normal["latencyMs"].median())
    mad = float((normal["latencyMs"] - baseline).abs().median())

    # Keep the score numerically stable for very small latencies.
    # One millisecond is a scale floor, not the anomaly threshold.
    effective_scale = max(mad, 1.0)

    candidates = df.copy()

    # If statusCode is available, exclude failed requests from latency
    # anomaly classification. Failures are investigated separately.
    if "statusCode" in candidates.columns:
        candidates = candidates[
            pd.to_numeric(
                candidates["statusCode"], errors="coerce"
            ).fillna(0) < 500
        ]

    candidates["deviation_score"] = (
        0.6745
        * (candidates["latencyMs"] - baseline).abs()
        / effective_scale
    )

    # A request is anomalous if it crosses the absolute floor or is
    # statistically unusual and slower than the normal baseline.
    flagged = candidates[
        (candidates["latencyMs"] >= latency_floor_ms)
        | (
            (candidates["deviation_score"] > z_threshold)
            & (candidates["latencyMs"] > baseline)
        )
    ]

    anomalies = []

    for _, row in flagged.iterrows():
        timestamp = row.get("timestamp")
        if pd.isna(timestamp):
            timestamp = None
        elif hasattr(timestamp, "isoformat"):
            timestamp = timestamp.isoformat()
        else:
            timestamp = str(timestamp)

        trace_id = row.get("traceId")
        if pd.isna(trace_id):
            trace_id = None

        anomalies.append(
            {
                "timestamp": timestamp,
                "service": row.get("service"),
                "route": row.get("route"),
                "trace_id": trace_id,
                "event": row.get("event"),
                "latency_ms": round(float(row["latencyMs"]), 3),
                "deviation_score": round(
                    float(row["deviation_score"]), 2
                ),
            }
        )

    return {
        "anomalies_detected": len(anomalies),
        "baseline_ms": round(baseline, 3),
        "latency_floor_ms": latency_floor_ms,
        "anomalies": anomalies,
        "message": (
            "Latency anomalies detected."
            if anomalies
            else "No latency anomalies detected."
        ),
    }