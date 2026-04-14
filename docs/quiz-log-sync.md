# QuizProg Remote Event Log

## Overview

The iOS app now writes a complete append-only quiz event log locally and can sync that log to an external server.

Implemented pieces:

- local persistent event storage on iOS
- append-only event records for quiz lifecycle and answers
- outbox-style sync to a remote HTTP endpoint
- server-side SQLite storage
- browser dashboard and JSON/JSONL APIs
- local JSONL export from the iOS app

## Event types

The app records:

- `quiz_started`
- `quiz_resumed`
- `question_answered`
- `question_skipped`
- `quiz_exited`
- `quiz_finished`

## Event fields

Each event includes at least:

- `event_id`
- `occurred_at`
- `session_id`
- `device_id`
- `question_id`
- `course_key`
- `source_path`
- `filter_mode`
- `scope`
- `event_type`
- `selected_index`
- `correct_index`
- `result`
- `app_version`
- `build_number`
- `metadata`

## iOS setup

Open the app home screen and use the `Event Log` card.

You can:

- configure the remote base URL
- optionally configure an API key
- enable or disable auto sync
- run manual sync
- export the local log as JSONL

The app expects the server base URL, for example:

- `https://quizlog.example.com`
- `http://192.168.1.20:8787` for local testing

The app sends batches to:

- `<base-url>/events/batch`

The browser dashboard lives at:

- `<base-url>/dashboard`

## Running the backend

Start the server from the repo root:

```bash
python3 server/quizlog_server.py --host 0.0.0.0 --port 8787
```

Optional API key protection for event ingestion:

```bash
QUIZLOG_API_KEY=your-secret python3 server/quizlog_server.py --host 0.0.0.0 --port 8787
```

Or:

```bash
python3 server/quizlog_server.py --host 0.0.0.0 --port 8787 --api-key your-secret
```

The server stores data in:

- `server/quizlog.sqlite3`

## Access from another computer

If the server is reachable on the network, open in a browser:

```text
http://<server-host>:8787/dashboard
```

Useful API endpoints:

- `GET /health`
- `GET /api/summary`
- `GET /api/events`
- `GET /api/sessions`
- `GET /api/export.jsonl`
- `POST /events/batch`

Example:

```bash
curl http://127.0.0.1:8787/api/summary
```

Filtered events:

```bash
curl "http://127.0.0.1:8787/api/events?course_key=01_FinY_Trib3&event_type=question_answered&limit=50"
```

## Validation and tests

Dataset validation:

```bash
python3 scripts/validate_quiz_data.py
```

Backend test:

```bash
PYTHONPATH=. pytest tests/test_quizlog_server.py
```

## Notes

- The remote sync is outbox-based: events are stored locally first, then uploaded.
- If the remote endpoint is unavailable, events remain in the local outbox and can be synced later.
- Local export produces a JSONL file from the iOS app's local event store.
