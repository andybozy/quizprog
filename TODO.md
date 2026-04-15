# TODO

## CloudKit bootstrap issue

- Fix first-sync bootstrap failure when CloudKit returns missing record type errors such as:
  - `did not find record type: QuizQuestionPerformance`
- Required behavior:
  - treat missing record types as empty remote state
  - continue sync instead of aborting
  - let first successful save bootstrap the development schema
- Apply the same handling to:
  - `QuizQuestionPerformance`
  - `QuizCourseStats`
  - `QuizBestScore`
  - `QuizDeviceLogEvent`

## Separate iCloud app data by device family

Detailed implementation roadmap:

- `docs/device-family-icloud-roadmap.md`

### Target behavior

- Keep iOS app data backed up/synced in iCloud separately from macOS app data.
- Keep local device data separate too.
- Each app must be able to read:
  - only iOS record set
  - only macOS record set
  - mixed/merged view of both
- Each app must always write new answers and backups to:
  - the local store of that device
  - the remote record set of that device

### Required model

- Maintain at least two logical app-data sets in iCloud:
  - `ios`
  - `macos`
- Keep device identity explicit on every persisted answer/progress/log record:
  - `device_id`
  - `platform`
  - logical record-set key (`ios` or `macos`)

### Read modes

- Add selectable read mode in app:
  - `iOS records`
  - `macOS records`
  - `Mixed`
- Mixed mode is a computed merged view, not a third write target.

### Write rules

- iPhone always writes to the iOS record set.
- Mac always writes to the macOS record set.
- This stays true even if the app is currently viewing:
  - the other platform’s records
  - the mixed view

### Merge rules for mixed mode

- Define deterministic merge policy for:
  - question performance
  - course stats
  - best scores
  - resumable progress if included
- Start with timestamp-based merge.
- Later evaluate smarter merge for answer history if needed.

### UI / product requirements

- Expose current read mode clearly in both apps.
- Expose current write target clearly in both apps.
- Show whether the app is currently using:
  - iOS dataset
  - macOS dataset
  - mixed dataset
- Make it obvious that new answers are saved to the current device dataset only.

### Persistence / sync requirements

- Preserve local-first behavior.
- Preserve device-scoped local SQLite/event log behavior.
- Keep CloudKit sync and HTTP backend sync compatible.
- Do not let mixed-mode reads overwrite another device’s dataset directly.

### Validation

- Real-device tests required:
  - iPhone using iOS-only mode
  - Mac using macOS-only mode
  - both using mixed mode
  - Mac reading iOS set while still writing to macOS set
  - iPhone reading macOS set while still writing to iOS set
