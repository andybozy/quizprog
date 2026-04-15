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

## Reading vs writing

The app now distinguishes between:

- `Reading`
- `Writing`

### Writing

The write target is fixed by device family:

- iPhone/iPad writes to `iOS`
- Mac writes to `macOS`

### Reading

The app can read in three modes:

- `Record iOS`
- `Record macOS`
- `Mixed`

### Important behavior

If you are reading a different family from the current device:

- the app still writes new answers only to the current device family

Examples:

- Mac reading `Record iOS`
  - reads iOS data
  - writes new answers to macOS data

- iPhone reading `Record macOS`
  - reads macOS data
  - writes new answers to iOS data

- `Mixed`
  - reads a merged view
  - still writes only to the current device family

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

## Enable CloudKit in Xcode

On the target `QuizProg`:

1. Open `Signing & Capabilities`
2. Add capability:
   - `iCloud`
3. Inside iCloud, enable:
   - `CloudKit`
4. Ensure the target uses your real Apple team and working bundle identifier
5. Let Xcode create or attach the proper CloudKit container

If iPhone and Mac use the same iCloud account, the shared progress records should then converge across devices.

## Manual same-account smoke test

1. Launch the app on iPhone and Mac
2. Open the `iCloud Sync` panel on both
3. Verify account state becomes `Available`
4. On iPhone:
   - answer one question
   - press `Sync iCloud adesso`
5. On Mac:
   - press `Sync iCloud adesso`
   - confirm the same question performance has changed
6. Repeat in the opposite direction:
   - answer on Mac
   - sync on iPhone
7. Confirm:
   - best score updates
   - course stats update
   - device logs remain separate

## Troubleshooting

### Account state is not `Available`

Check:

- device is signed into iCloud
- iCloud Drive / CloudKit is available
- capability is enabled in the app target

### Sync button runs but nothing changes

Check:

- same iCloud account on both devices
- the target is signed with the iCloud capability enabled
- the CloudKit container belongs to the same app identifier/team

### Logs should stay separate

This is expected:

- shared learning state is common
- event logs are still device-scoped

The separation happens through:

- `device_id`
- `platform`
