import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const REFRESH_MS = 5000;

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.message || `Request failed (${response.status})`);
  }
  return body;
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function formatMs(value) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? "—"
    : `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 3 })} ms`;
}

function Severity({ value }) {
  const severity = String(value || "none").toLowerCase();
  return <span className={`severity-pill ${severity}`}>{severity.toUpperCase()}</span>;
}

function MetricCard({ label, value, detail, icon }) {
  return (
    <article className="metric-card">
      <div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div>
      <div className="metric-value">{value ?? "—"}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function EvidenceList({ items }) {
  if (!items?.length) return <p className="muted">No evidence was returned.</p>;
  return <ul className="evidence-list">{items.map((item, index) => (
    <li key={`${index}-${item}`}><span className="evidence-check">✓</span><span>{item}</span></li>
  ))}</ul>;
}

function RunbookCard({ item }) {
  return (
    <article className="runbook-card">
      <div className="runbook-card-top">
        <span className="runbook-icon">▤</span>
        <div><strong>{item.source || "Runbook"}</strong><p>{item.section || item.heading || "Guidance"}</p></div>
        {item.relevance !== undefined && <span className="relevance">{Math.round(Number(item.relevance) * 100)}%</span>}
      </div>
      <p className="runbook-guidance">{item.guidance || item.text || "No guidance provided."}</p>
    </article>
  );
}

export default function App() {
  const [health, setHealth] = useState("checking");
  const [monitorStatus, setMonitorStatus] = useState(null);
  const [incident, setIncident] = useState(null);
  const [activeIncident, setActiveIncident] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);

  const refreshData = useCallback(async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true);
    try {
      const [healthResult, statusResult, activeResult, reportResult] = await Promise.all([
        apiRequest("/health"),
        apiRequest("/monitor/status"),
        apiRequest("/incidents/active"),
        apiRequest("/incidents/report"),
      ]);
      setHealth(healthResult.status === "ok" ? "connected" : "unknown");
      setMonitorStatus(statusResult);
      setActiveIncident(activeResult.incident || null);
      setIncident(reportResult);
      setLastUpdated(new Date());
      setError("");
    } catch (err) {
      setHealth("disconnected");
      setError(err.message || "Could not connect to TraceMind API.");
    } finally {
      if (showSpinner) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshData(true);
    const timer = window.setInterval(() => refreshData(false), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refreshData]);

  const runAIInvestigation = async () => {
    setLoadingAI(true);
    setError("");
    try {
      const result = await apiRequest("/incidents/ai-investigate");
      setIncident(result.incident || null);
      setAiAnalysis(result.ai_analysis || null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || "AI investigation failed.");
    } finally {
      setLoadingAI(false);
    }
  };

  const runMonitorCheck = async () => {
    setRefreshing(true);
    setError("");
    try {
      await apiRequest("/monitor/check", { method: "POST" });
      await refreshData(false);
    } catch (err) {
      setError(err.message || "Monitor check failed.");
    } finally {
      setRefreshing(false);
    }
  };

  const updateIncidentStatus = async (action) => {
    if (!activeIncident?.id) return;
    setActionBusy(true);
    setError("");
    try {
      await apiRequest(`/incidents/${encodeURIComponent(activeIncident.id)}/${action}`, { method: "POST" });
      await refreshData(false);
    } catch (err) {
      setError(err.message || `Could not ${action} incident.`);
    } finally {
      setActionBusy(false);
    }
  };

  const metrics = incident?.metrics || {};
  const latency = metrics.latency_ms || {};
  const anomalies = metrics.latency_anomalies_detail || [];
  const runbooks = incident?.knowledge || [];
  const confidence = Math.max(0, Math.min(100, Math.round((Number(incident?.confidence) || 0) * 100)));
  const incidentDetected = Boolean(incident?.incident_detected);
  const monitorOnline = Boolean(monitorStatus?.monitoring);
  const metricCards = useMemo(() => [
    { label: "Incident severity", value: incidentDetected ? String(incident?.severity || "unknown").toUpperCase() : "CLEAR", detail: incidentDetected ? "Current log analysis" : "No incident in current logs", icon: "◈" },
    { label: "Failed requests", value: metrics.failed_requests ?? "—", detail: "HTTP 5xx responses", icon: "⚠" },
    { label: "Latency anomalies", value: metrics.latency_anomalies ?? "—", detail: "Requests above detection criteria", icon: "↗" },
    { label: "Log events", value: metrics.event_count ?? "—", detail: "Events in the current log file", icon: "▤" },
  ], [incidentDetected, incident?.severity, metrics.failed_requests, metrics.latency_anomalies, metrics.event_count]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">T</div><div><h1>TraceMind</h1><span>AI INCIDENT INTELLIGENCE</span></div></div>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav-item active" href="#overview"><span>◫</span> Overview</a>
        <a className="nav-item" href="#active-incident"><span>⚑</span> Incidents</a>
        <a className="nav-item" href="#investigation"><span>✳</span> AI investigation</a>
        <a className="nav-item" href="#runbooks"><span>▤</span> Runbooks</a>
        <div className="sidebar-bottom"><span className={`status-dot ${health === "connected" ? "online-dot" : ""}`} /><div><strong>{health === "connected" ? "API connected" : health === "checking" ? "Connecting…" : "API disconnected"}</strong><span>{monitorOnline ? "Background monitor running" : "Monitor not confirmed"}</span></div></div>
      </aside>

      <section className="main-content" id="overview">
        <header className="topbar"><div className="breadcrumbs">TraceMind <span>/</span> Observability <span>/</span> Overview</div><div className={`connection ${health === "connected" ? "connected" : ""}`}><span className={`status-dot ${health === "connected" ? "online-dot" : ""}`} />{health === "connected" ? "API connected" : health === "checking" ? "Connecting to API" : "API unavailable"}</div></header>

        <div className="page-heading"><div><div className="eyebrow">OBSERVABILITY WORKSPACE</div><h2>Incident overview</h2><p>Detect anomalies, inspect evidence, and investigate backend incidents.</p></div><div className="heading-actions"><button className="secondary-button" onClick={() => refreshData(true)} disabled={refreshing}>{refreshing ? "Refreshing…" : "↻ Refresh"}</button><button className="primary-button" onClick={runMonitorCheck} disabled={refreshing}>Check logs now</button></div></div>

        {error && <div className="error-banner" role="alert">{error}</div>}

        <div className="monitor-strip"><div><span className={`status-dot ${monitorOnline ? "online-dot" : ""}`} /><strong>{monitorOnline ? "Background monitoring active" : "Monitoring status unavailable"}</strong><span className="muted"> · Poll interval: {monitorStatus?.poll_interval_seconds ?? "—"}s</span></div><div className="muted">Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}</div></div>

        <section className="metrics-grid">{metricCards.map((item) => <MetricCard key={item.label} {...item} />)}</section>

        <div className="content-grid">
          <section className="panel" id="active-incident">
            <div className="panel-heading"><div><div className="eyebrow">CURRENT ASSESSMENT</div><h3>Incident summary</h3></div><Severity value={incident?.severity} /></div>
            {incidentDetected ? <>
              <div className="incident-summary"><div className="incident-symbol">!</div><div><h4>{incident.summary}</h4><p>{incident.root_cause}</p></div></div>
              <div className="divider" />
              <div className="section-label">LATENCY STATISTICS</div>
              <div className="metric-row"><span>Baseline median</span><strong>{formatMs(metrics.latency_baseline_ms)}</strong></div>
              <div className="metric-row"><span>Mean latency</span><strong>{formatMs(metrics.latency_mean_ms ?? latency.mean)}</strong></div>
              <div className="metric-row"><span>Median latency</span><strong>{formatMs(metrics.latency_median_ms ?? latency.median)}</strong></div>
              <div className="metric-row"><span>95th percentile</span><strong>{formatMs(metrics.latency_p95_ms ?? latency.p95)}</strong></div>
              <div className="metric-row"><span>Maximum latency</span><strong>{formatMs(metrics.latency_max_ms ?? latency.max)}</strong></div>
            </> : <div className="empty-state"><span>✓</span><p>No incident detected in the available logs.</p><small>The monitor will recheck when the log file changes.</small></div>}
            {activeIncident && <div className="active-incident-card"><div className="panel-heading"><div><div className="eyebrow">TRACKED INCIDENT</div><h3>{activeIncident.status}</h3></div><Severity value={activeIncident.report?.severity} /></div><p className="muted">ID: <code>{activeIncident.id}</code></p><p className="muted">Opened: {formatTime(activeIncident.created_at)}</p><div className="action-row">{activeIncident.status === "active" && <button className="secondary-button" disabled={actionBusy} onClick={() => updateIncidentStatus("acknowledge")}>Acknowledge</button>}<button className="secondary-button" disabled={actionBusy} onClick={() => updateIncidentStatus("resolve")}>Resolve</button></div></div>}
          </section>

          <section className="panel" id="runbooks"><div className="panel-heading"><div><div className="eyebrow">KNOWLEDGE BASE</div><h3>Relevant runbooks</h3></div><span className="count-badge">{runbooks.length} sections</span></div>{runbooks.length ? <div className="runbook-list">{runbooks.map((item, index) => <RunbookCard key={`${item.source}-${item.section}-${index}`} item={item} />)}</div> : <div className="empty-state compact"><span>▤</span><p>No runbooks returned</p><small>Runbook guidance will appear when relevant to current signals.</small></div>}</section>
        </div>

        <section className="panel evidence-panel" id="investigation">
          <div className="panel-heading"><div><div className="eyebrow">INVESTIGATION WORKSPACE</div><h3>AI analysis &amp; evidence</h3></div><div className="investigation-actions"><span className="ai-badge">✳ qwen2.5:3b</span><button className="primary-button" onClick={runAIInvestigation} disabled={loadingAI || health !== "connected"}>{loadingAI ? "Investigating…" : "Run AI investigation"}</button></div></div>
          {!aiAnalysis && <p className="muted">AI investigation runs on demand. Routine dashboard refreshes do not call the language model.</p>}
          {aiAnalysis && <div className="investigation-report"><div className="report-banner"><div><div className="eyebrow">INVESTIGATION RESULT</div><h4>{incident?.summary || "Investigation completed"}</h4><p>{incident?.root_cause || "No confirmed root cause was returned."}</p></div><Severity value={incident?.severity} /></div><div className="confidence-row"><span>Incident assessment confidence</span><strong>{confidence}%</strong></div><div className="confidence-track"><div className="confidence-fill" style={{ width: `${confidence}%` }} /></div><p className="muted confidence-note">Confidence in the incident assessment does not mean the root cause has been confirmed.</p>
            <div className="report-section"><h4>AI investigation</h4><div className="ai-narrative"><ReactMarkdown>{aiAnalysis.investigation || "No AI explanation was returned."}</ReactMarkdown></div></div>
            <div className="report-section"><h4>Evidence from incident data</h4><EvidenceList items={incident?.evidence || []} /></div>
            <div className="report-section"><h4>Recommended actions</h4>{incident?.recommendations?.length ? <ol className="recommendation-list">{incident.recommendations.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ol> : <p className="muted">No recommendations provided.</p>}</div>
            <div className="report-section"><h4>Anomalous requests</h4><p className="muted">{anomalies.length} flagged request(s) in the available incident metrics.</p>{anomalies.length ? <div className="table-scroll"><table className="anomaly-table"><thead><tr><th>Service</th><th>Route</th><th>Latency</th><th>Trace ID</th><th>Timestamp</th></tr></thead><tbody>{anomalies.map((item, index) => <tr key={`${item.trace_id || item.timestamp}-${index}`}><td>{item.service || "—"}</td><td><code>{item.route || "—"}</code></td><td className="latency-value">{formatMs(item.latency_ms)}</td><td><code>{item.trace_id || "—"}</code></td><td>{formatTime(item.timestamp)}</td></tr>)}</tbody></table></div> : <p className="muted">No anomalous request details available.</p>}</div>
            <div className="report-section"><h4>Runbooks used in this investigation</h4>{runbooks.length ? <div className="investigation-runbooks">{runbooks.map((item, index) => <RunbookCard key={`${item.source}-${item.section}-${index}`} item={item} />)}</div> : <p className="muted">No runbook details were returned.</p>}{aiAnalysis.sources?.length > 0 && <p className="source-note">AI-reported sources: {aiAnalysis.sources.join(", ")}</p>}</div>
          </div>}
        </section>

        <footer><span>TraceMind <span className="footer-muted">· Evidence-driven incident investigation</span></span><span>Local development · v0.2.0</span></footer>
      </section>
    </main>
  );
}
