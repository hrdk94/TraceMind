
import json

from tracemind.anomaly import detect_latency_anomalies
from tracemind.retrieval import search_runbooks
from tracemind.incident_report import build_incident_report


def write_logs(tmp_path, records):
    log_file = tmp_path / "backend-logs.jsonl"
    log_file.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )
    return log_file


def make_record(latency, event="request_completed", status=200):
    return {
        "timestamp": "2026-10-09T10:00:00Z",
        "service": "order-api",
        "route": "/orders",
        "statusCode": status,
        "latencyMs": latency,
        "event": event,
        "dependency": "postgres" if event == "slow_dependency" else None,
    }


def test_anomaly_detector_flags_slow_request(tmp_path):
    records = [
        make_record(value)
        for value in [10, 12, 9, 11, 10]
    ]
    records.append(
        make_record(1200, event="slow_dependency")
    )
    log_file = write_logs(tmp_path, records)

    result = detect_latency_anomalies(log_file)

    assert result["baseline_ms"] == 10.0
    assert result["anomalies_detected"] == 1
    assert result["anomalies"][0]["latency_ms"] == 1200.0


def test_runbook_retrieval_finds_latency_guidance():
    results = search_runbooks(
        "slow requests dependency latency timeouts",
        top_k=3,
    )

    assert results
    assert any(
        item["source"] == "high-latency.md"
        for item in results
    )


def test_unified_report_includes_latency_knowledge(tmp_path):
    records = [
        make_record(value)
        for value in [10, 12, 9, 11, 10]
    ]
    records.append(
        make_record(1200, event="slow_dependency")
    )
    log_file = write_logs(tmp_path, records)

    report = build_incident_report(log_file)

    assert report["incident_detected"] is True
    assert report["severity"] == "medium"
    assert report["metrics"]["latency_anomalies"] == 1
    assert report["knowledge"]
    assert any(
        item["source"] == "high-latency.md"
        for item in report["knowledge"]
    )
