import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from tracemind.retrieval import search_runbooks

from tracemind.analyzer import analyze_incident

from tracemind.investigator import investigate_incident

from tracemind.anomaly import detect_latency_anomalies

from tracemind.incident_report import build_incident_report

from tracemind.llm import generate_investigation

app = FastAPI(title="TraceMind", version="0.1.0")

LOG_FILE = Path(
    os.getenv(
        "TRACEMIND_LOG_FILE",
        str(
            Path(__file__).resolve().parents[3]
            / "datasets"
            / "samples"
            / "backend-logs.jsonl"
        ),
    )
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "tracemind"}

@app.get("/incidents/investigate")
def investigate_latest_incident():
    try:
        return investigate_incident(LOG_FILE)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/anomalies/latency")
def latency_anomalies():
    try:
        return detect_latency_anomalies(LOG_FILE)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/incidents/report")
def unified_incident_report():
    try:
        return build_incident_report(LOG_FILE)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/incidents/ai-investigate")
def ai_investigate():
    try:
        report = build_incident_report(LOG_FILE)
        result = generate_investigation(report)

        return {
            "incident": report,
            "ai_analysis": result,
        }
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/knowledge/search")
def search_knowledge(query: str, top_k: int = 3):
    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    if not 1 <= top_k <= 10:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and 10.",
        )

    results = search_runbooks(query, top_k)

    return {
        "query": query,
        "results_count": len(results),
        "results": results,
    }
 
@app.get("/incidents/latest")
def latest_incident():
    try:
        report = analyze_incident(LOG_FILE)
        return {
            "incident_detected": report["failed_requests"] > 0,
            "analysis": report,
        }
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc