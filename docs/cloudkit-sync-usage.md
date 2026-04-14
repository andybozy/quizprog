# CloudKit Sync Usage

QuizProg now contains an Apple-native sync layer designed for the case where the iPhone and Mac use the same iCloud account.

## Shared across devices

These records are intended to converge across iOS and macOS:

- question performance
  - history
  - ease
  - interval
  - repetition
  - next review
- course stats
  - plays
  - answered
  - correct
- best scores

## Kept separate by device

These remain device-scoped even if mirrored to the same iCloud account:

- full event log records
- device identity
- UI/runtime preferences
- local export files
- in-flight local queue state

Device log events are tagged with:

- `device_id`
- `platform`

## In-app controls

Open the app home screen and use the `iCloud Sync` card.

You can:

- check iCloud account status
- see pending shared changes
- see pending device log mirroring
- enable or disable:
  - auto sync
  - shared progress sync
  - CloudKit log mirroring
- trigger manual sync

## Expected behavior

If iPhone and macOS use the same iCloud account:

- answering on iPhone updates spaced-repetition state
- a later sync on Mac pulls the newer performance record
- logs remain identifiable by originating device

## Current coexistence with remote backend

The app still keeps the existing HTTP remote log backend.

Recommended usage:

- CloudKit:
  - shared quiz state
  - optional log mirroring
- HTTP backend:
  - external dashboard
  - audit trail
  - analytics outside Apple ecosystem

## Important note

The code path is in place, but actual CloudKit runtime availability still depends on the app being signed with the appropriate iCloud capability in the Apple developer configuration used to run the app.
