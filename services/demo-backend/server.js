
import express from "express";
import pino from "pino";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { performance } from "node:perf_hooks";

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
  {
    level: "info",
    base: {
      service: "order-api",
    },
  },
  destination
);

// Attach a trace ID to every request.
app.use((req, res, next) => {
  req.traceId = req.get("x-trace-id") || randomUUID();
  res.setHeader("x-trace-id", req.traceId);
  next();
});

// Health check endpoint.
app.get("/", (req, res) => {
  res.json({
    message: "TraceMind demo backend is running",
  });
});

// Orders endpoint with simulated database failures and latency.
app.get("/orders", (req, res) => {
  const started = performance.now();
  const fail = req.query.fail;

  const logRequest = (statusCode, event, extra = {}) => {
    const latencyMs = Number(
      (performance.now() - started).toFixed(3)
    );

    logger.info({
      timestamp: new Date().toISOString(),
      traceId: req.traceId,
      method: req.method,
      route: req.path,
      statusCode,
      latencyMs,
      event,
      ...extra,
    });
  };

  // Simulate a database connection failure.
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

  // Simulate a slow database response.
  if (fail === "slow-db") {
    return setTimeout(() => {
      logRequest(200, "slow_dependency", {
        dependency: "postgres",
        message: "Database response exceeded latency threshold",
      });

      res.json({
        message: "Simulated slow database response",
        traceId: req.traceId,
      });
    }, 1200);
  }

  // Normal request.
  logRequest(200, "request_completed");

  return res.json({
    message: "Orders fetched successfully",
    orders: [101, 102, 103],
    traceId: req.traceId,
  });
});

app.listen(PORT, () => {
  console.log(`Demo backend running at http://localhost:${PORT}`);
  console.log(`Writing structured logs to: ${logPath}`);
});
