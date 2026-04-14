# CloudKit Cross-Device Sync Roadmap

## Goal

Implement cross-device sync for QuizProg when iOS and macOS use the same iCloud account, while still keeping device-specific data separated when needed.

The target behavior is:

- shared quiz progress across iPhone and Mac
- separated device logs, preferences, and transient sync state
- a single Apple-native sync path inside the apps
- optional coexistence with the existing remote log backend

## Guiding model

Use three data classes:

1. Shared synced data
   - same user, same iCloud account, same state on all devices
   - examples:
     - spaced repetition progress
     - question performance
     - best scores
     - resumable progress if you want handoff-like continuity

2. Device-scoped synced data
   - synced to iCloud, but logically separated per device
   - examples:
     - device event logs
     - device diagnostics
     - per-device session history

3. Local-only data
   - never synced
   - examples:
     - temporary outbox state
     - last sync attempt metadata
     - UI/window preferences
     - local export cache

## Recommended architecture

Use CloudKit private database with explicit partitioning:

- one shared zone or record family for shared quiz state
- one device-scoped zone or record family for per-device logs
- one local SQLite layer for cache/outbox/runtime-only state

Recommended identifiers:

- `user_id`: implicit CloudKit account owner
- `device_id`: existing device UUID in app
- `platform`: `ios` or `macos`

## Phase 1: Define the sync contract

### Objective

Decide exactly what belongs to shared state vs device state.

### Shared entities

- `QuestionPerformance`
  - `question_id`
  - `history_summary`
  - `ease`
  - `interval`
  - `repetition`
  - `next_review`
  - `updated_at`

- `CourseStats`
  - `course_key`
  - `plays`
  - `answered`
  - `correct`
  - `updated_at`

- optional `ActiveQuizSnapshot`
  - only if you want resume continuity between devices

### Device-scoped entities

- `QuizLogEvent`
  - current event model already exists
  - include `device_id`
  - include `platform`

- `DeviceConfig`
  - optional
  - only if you want per-device synced config

### Local-only entities

- sync queue state
- in-flight upload markers
- export temp files
- dashboard/browser cache

### Deliverable

A short schema contract file in the repo, ideally before coding.

## Phase 2: Extract storage interfaces

### Objective

Stop binding business logic directly to `UserDefaults`.

### Tasks

1. Introduce protocols:
   - `QuizProgressStore`
   - `QuizStatsStore`
   - `QuizLogStore`

2. Keep current implementations temporarily:
   - `UserDefaultsQuizProgressStore`
   - existing SQLite log store

3. Inject stores into `QuizSession` instead of hardcoding persistence keys.

### Why

Without this layer, adding CloudKit will tangle app logic and transport logic together.

### Deliverable

`QuizSession` depends on abstractions, not persistence details.

## Phase 3: Introduce CloudKit service layer

### Objective

Add a dedicated CloudKit adapter instead of mixing CK APIs inside views or session logic.

### Tasks

1. Create a shared service file, for example:
   - `QuizCloudSyncController.swift`

2. Responsibilities:
   - fetch shared records
   - save shared records
   - save per-device records
   - reconcile local and cloud state
   - expose sync status to UI

3. Use:
   - `CKContainer.default()`
   - private database
   - custom zones where useful

### Suggested partitioning

- zone: `QuizSharedState`
  - question performance
  - course stats

- zone: `QuizDeviceLogs-<deviceID>`
  - log events for one device

### Deliverable

A CloudKit service layer with no UI code inside it.

## Phase 4: Shared progress sync

### Objective

Make spaced repetition and quiz progress shared between Mac and iPhone.

### Tasks

1. Map current local performance model to CloudKit record model.
2. Sync on:
   - app launch
   - app foreground
   - after answer/skip
   - after finishing quiz
3. Decide conflict policy.

### Recommended conflict policy

Use `last-write-wins` by `updated_at` for the first version.

For `QuestionPerformance`:
- if cloud is newer, pull cloud
- if local is newer, push local

### Important note

If two devices answer the same question offline, you need deterministic merge rules.

For V1:
- compare timestamps
- keep latest record

For V2:
- merge event history more intelligently

### Deliverable

Question scheduling state matches across devices.

## Phase 5: Device-separated event logs in iCloud

### Objective

Keep logs synchronized to the same iCloud account without mixing Mac and iPhone histories.

### Tasks

1. Add `device_id` and `platform` to every log event if not already present.
2. Store logs either:
   - in separate zones per device
   - or in one record type filtered by `device_id`

### Recommendation

Prefer one record type plus `device_id` filter unless zone count becomes operationally annoying.

Suggested record type:

- `QuizLogEvent`

Record fields:
- `event_id`
- `occurred_at`
- `session_id`
- `device_id`
- `platform`
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
- `metadata_json`

### Behavior

- Mac logs sync to iCloud
- iPhone logs sync to iCloud
- both are queryable separately by `device_id` or `platform`

### Deliverable

Cloud-backed logs that stay separated by device.

## Phase 6: Keep local SQLite log as source-of-capture

### Objective

Do not send events directly to CloudKit from UI events.

### Tasks

1. Continue writing every event immediately to local SQLite.
2. Add a CloudKit sync worker that reads unsynced events from local store.
3. Mark events as synced locally after successful cloud save.

### Why

This preserves:
- offline safety
- retry behavior
- export capability
- future backend fan-out

### Deliverable

CloudKit becomes a sync target, not the only event store.

## Phase 7: Support both CloudKit and the existing remote backend

### Objective

Avoid throwing away the remote backend you already added.

### Strategy

Use dual sync targets:

- Target A: CloudKit
- Target B: HTTP backend

### Suggested split

- shared progress:
  - CloudKit primary
- full analytics/audit:
  - remote backend primary
- device-scoped logs:
  - optionally both CloudKit and backend

### Practical recommendation

V1:
- sync progress to CloudKit
- keep event log syncing to backend

V2:
- optionally mirror event logs to CloudKit too

### Deliverable

No regression in current remote logging path while adding Apple-native sync.

## Phase 8: Add app UI for sync status on both iOS and macOS

### Objective

Expose sync behavior clearly in both apps.

### Tasks

1. Add a `Sync` / `iCloud` management panel.
2. Show:
   - iCloud availability
   - current Apple account state
   - last sync time
   - pending local changes
   - per-device identity
3. Add actions:
   - sync now
   - export local log
   - open remote dashboard
   - reset local cache only

### Platform notes

iOS:
- sheet/settings panel

macOS:
- settings window or sidebar panel

### Deliverable

Users can understand whether data is shared or device-specific.

## Phase 9: Handle account and device edge cases

### Objective

Prevent silent corruption when iCloud state changes.

### Cases to handle

1. User not signed into iCloud
2. iCloud temporarily unavailable
3. account changes while app is installed
4. one device offline for a long time
5. duplicate local events already uploaded

### Required protections

- stable `event_id` dedup
- stable `device_id`
- explicit sync status errors in UI
- safe fallback to local-only mode

### Deliverable

Predictable behavior when iCloud isn’t healthy.

## Phase 10: Testing strategy

### Objective

Verify sync correctness across both app platforms.

### Tests

1. Unit tests
   - record mapping
   - merge policy
   - dedup logic
   - store abstraction behavior

2. Integration tests
   - iPhone answer updates Mac after sync
   - Mac answer updates iPhone after sync
   - logs remain separable by `device_id`

3. Manual matrix
   - same account, both online
   - one offline then reconnect
   - conflicting edits
   - account signed out

### Deliverable

Cross-device sync is reproducible and testable.

## Phase 11: Implementation order

### Recommended order

1. Extract persistence interfaces from `QuizSession`
2. Implement shared state CloudKit adapter
3. Sync `QuestionPerformance`
4. Sync `CourseStats`
5. Expose sync status in UI
6. Add CloudKit log mirroring for device-scoped logs
7. Add conflict handling and retry polish
8. Expand tests

## MVP definition

The smallest good version is:

- iPhone and Mac on same iCloud account
- question performance shared both ways
- best scores/course stats shared both ways
- local event log still works
- remote backend still works
- each device keeps its own log identity

## Final target state

At the end, the app should have:

- shared quiz learning state across iOS and macOS
- device-separated logs
- local-first persistence
- CloudKit sync for Apple-native continuity
- optional remote backend for analytics and external access

## Concrete file map for this repo

### Existing files that should be extended

- `QuizProgApp/QuizProg/QuizProg/QuizSession.swift`
  - remove direct persistence coupling
  - depend on shared store abstractions

- `QuizProgApp/QuizProg/QuizProg/QuizLogController.swift`
  - keep local SQLite as source-of-capture
  - add optional CloudKit mirroring path

- `QuizProgApp/QuizProg/QuizProg/ContentView.swift`
  - add iCloud sync status/config UI

- `server/quizlog_server.py`
  - stays as external analytics/audit backend
  - not replaced by CloudKit

### Suggested new shared app files

- `QuizProgApp/QuizProg/QuizProg/QuizCloudSyncController.swift`
- `QuizProgApp/QuizProg/QuizProg/QuizProgressStore.swift`
- `QuizProgApp/QuizProg/QuizProg/CloudKitQuizProgressStore.swift`
- `QuizProgApp/QuizProg/QuizProg/LocalQuizProgressStore.swift`
- `QuizProgApp/QuizProg/QuizProg/QuizCloudModels.swift`

### Suggested macOS-specific follow-up files

- if staying on Mac Catalyst:
  - reuse the same target and add macOS-conditional UI

- if later splitting into a native macOS target:
  - `QuizProgMacApp.swift`
  - `MacSettingsView.swift`
  - `MacSyncStatusView.swift`

## First implementation patch set

The first real implementation batch should do exactly this:

1. Introduce persistence protocols and stop hardcoding `UserDefaults` inside `QuizSession`
2. Add `QuizCloudSyncController`
3. Sync `QuestionPerformance` records to CloudKit private database
4. Sync `CourseStats` records to CloudKit private database
5. Keep `QuizLogController` local-first and continue syncing to HTTP backend
6. Add optional CloudKit mirroring for logs only after shared progress is stable
7. Add a visible `iCloud Sync` status panel to the app UI on both iOS and macOS

## What not to do

- Do not replace the local SQLite event log with direct CloudKit writes
- Do not mix per-device logs into the shared progress record set
- Do not bind CloudKit calls directly inside SwiftUI views
- Do not remove the remote backend before CloudKit shared progress is stable
