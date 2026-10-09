
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from tracemind.analyzer import analyze_incident
from tracemind.anomaly import detect_latency_anomalies
from tracemind.incident_report import build_incident_report
from tracemind.investigator import investigate_incident
from tracemind.llm import generate_investigation
from tracemind.monitor import IncidentMonitor
from tracemind.retrieval import search_runbooks


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

POLL_INTERVAL = float(os.getenv("TRACEMIND_POLL_INTERVAL", "5"))

monitor = IncidentMonitor(
    log_file=LOG_FILE,
    report_builder=build_incident_report,
    poll_interval=POLL_INTERVAL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await monitor.start()
    try:
        yield
    finally:
        await monitor.stop()


app = FastAPI(
    title="TraceMind",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/monitor/status")
def monitor_status():
    return monitor.status()


@app.post("/monitor/check")
async def check_monitor_now():
    """Manually trigger a check without waiting for the next poll."""
    try:
        return await monitor.check_once()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not check the log file.",
        ) from exc


@app.get("/incidents/active")
def active_incident():
    incident = monitor.active_incident()
    return {
        "incident_detected": incident is not None,
        "incident": incident,
    }


@app.get("/incidents/history")
def incident_history():
    return {
        "count": len(monitor.history()),
        "incidents": monitor.history(),
    }


@app.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: str):
    incident = monitor.acknowledge(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="No matching active incident found.",
        )
    return {"message": "Incident acknowledged.", "incident": incident}


@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str):
    incident = monitor.resolve(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="No matching active incident found.",
        )
    return {"message": "Incident resolved.", "incident": incident}
