import json
from pathlib import Path

import pandas as pd


def load_logs(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"No log file found: {path}")

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number}"
                ) from exc

    df = pd.DataFrame(records)

    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], utc=True, errors="coerce"
    )
    df["statusCode"] = pd.to_numeric(
        df["statusCode"], errors="coerce"
    )
    df["latencyMs"] = pd.to_numeric(
        df["latencyMs"], errors="coerce"
    )

    return df