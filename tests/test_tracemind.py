
import json

from tracemind.ingestion.log_reader import load_logs
from tracemind.analyzer import analyze_incident


def test_load_logs_reads_jsonl(tmp_path):
    log_file = tmp_path / "logs.jsonl"

    records = [
        {
            "timestamp": "2026-10-09T10:00:00Z",
            "service": "order-api",
            "statusCode": 200,
            "latencyMs": 25,
            "event": "request_completed",
        },
        {
            "timestamp": "2026-10-09T10:00:01Z",
            "service": "order-api",
            "statusCode": 500,
            "latencyMs": 40,
            "event": "dependency_failure",
            "errorType": "DatabaseUnavailable",
        },
    ]

    log_file.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    df = load_logs(log_file)

    assert len(df) == 2
    assert df["statusCode"].tolist() == [200, 500]


def test_analyzer_detects_failed_requests(tmp_path):
    log_file = tmp_path / "logs.jsonl"

    records = [
        {
            "timestamp": "2026-10-09T10:00:00Z",
            "service": "order-api",
            "statusCode": 200,
            "latencyMs": 25,
            "event": "request_completed",
        },
        {
            "timestamp": "2026-10-09T10:00:01Z",
            "service": "order-api",
            "statusCode": 500,
            "latencyMs": 40,
            "event": "dependency_failure",
            "errorType": "DatabaseUnavailable",
        },
    ]

    log_file.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    report = analyze_incident(log_file)

    assert report["event_count"] == 2
    assert report["failed_requests"] == 1
    assert report["error_types"]["DatabaseUnavailable"] == 1
    assert report["services"] == ["order-api"]
