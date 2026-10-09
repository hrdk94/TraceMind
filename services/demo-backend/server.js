
import express from "express";
import pino from "pino";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";

const app = express();
const PORT = 3000;

const logPath = path.resolve(
  process.cwd(),
  "../../datasets/samples/backend-logs.jsonl"
);

fs.mkdirSync(path.dirname(logPath), { recursive: true });

const destination = pino.destination({
  dest: logPath,
  sync: true,
});

const logger = pino(
  { level: "info", base: { service: "order-api" } },
  destination
);

app.use((req, res, next) => {
  req.traceId = req.get("x-trace-id") || randomUUID();
  res.setHeader("x-trace-id", req.traceId);
  next();
});

app.get("/", (req, res) => {
  res.json({ message: "TraceMind demo backend is running" });
});

app.get("/orders", (req, res) => {
  const started = Date.now();
  const fail = req.query.fail;

  const logRequest = (statusCode, event, extra = {}) => {
    logger.info({
      timestamp: new Date().toISOString(),
      traceId: req.traceId,
      method: req.method,
      route: req.path,
      statusCode,
      latencyMs: Date.now() - started,
      event,
      ...extra,
    });
  };

  if (fail === "db") {
    logRequest(500, "dependency_failure", {
      dependency: "postgres",
      errorType: "DatabaseUnavailable",
      message: "Database connection failed",
    });

    return res.status(500).json({
      error: "Database connection failed",
      traceId: req.traceId,
    });
  }

  if (fail === "slow-db") {
    logRequest(200, "slow_dependency", {
      dependency: "postgres",
      latencyMs: 1200,
      message: "Database response exceeded latency threshold",
    });

    return res.json({
      message: "Simulated slow database response",
      simulatedLatencyMs: 1200,
      traceId: req.traceId,
    });
  }

  logRequest(200, "request_completed");

  res.json({
    message: "Orders fetched successfully",
    orders: [101, 102, 103],
    traceId: req.traceId,
  });
});

app.listen(PORT, () => {
  console.log(`Demo backend running at http://localhost:${PORT}`);
  console.log(`Writing structured logs to: ${logPath}`);
});
