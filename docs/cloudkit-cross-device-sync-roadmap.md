# CloudKit Cross-Device Sync Roadmap

## Goal

Implement cross-device sync for QuizProg when iOS and macOS use the same iCloud account, while still keeping device-specific data separated when needed.

The target behavior is:

- shared quiz progress across iPhone and Mac
- separated device logs, preferences, and transient sync state
- a single Apple-native sync path inside the apps
- optional coexistence with the existing remote log backend

## Current status

### Already implemented on this branch

- shared CloudKit sync controller exists
- shared state model exists for:
  - question performance
  - course stats
  - best scores
- iOS and macOS app UI expose an `iCloud Sync` panel
- local SQLite event log remains source-of-capture
- optional CloudKit mirroring path exists for device-scoped logs
- HTTP remote backend still exists and still works
- iOS simulator build passes
- Mac Catalyst Release build passes

### Important limitation right now

The code path is implemented, but the project is not yet fully “done” from a product/runtime perspective.

The remaining work is mostly:

- Apple capability wiring and signing validation on the real developer environment
- actor-isolation cleanup in `QuizLogController.swift`
- real-world iCloud account testing across iPhone and Mac
- conflict and offline recovery testing

## Is the project already complete?

No, not completely.

The current branch is at a strong **developer-complete MVP** stage, but not yet at **production-complete** stage.

### Developer-complete means

- architecture exists
- code compiles
- sync UI exists
- local and remote persistence paths coexist
- CloudKit integration points are implemented

### Production-complete means

- iCloud capability is fully enabled and verified in the actual signed app configuration
- the app is tested with the same real iCloud account on both iOS and macOS
- conflict/offline behavior is validated
- no unresolved actor-isolation warnings remain in the logging layer
- sync behavior is documented and repeatable for release

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

## Final phases still required to reach the end

These are the final phases needed to actually close the project.

### Phase 12: Apple capability wiring

#### Objective

Turn the current CloudKit code path into a real working Apple-signed runtime feature.

#### Tasks

1. Enable the iCloud capability in Xcode for the app target
2. Enable CloudKit service for the app target
3. Ensure the correct container exists in the Apple developer account
4. Verify signing/provisioning for:
   - iOS run/install
   - macOS Catalyst run/install
5. Confirm the container name and bundle identifiers match the signed app

#### Deliverable

A signed app that can actually talk to CloudKit at runtime on both iPhone and Mac.

### Phase 13: Real-device validation

#### Objective

Verify the sync path using the same iCloud account on actual devices.

#### Manual matrix

1. iPhone answers a question, then Mac syncs and sees the new performance state
2. Mac answers a question, then iPhone syncs and sees the new performance state
3. Shared best score changes propagate both ways
4. Course stats propagate both ways
5. Device log records remain distinguishable by `device_id` and `platform`
6. One device offline, then reconnect
7. Both devices edit the same question state at different times
8. User signed out of iCloud, then signed back in

#### Deliverable

Confirmed correct sync behavior on real hardware and real iCloud account state.

### Phase 14: Conflict and recovery hardening

#### Objective

Move from simple timestamp merge to reliable long-lived sync behavior.

#### Tasks

1. Audit every merge decision in `QuizCloudSyncController`
2. Verify no stale local state overwrites newer cloud state
3. Ensure local writes are never lost if CloudKit is unavailable
4. Add user-visible error state for CloudKit failures
5. Optionally add throttling/debounce for repeated sync triggers

#### Deliverable

Predictable sync under offline, delayed, and conflicting updates.

### Phase 15: Concurrency cleanup

#### Objective

Remove the remaining actor-isolation warnings and leave the codebase in a future-safe state.

#### Tasks

1. Refactor `QuizLogController.swift` so the SQLite actor internals do not rely on main-actor isolated constants or synthesized Codable behavior in actor context
2. Separate actor-internal DTO encoding/decoding cleanly if needed
3. Rebuild both iOS and macOS targets with zero new warnings from the logging layer

#### Deliverable

A clean build with the logging and sync stack aligned with the project’s concurrency settings.

### Phase 16: Release-readiness and docs

#### Objective

Make the feature maintainable after handoff.

#### Tasks

1. Update docs with:
   - how to enable CloudKit in Xcode
   - how to verify same-account cross-device sync
   - what is shared vs device-scoped
2. Add a short troubleshooting section for:
   - no iCloud account
   - account mismatch
   - capability misconfiguration
   - stale local cache
3. Add a small smoke-test checklist for every release

#### Deliverable

A feature that another developer can run, validate, and maintain.

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
- verified real-device behavior on the same iCloud account
- working Apple capability/signing setup
- clean concurrency/build state in the logging stack

## Integrated end-to-end plan

This is the consolidated route from the current branch state to actual completion.

### Stage A: Foundation

Status:
- `done`

Scope:
- CloudKit shared sync controller exists
- app UI exposes iCloud sync state/actions
- local SQLite event log remains source-of-capture
- HTTP backend still works
- iOS build passes
- Mac Catalyst build passes

Exit criteria:
- branch builds on both iOS and macOS
- no regression in quiz flow
- remote backend path still functional

### Stage B: Shared state sync correctness

Status:
- `in_progress`

Remaining work:
1. Validate that `QuestionPerformance`, `CourseStats`, and `BestScores` serialize and deserialize exactly as intended
2. Verify merge behavior on repeated sync cycles
3. Verify `last-write-wins` timestamps are consistently set everywhere
4. Add or extend tests for merge correctness

Exit criteria:
- repeated sync cycles are idempotent
- no shared-state drift between local and cloud representations
- merge logic is covered by tests

### Stage C: Device-scoped CloudKit log mirroring

Status:
- `in_progress`

Remaining work:
1. Verify CloudKit-mirrored device log records are queryable and remain separable by:
   - `device_id`
   - `platform`
2. Ensure Cloud log mirror never blocks local event capture
3. Ensure Cloud mirror failures do not affect HTTP backend sync

Exit criteria:
- device log mirroring is additive only
- local log remains authoritative
- iPhone and Mac logs remain separable even on same iCloud account

### Stage D: Apple runtime enablement

Status:
- `todo`

Remaining work:
1. Enable iCloud capability in the actual Xcode signing environment
2. Enable CloudKit service for the target
3. Ensure the proper iCloud container exists
4. Verify that the signed app can read/write CloudKit on:
   - iPhone
   - Mac Catalyst app

Important note:
- this cannot be considered fully done from code alone
- it requires actual Apple account / provisioning state verification

Exit criteria:
- both apps run signed with CloudKit enabled
- no runtime entitlement/container errors

### Stage E: Real-device cross-device validation

Status:
- `todo`

Remaining work:
1. iPhone answer -> Mac sees updated question performance after sync
2. Mac answer -> iPhone sees updated question performance after sync
3. Best scores sync both ways
4. Course stats sync both ways
5. Device logs remain separated both ways
6. Manual sync and auto sync both behave correctly

Exit criteria:
- real same-account iPhone/Mac behavior confirmed end to end

### Stage F: Offline/conflict hardening

Status:
- `todo`

Remaining work:
1. Test one device offline for a long time
2. Test conflicting edits on same question from both devices
3. Verify no stale local state overwrites newer cloud state
4. Verify recovery after temporary iCloud errors

Exit criteria:
- conflict and recovery behavior is predictable
- no silent data loss

### Stage G: Concurrency cleanup

Status:
- `todo`

Remaining work:
1. Remove remaining actor-isolation warnings from `QuizLogController.swift`
2. Refactor SQLite actor boundaries if needed
3. Make builds clean enough for long-term maintenance

Exit criteria:
- logging/sync layer builds without unresolved concurrency warnings

### Stage H: Release closure

Status:
- `todo`

Remaining work:
1. Final docs for:
   - capability enablement
   - iCloud troubleshooting
   - same-account test procedure
2. Smoke-test checklist for every release
3. Confirm macOS install flow still works after CloudKit enablement

Exit criteria:
- another developer can enable, test, and ship the feature

## Final execution order from now

This is the actual remaining order to reach the end:

1. Finish shared-state correctness checks and tests
2. Finish device-log mirroring verification
3. Enable iCloud capability and CloudKit in the real signed Xcode environment
4. Validate same-account iPhone/Mac sync on real devices
5. Validate offline/conflict behavior
6. Remove remaining concurrency warnings in `QuizLogController.swift`
7. Finalize docs and smoke tests

## Definition of done

The CloudKit part of the project is only truly done when all of the following are true:

- iOS app builds and runs
- macOS app builds and runs
- signed app configuration has working iCloud/CloudKit capability
- same-account iPhone/Mac sync is verified on real devices
- shared progress actually converges across devices
- device-scoped logs remain separated
- local logging and remote backend still work
- no unresolved concurrency warnings remain in the logging/sync layer
- docs are sufficient for maintenance and release

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

## Short answer

The three steps below are necessary, but they are not by themselves enough to say the whole project is finished:

1. add iCloud capability wiring in Xcode/project
2. verify on the signed local Apple environment
3. clean remaining `QuizLogController` actor-isolation warnings

To truly reach the end, you also need:

4. real-device cross-sync validation
5. conflict/offline recovery verification
6. release-ready documentation and troubleshooting guidance
