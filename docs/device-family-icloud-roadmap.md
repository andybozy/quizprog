# Device-Family iCloud Sync Roadmap

## Goal

Support two separate iCloud-backed app-data families:

- `ios`
- `macos`

and allow each app to:

- read only iOS records
- read only macOS records
- read a mixed/merged view of both

while always writing new answers and backups to:

- the local store of the current device
- the iCloud dataset family of the current device

This means:

- iPhone always writes to the `ios` family
- Mac always writes to the `macos` family
- read mode can vary independently from write target

## Core proposal

Introduce a strict distinction between:

1. `write family`
2. `read mode`
3. `effective working state`

### 1. Write family

Derived from platform:

- iPhone/iPad -> `ios`
- macOS / Mac Catalyst -> `macos`

This never changes at runtime.

### 2. Read mode

User-selectable:

- `iosOnly`
- `macosOnly`
- `mixed`

Optional convenience mode:

- `currentDevice`

which resolves to:

- `iosOnly` on iPhone
- `macosOnly` on Mac

### 3. Effective working state

The app should not use the raw selected dataset directly.

Instead:

- load base state from selected read mode
- overlay current device local state on top

This is necessary because otherwise:

- Mac could read `iosOnly`
- user answers a question on Mac
- answer would be written to `macos`
- but the UI would still look like nothing changed

So the effective state should be:

`effective_state = merge(selected_base_state, current_device_state_overlay)`

This preserves the rule:

- writes go only to the current device family

while still making answers visible immediately in the app that produced them.

## Data model

## New enums

### `QuizDatasetFamily`

```swift
enum QuizDatasetFamily: String, Codable, CaseIterable {
    case ios
    case macos
}
```

### `QuizDatasetReadMode`

```swift
enum QuizDatasetReadMode: String, Codable, CaseIterable {
    case iosOnly
    case macosOnly
    case mixed
}
```

### `QuizPlatform`

```swift
enum QuizPlatform: String, Codable {
    case ios
    case macos
}
```

## Shared progress entities

These need a dataset-family dimension:

- `QuizQuestionPerformance`
- `QuizCourseStats`
- `QuizBestScoreEntry`
- optional resumable snapshot

Each record should carry:

- `dataset_family`
- `updated_at`
- current entity payload

## Device log entities

Each event already has:

- `device_id`
- `platform`

Add:

- `dataset_family`

for explicit alignment with the write target.

## CloudKit schema proposal

Use the private database.

Keep the same record types, but namespace the records by family.

### Record types

- `QuizQuestionPerformance`
- `QuizCourseStats`
- `QuizBestScore`
- `QuizDeviceLogEvent`

### Required fields

For shared-state types:

- `datasetFamily` (`ios` / `macos`)
- `updatedAt`

For logs:

- `datasetFamily`
- `deviceID`
- `platform`
- `occurredAt`

### Record IDs

Use family-prefixed record names.

Examples:

- `question-performance|ios|<questionID>`
- `question-performance|macos|<questionID>`
- `course-stats|ios|<courseID>`
- `course-stats|macos|<courseID>`
- `best-score|ios|<courseID>`
- `best-score|macos|<courseID>`
- `device-log|ios|<deviceID>|<eventID>`
- `device-log|macos|<deviceID>|<eventID>`

This gives:

- natural physical separation
- easy filtering
- no cross-family overwrites

## Local persistence proposal

## Current-device local store remains authoritative for writes

Keep:

- `UserDefaults` for current-device progress/stats/settings (short term)
- local SQLite for event log

But reinterpret the local store as:

- current device family store only

So:

- iPhone local performance == local `ios` family state
- Mac local performance == local `macos` family state

## Remote read cache

Add a lightweight local cache for the non-local family snapshots fetched from CloudKit.

Recommended:

- a small JSON or SQLite cache in `Application Support`

Example:

- `cloud_cache_ios.json`
- `cloud_cache_macos.json`

This cache is read-only from the perspective of user answers.

It exists to:

- build `iosOnly`
- build `macosOnly`
- build `mixed`

without replacing the current-device write store.

## Merge rules

## 1. Question performance

For `mixed` mode:

- choose the newer record by `updatedAt`
- if equal, prefer current device family

Why:

- question scheduling needs one effective state per question
- latest state is the simplest deterministic rule

## 2. Course stats

For `mixed` mode:

- sum:
  - `plays`
  - `answered`
  - `correct`
- `updatedAt` = max timestamp

Why:

- course stats are aggregations
- additive merge is more meaningful than last-write-wins here

## 3. Best score

For `mixed` mode:

- `score = max(ios.score, macos.score)`
- `updatedAt = max(timestamp)`

## 4. Resumable quiz snapshot

Recommendation:

- keep resumable snapshot device-family scoped only
- do not merge resumable state across families in V1

Reason:

- mixed resumable state is ambiguous
- cross-device active session handoff is a separate feature

## Read-mode behavior

## `iosOnly`

- base state = CloudKit/cache `ios`
- overlay = current device local family

Example on Mac:

- base = iOS family
- overlay = local macOS writes

This means the app can inspect iOS progress while still making new answers immediately visible and stored into macOS family.

## `macosOnly`

- base state = CloudKit/cache `macos`
- overlay = current device local family

Example on iPhone:

- base = macOS family
- overlay = local iOS writes

## `mixed`

- base state = merge(iOS family, macOS family)
- overlay = current device local family

This keeps the current device writes authoritative in the live session.

## Write path

Every answer/skip should do this:

1. update local current-device progress
2. update local current-device stats
3. append local device log
4. enqueue CloudKit sync for current-device family only
5. optionally enqueue HTTP backend sync as today

No answer should ever directly write into the “other” family.

## Required UI changes

## New settings/state

Add:

- `current write family` label
- `current read mode` selector

UI should show both at the same time.

Example:

- `Reading: iOS records`
- `Writing: macOS records`

## Views to update

- iOS `iCloud Sync` sheet
- macOS `iCloud Sync` panel
- optionally home screen status card

## Warnings in UI

If read mode != write family:

- show a clear banner:
  - "You are reading iOS data, but new answers are saved to macOS data."

This is essential to avoid user confusion.

## Required refactor in codebase

## New types/files

Recommended files:

- `QuizDatasetFamily.swift`
- `QuizDatasetSelection.swift`
- `QuizCloudReadCache.swift`
- `QuizEffectiveStateBuilder.swift`

## Existing files to change

- `QuizSession.swift`
  - stop assuming one global shared progress set
  - expose snapshots for current-device family
  - apply effective merged state into the active session

- `QuizCloudSyncController.swift`
  - namespace records by family
  - fetch family-specific state
  - build mixed view input

- `QuizLogController.swift`
  - store `datasetFamily` on events
  - keep local-first behavior

- `ContentView.swift`
  - add read-mode picker
  - show read/write distinction

## Migration from current branch state

Current branch assumes one shared state family.

To migrate:

1. Add `QuizDatasetFamily`
2. Make current platform choose its write family automatically
3. Namespace all new CloudKit records by family
4. Treat old unscoped shared records as legacy

Recommended migration strategy:

- development reset / schema reset
- rebuild CloudKit development data with the new family-aware schema

Because this is still under development, this is much safer than trying to auto-migrate every old record format.

## Rollout plan

### Phase A

- add dataset family enums and read-mode model
- add family field to log events
- add write-family derivation from platform

### Phase B

- refactor CloudKit record IDs to family-scoped IDs
- fetch/save shared-state by family
- keep current device writing only to its own family

### Phase C

- add read cache for iOS and macOS family remote state
- build `iosOnly`, `macosOnly`, `mixed` effective state

### Phase D

- expose read mode in UI
- expose write target in UI
- add user warning when read mode differs from write family

### Phase E

- real-device validation:
  - iPhone reads iOS only and writes iOS
  - Mac reads macOS only and writes macOS
  - Mac reads iOS but writes macOS
  - iPhone reads macOS but writes iOS
  - both use mixed mode

## Success criteria

The feature is done when:

- iPhone and Mac each keep their own iCloud dataset family
- either app can read:
  - iOS
  - macOS
  - mixed
- new answers always write only to the current device family
- mixed mode is deterministic
- UI makes read/write behavior explicit
- local logging and remote backend still work

## Important non-goals

- do not create a third persistent `mixed` dataset
- do not write into the other platform family
- do not replace the local log with direct CloudKit-only logging
