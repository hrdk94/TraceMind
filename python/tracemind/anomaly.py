
from pathlib import Path

from tracemind.ingestion.log_reader import load_logs


def detect_latency_anomalies(
    file_path: str | Path,
    min_samples: int = 5,
    z_threshold: float = 2.0,
) -> dict:
    df = load_logs(file_path)

    if df.empty or "latencyMs" not in df:
        return {
            "anomalies_detected": 0,
            "baseline_ms": None,
            "anomalies": [],
            "message": "No latency data available.",
        }

    df = df.dropna(subset=["latencyMs"]).copy()
    df = df[df["latencyMs"] >= 0]

    if len(df) < min_samples:
        return {
            "anomalies_detected": 0,
            "baseline_ms": None,
            "anomalies": [],
            "message": (
                f"Need at least {min_samples} requests to establish "
                "a latency baseline."
            ),
        }

    # Use the median and median absolute deviation for robustness.
    median = float(df["latencyMs"].median())
    mad = float((df["latencyMs"] - median).abs().median())

    if mad == 0:
        # Fall back to standard deviation when MAD cannot separate values.
        std = float(df["latencyMs"].std(ddof=0))

        if std == 0:
            return {
                "anomalies_detected": 0,
                "baseline_ms": round(median, 2),
                "anomalies": [],
                "message": "Latency values have no observed variation.",
            }

        scores = (df["latencyMs"] - median).abs() / std
    else:
        # 0.6745 makes the MAD-based score comparable to a z-score.
        scores = 0.6745 * (df["latencyMs"] - median).abs() / mad

    anomalous = df[scores > z_threshold]

    anomalies = []
    for _, row in anomalous.iterrows():
        anomalies.append({
            "timestamp": (
                row["timestamp"].isoformat()
                if "timestamp" in row and not __import__("pandas").isna(row["timestamp"])
                else None
            ),
            "service": row.get("service"),
            "route": row.get("route"),
            "latency_ms": float(row["latencyMs"]),
            "deviation_score": round(float(scores.loc[row.name]), 2),
        })

    return {
        "anomalies_detected": len(anomalies),
        "baseline_ms": round(median, 2),
        "anomalies": anomalies,
        "message": (
            "Latency anomalies detected."
            if anomalies
            else "No latency anomalies detected."
        ),
    }
from pathlib import Path

from tracemind.ingestion.log_reader import load_logs


def detect_latency_anomalies(
    file_path: str | Path,
    min_samples: int = 5,
    z_threshold: float = 2.0,
    latency_floor_ms: float = 100.0,
) -> dict:
    df = load_logs(file_path)

    if df.empty or "latencyMs" not in df:
        return {
            "anomalies_detected": 0,
            "baseline_ms": None,
            "anomalies": [],
            "message": "No latency data available.",
        }

    df = df.dropna(subset=["latencyMs"]).copy()
    df = df[df["latencyMs"] >= 0]

    if "event" in df:
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
                "to establish a baseline."
            ),
        }

    baseline = float(normal["latencyMs"].median())
    mad = float((normal["latencyMs"] - baseline).abs().median())

    candidates = df[df.get(
        "event",
        df["statusCode"].astype(str).map(lambda _: ""),
    ) != "request_completed"].copy()

    if mad > 0:
        candidates["deviation_score"] = (
            0.6745 * (candidates["latencyMs"] - baseline).abs() / mad
        )
        flagged = candidates[
            (candidates["latencyMs"] >= latency_floor_ms)
            | (candidates["deviation_score"] > z_threshold)
        ]
    else:
        candidates["deviation_score"] = None
        flagged = candidates[
            candidates["latencyMs"] >= latency_floor_ms
        ]

    anomalies = []
    for _, row in flagged.iterrows():
        timestamp = row.get("timestamp")
        anomalies.append({
            "timestamp": (
                timestamp.isoformat()
                if timestamp is not None and not __import__("pandas").isna(timestamp)
                else None
            ),
            "service": row.get("service"),
            "route": row.get("route"),
            "latency_ms": float(row["latencyMs"]),
            "deviation_score": (
                round(float(row["deviation_score"]), 2)
                if row["deviation_score"] is not None
                else None
            ),
        })

    return {
        "anomalies_detected": len(anomalies),
        "baseline_ms": round(baseline, 2),
        "anomalies": anomalies,
        "message": (
            "Latency anomalies detected."
            if anomalies
            else "No latency anomalies detected."
        ),
    }
