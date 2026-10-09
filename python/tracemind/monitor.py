
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentMonitor:
    """Poll a log file and maintain one deduplicated active incident."""

    def __init__(
        self,
        log_file: str | Path,
        report_builder: Callable[[str | Path], dict],
        poll_interval: float = 5.0,
    ) -> None:
        self.log_file = Path(log_file)
        self.report_builder = report_builder
        self.poll_interval = max(1.0, poll_interval)

        self._task: asyncio.Task | None = None
        self._last_signature: tuple[int, int] | None = None
        self._last_check: str | None = None
        self._last_error: str | None = None

        self._active_incident: dict[str, Any] | None = None
        self._incident_history: list[dict[str, Any]] = []

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
            logger.info("TraceMind incident monitor started")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("TraceMind incident monitor stopped")

    async def _run(self) -> None:
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                self._last_error = "Unexpected monitoring error"
                logger.exception("Incident monitoring cycle failed")

            await asyncio.sleep(self.poll_interval)

    async def check_once(self) -> dict:
        """Analyze the log file only when its size or modification time changes."""
        try:
            stat = self.log_file.stat()
            signature = (stat.st_size, stat.st_mtime_ns)
        except FileNotFoundError:
            self._last_error = f"Log file not found: {self.log_file}"
            self._last_check = utc_now()
            return self.status()

        if signature == self._last_signature:
            return self.status()

        self._last_check = utc_now()

        try:
            report = await asyncio.to_thread(
                self.report_builder, self.log_file
            )
        except Exception:
            self._last_error = "Could not analyze the current log file"
            logger.exception("Could not build incident report")
            return self.status()

        # Avoid marking this file version as processed if it changed while
        # the report was being calculated. The next poll will process it.
        try:
            latest_stat = self.log_file.stat()
            latest_signature = (
                latest_stat.st_size,
                latest_stat.st_mtime_ns,
            )
        except FileNotFoundError:
            self._last_error = f"Log file not found: {self.log_file}"
            return self.status()

        if latest_signature != signature:
            return self.status()

        self._last_signature = signature
        self._last_error = None

        if not report.get("incident_detected", False):
            # Reports analyze historical logs. An empty result alone is not
            # sufficient evidence to resolve an already-open incident.
            return self.status()

        now = utc_now()

        if self._active_incident is None:
            self._active_incident = {
                "id": str(uuid.uuid4()),
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "acknowledged_at": None,
                "resolved_at": None,
                "report": report,
            }
            self._incident_history.append(self._active_incident.copy())
            logger.warning(
                "Incident detected: %s",
                self._active_incident["id"],
            )
        else:
            # Update the existing active incident instead of creating a
            # duplicate every time another log entry arrives.
            self._active_incident["updated_at"] = now
            self._active_incident["report"] = report

            incident_id = self._active_incident["id"]
            for historical in reversed(self._incident_history):
                if historical["id"] == incident_id:
                    historical.update(self._active_incident)
                    break

        return self.status()

    def acknowledge(self, incident_id: str) -> dict | None:
        incident = self._active_incident

        if incident is None or incident["id"] != incident_id:
            return None

        if incident["status"] == "active":
            incident["status"] = "acknowledged"
            incident["acknowledged_at"] = utc_now()
            incident["updated_at"] = utc_now()
            self._sync_history(incident)

        return incident.copy()

    def resolve(self, incident_id: str) -> dict | None:
        incident = self._active_incident

        if incident is None or incident["id"] != incident_id:
            return None

        incident["status"] = "resolved"
        incident["resolved_at"] = utc_now()
        incident["updated_at"] = utc_now()

        resolved = incident.copy()
        self._sync_history(incident)
        self._active_incident = None

        return resolved

    def _sync_history(self, incident: dict) -> None:
        for historical in reversed(self._incident_history):
            if historical["id"] == incident["id"]:
                historical.update(incident)
                return

    def status(self) -> dict:
        return {
            "monitoring": self._task is not None and not self._task.done(),
            "poll_interval_seconds": self.poll_interval,
            "log_file": str(self.log_file),
            "last_check": self._last_check,
            "last_error": self._last_error,
            "active_incident": (
                self._active_incident.copy()
                if self._active_incident is not None
                else None
            ),
            "incidents_seen": len(self._incident_history),
        }

    def active_incident(self) -> dict | None:
        return (
            self._active_incident.copy()
            if self._active_incident is not None
            else None
        )

    def history(self) -> list[dict]:
        return [item.copy() for item in self._incident_history]
