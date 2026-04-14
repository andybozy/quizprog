#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    session_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    question_id TEXT,
    course_key TEXT,
    source_path TEXT,
    filter_mode TEXT,
    scope TEXT,
    event_type TEXT NOT NULL,
    selected_index INTEGER,
    correct_index INTEGER,
    result TEXT,
    app_version TEXT,
    build_number TEXT,
    metadata_json TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_received_at ON events(received_at);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_course_key ON events(course_key);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
"""


@dataclass
class ServerConfig:
    database_path: Path
    api_key: str | None = None


class EventRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def insert_events(self, events: list[dict[str, Any]], received_at: str) -> tuple[int, int]:
        inserted = 0
        deduplicated = 0
        with self._connect() as connection:
            for event in events:
                payload = json.dumps(event, ensure_ascii=False, sort_keys=True)
                metadata = json.dumps(event.get("metadata", {}), ensure_ascii=False, sort_keys=True)
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO events (
                        event_id, occurred_at, received_at, session_id, device_id, question_id,
                        course_key, source_path, filter_mode, scope, event_type, selected_index,
                        correct_index, result, app_version, build_number, metadata_json, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        event["occurred_at"],
                        received_at,
                        event["session_id"],
                        event["device_id"],
                        event.get("question_id"),
                        event.get("course_key"),
                        event.get("source_path"),
                        event.get("filter_mode"),
                        event.get("scope"),
                        event["event_type"],
                        event.get("selected_index"),
                        event.get("correct_index"),
                        event.get("result"),
                        event.get("app_version"),
                        event.get("build_number"),
                        metadata,
                        payload,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    deduplicated += 1
        return inserted, deduplicated

    def summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            by_type = {
                row["event_type"]: row["count"]
                for row in connection.execute(
                    "SELECT event_type, COUNT(*) AS count FROM events GROUP BY event_type ORDER BY event_type"
                )
            }
            by_course = {
                row["course_key"] or "(none)": row["count"]
                for row in connection.execute(
                    "SELECT course_key, COUNT(*) AS count FROM events GROUP BY course_key ORDER BY count DESC, course_key"
                )
            }
            recent = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT event_id, occurred_at, received_at, session_id, device_id, course_key, event_type, result
                    FROM events
                    ORDER BY received_at DESC
                    LIMIT 10
                    """
                )
            ]
        return {
            "total_events": total,
            "by_event_type": by_type,
            "by_course": by_course,
            "recent": recent,
        }

    def list_events(self, filters: dict[str, str], limit: int) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        for field in ("course_key", "event_type", "device_id", "session_id", "result"):
            value = filters.get(field)
            if value:
                clauses.append(f"{field} = ?")
                values.append(value)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT payload_json, received_at
        FROM events
        {where_clause}
        ORDER BY received_at DESC
        LIMIT ?
        """
        values.append(limit)

        with self._connect() as connection:
            rows = connection.execute(sql, values).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["server_received_at"] = row["received_at"]
            events.append(payload)
        return events

    def list_sessions(self, limit: int) -> list[dict[str, Any]]:
        sql = """
        SELECT
            session_id,
            MIN(occurred_at) AS started_at,
            MAX(occurred_at) AS ended_at,
            MAX(device_id) AS device_id,
            MAX(course_key) AS course_key,
            MAX(filter_mode) AS filter_mode,
            MAX(scope) AS scope,
            SUM(CASE WHEN event_type = 'question_answered' THEN 1 ELSE 0 END) AS answered_events,
            SUM(CASE WHEN event_type = 'question_skipped' THEN 1 ELSE 0 END) AS skipped_events
        FROM events
        GROUP BY session_id
        ORDER BY ended_at DESC
        LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(sql, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def export_jsonl(self) -> str:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM events ORDER BY occurred_at ASC"
            ).fetchall()
        return "\n".join(row["payload_json"] for row in rows)


class QuizLogRequestHandler(BaseHTTPRequestHandler):
    repository: EventRepository
    server_config: ServerConfig

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.respond_json({"status": "ok", "timestamp": now_iso()})
            return
        if parsed.path == "/api/summary":
            self.respond_json(self.repository.summary())
            return
        if parsed.path == "/api/events":
            params = parse_qs(parsed.query)
            filters = {key: values[0] for key, values in params.items() if values}
            limit = clamp_limit(filters.pop("limit", "100"))
            self.respond_json({"events": self.repository.list_events(filters, limit)})
            return
        if parsed.path == "/api/sessions":
            params = parse_qs(parsed.query)
            limit = clamp_limit(params.get("limit", ["100"])[0])
            self.respond_json({"sessions": self.repository.list_sessions(limit)})
            return
        if parsed.path == "/api/export.jsonl":
            payload = self.repository.export_jsonl().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path in {"/", "/dashboard"}:
            html = DASHBOARD_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/events/batch":
            self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        if self.server_config.api_key:
            provided_key = self.headers.get("X-API-Key", "")
            if provided_key != self.server_config.api_key:
                self.respond_json({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            self.respond_json({"error": f"Invalid JSON: {exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        events = payload.get("events")
        if not isinstance(events, list) or not events:
            self.respond_json({"error": "Payload must contain a non-empty 'events' array"}, status=HTTPStatus.BAD_REQUEST)
            return

        validation_errors = [error for event in events for error in validate_event(event)]
        if validation_errors:
            self.respond_json({"error": "Invalid event payload", "details": validation_errors[:20]}, status=HTTPStatus.BAD_REQUEST)
            return

        received_at = now_iso()
        inserted, deduplicated = self.repository.insert_events(events, received_at)
        self.respond_json(
            {
                "accepted": inserted,
                "deduplicated": deduplicated,
                "received_at": received_at,
            }
        )

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def respond_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def validate_event(event: Any) -> list[str]:
    if not isinstance(event, dict):
        return ["Event must be an object"]
    errors: list[str] = []
    for field in ("event_id", "occurred_at", "session_id", "device_id", "event_type"):
        value = event.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Missing required field: {field}")
    metadata = event.get("metadata", {})
    if metadata is not None and not isinstance(metadata, dict):
        errors.append("metadata must be an object")
    return errors


def clamp_limit(value: str, default: int = 100, minimum: int = 1, maximum: int = 1000) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QuizProg Log Dashboard</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; background: #f6f8fb; color: #1a2433; }
    h1, h2 { margin: 0 0 12px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .card { background: white; border: 1px solid #d6dde8; border-radius: 14px; padding: 16px; box-shadow: 0 8px 24px rgba(17, 24, 39, 0.06); }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; }
    th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #eef2f7; font-size: 14px; }
    th { background: #f1f5f9; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
    .muted { color: #516074; }
    .filters { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
    input { padding: 10px 12px; border: 1px solid #c9d3e0; border-radius: 10px; min-width: 220px; }
    button { padding: 10px 14px; border: 0; border-radius: 10px; background: #0b60d1; color: white; cursor: pointer; }
  </style>
</head>
<body>
  <h1>QuizProg Log Dashboard</h1>
  <p class="muted">Server-side event log for quiz sessions, answers, skips, and sync history.</p>

  <div class="grid" id="summary"></div>

  <div class="card">
    <h2>Recent Sessions</h2>
    <table id="sessions-table">
      <thead>
        <tr><th>Session</th><th>Course</th><th>Filter</th><th>Scope</th><th>Answered</th><th>Skipped</th><th>Ended</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="card" style="margin-top: 24px;">
    <h2>Recent Events</h2>
    <div class="filters">
      <input id="course-filter" placeholder="Filter by course_key" />
      <input id="event-filter" placeholder="Filter by event_type" />
      <button onclick="loadEvents()">Apply</button>
    </div>
    <table id="events-table">
      <thead>
        <tr><th>Occurred</th><th>Type</th><th>Course</th><th>Result</th><th>Question</th><th>Session</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <script>
    async function fetchJSON(path) {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      return await response.json();
    }

    function renderSummary(summary) {
      const items = [
        ['Total Events', summary.total_events],
        ['Event Types', Object.keys(summary.by_event_type).length],
        ['Courses', Object.keys(summary.by_course).length],
        ['Most Recent', summary.recent[0]?.received_at ?? '—'],
      ];
      document.getElementById('summary').innerHTML = items.map(([label, value]) =>
        `<div class="card"><div class="muted">${label}</div><div style="font-size: 24px; font-weight: 700;">${value}</div></div>`
      ).join('');
    }

    function renderSessions(sessions) {
      const rows = sessions.map(session => `
        <tr>
          <td><code>${session.session_id}</code></td>
          <td>${session.course_key ?? '—'}</td>
          <td>${session.filter_mode ?? '—'}</td>
          <td>${session.scope ?? '—'}</td>
          <td>${session.answered_events}</td>
          <td>${session.skipped_events}</td>
          <td>${session.ended_at ?? '—'}</td>
        </tr>
      `).join('');
      document.querySelector('#sessions-table tbody').innerHTML = rows;
    }

    function renderEvents(events) {
      const rows = events.map(event => `
        <tr>
          <td>${event.occurred_at}</td>
          <td>${event.event_type}</td>
          <td>${event.course_key ?? '—'}</td>
          <td>${event.result ?? '—'}</td>
          <td><code>${event.question_id ?? '—'}</code></td>
          <td><code>${event.session_id}</code></td>
        </tr>
      `).join('');
      document.querySelector('#events-table tbody').innerHTML = rows;
    }

    async function loadEvents() {
      const params = new URLSearchParams({ limit: '100' });
      const course = document.getElementById('course-filter').value.trim();
      const eventType = document.getElementById('event-filter').value.trim();
      if (course) params.set('course_key', course);
      if (eventType) params.set('event_type', eventType);
      const data = await fetchJSON(`/api/events?${params.toString()}`);
      renderEvents(data.events);
    }

    async function init() {
      const [summary, sessions] = await Promise.all([
        fetchJSON('/api/summary'),
        fetchJSON('/api/sessions?limit=50'),
      ]);
      renderSummary(summary);
      renderSessions(sessions.sessions);
      renderEvents(summary.recent.map(event => ({
        occurred_at: event.occurred_at,
        event_type: event.event_type,
        course_key: event.course_key,
        result: event.result,
        question_id: event.event_id,
        session_id: event.session_id
      })));
      await loadEvents();
    }

    init().catch(error => {
      document.body.insertAdjacentHTML('beforeend', `<p style="color: #b42318;">${error.message}</p>`);
    });
  </script>
</body>
</html>
"""


def build_handler(repository: EventRepository, server_config: ServerConfig):
    class ConfiguredHandler(QuizLogRequestHandler):
        pass

    ConfiguredHandler.repository = repository
    ConfiguredHandler.server_config = server_config
    return ConfiguredHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QuizProg event log server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--database",
        default=str(Path("server") / "quizlog.sqlite3"),
        help="SQLite database path",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("QUIZLOG_API_KEY", ""),
        help="Optional X-API-Key required for POST /events/batch",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = ServerConfig(
        database_path=Path(args.database).resolve(),
        api_key=args.api_key.strip() or None,
    )
    repository = EventRepository(config.database_path)
    handler = build_handler(repository, config)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"QuizProg log server listening on http://{args.host}:{args.port}")
    print(f"Database: {config.database_path}")
    if config.api_key:
        print("API key protection enabled for POST /events/batch")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
