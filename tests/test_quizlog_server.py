import json
import threading
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from server.quizlog_server import EventRepository, ServerConfig, build_handler
from http.server import ThreadingHTTPServer


def test_quizlog_server_ingests_and_lists_events():
    with TemporaryDirectory() as tmp:
        database_path = Path(tmp) / "quizlog.sqlite3"
        repository = EventRepository(database_path)
        handler = build_handler(repository, ServerConfig(database_path=database_path))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            payload = {
                "events": [
                    {
                        "event_id": "evt-1",
                        "occurred_at": "2026-04-14T12:00:00Z",
                        "session_id": "sess-1",
                        "device_id": "dev-1",
                        "question_id": "q-1",
                        "course_key": "01_FinY_Trib3",
                        "source_path": "01_FinY_Trib3/primero_finYtrib.json",
                        "filter_mode": "due",
                        "scope": "repository",
                        "event_type": "question_answered",
                        "selected_index": 1,
                        "correct_index": 1,
                        "result": "correct",
                        "app_version": "1.0",
                        "build_number": "1",
                        "metadata": {"score": "1"},
                    }
                ]
            }
            request = urllib.request.Request(
                f"{base_url}/events/batch",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                body = json.loads(response.read().decode("utf-8"))
            assert body["accepted"] == 1

            with urllib.request.urlopen(f"{base_url}/api/summary") as response:
                summary = json.loads(response.read().decode("utf-8"))
            assert summary["total_events"] == 1
            assert summary["by_event_type"]["question_answered"] == 1

            with urllib.request.urlopen(f"{base_url}/api/events?course_key=01_FinY_Trib3") as response:
                events = json.loads(response.read().decode("utf-8"))["events"]
            assert len(events) == 1
            assert events[0]["event_id"] == "evt-1"

            with urllib.request.urlopen(f"{base_url}/api/export.jsonl") as response:
                export_body = response.read().decode("utf-8")
            assert '"event_id": "evt-1"' in export_body
        finally:
            server.shutdown()
            thread.join(timeout=5)
