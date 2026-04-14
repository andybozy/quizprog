# QuizProg macOS Installable Roadmap

## Goal

Make QuizProg installable and usable on macOS, with a maintainable architecture that avoids duplicating quiz logic across iOS and macOS.

This roadmap assumes the current codebase is iOS-first and already contains:

- shared quiz/session logic in Swift files
- bundled quiz data from `quiz_data/`
- local event logging + remote sync

## Recommendation

Use a **shared core + separate macOS app target** approach.

Short-term, Mac Catalyst can produce a fast proof of concept.
Long-term, a native macOS SwiftUI target is the cleaner solution.

Recommended final architecture:

- shared core module for data loading, quiz engine, logging, sync
- iOS target for phone/tablet UX
- macOS target for desktop UX

## Phase 1: Stabilize shared code boundaries

### Objective

Move all platform-neutral code out of the iOS view layer so both apps can reuse it.

### Tasks

1. Extract shared logic from iOS-only files.
   - Keep `QuizSession`, quiz models, bundle loader, logging, and sync in shared files.
   - Remove any direct SwiftUI assumptions from the engine layer when possible.

2. Define shared folders or modules.
   - `Shared/QuizCore`
   - `Shared/QuizLogging`
   - `Shared/QuizData`

3. Keep UI-only logic separate.
   - iOS-specific views remain in the iOS target
   - future macOS views live in a separate macOS target

### Deliverable

A shared layer that compiles independently from the iOS-only UI.

## Phase 2: Create a macOS app target

### Objective

Add a real macOS app target to the Xcode project.

### Tasks

1. Add a new target:
   - `QuizProgMac`
   - platform: macOS
   - app lifecycle: SwiftUI

2. Reuse the shared source files in the new target.
   - `QuizSession.swift`
   - `QuizLogController.swift`
   - shared models/loaders

3. Add a separate entrypoint:
   - `QuizProgMacApp.swift`

4. Add a separate top-level macOS view:
   - can initially reuse the current SwiftUI structure
   - later optimize for sidebar/table split navigation

### Deliverable

A macOS app target that builds and launches locally on the Mac.

## Phase 3: Make quiz data bundling platform-neutral

### Objective

Bundle `quiz_data/` correctly into both iOS and macOS apps.

### Tasks

1. Reuse the same root source of truth:
   - `quiz_data/`

2. Add a macOS build phase equivalent to the current iOS one.
   - copy `quiz_data/` into:
     - `QuizProg.app/Contents/Resources/quiz_data`

3. Make the loader work for both bundle layouts.
   - iOS:
     - `Bundle.main.resourceURL/quiz_data`
   - macOS:
     - `Bundle.main.resourceURL/quiz_data`
   - this should already be mostly compatible, but needs verification

4. Add post-build verification.
   - assert `quiz_data/` exists in both app bundles
   - assert no quiz JSON files are flattened into the bundle root

### Deliverable

Both targets consume the same bundled dataset without manual syncing.

## Phase 4: Add macOS-specific UI and interaction patterns

### Objective

Make the app feel correct on desktop instead of just “running”.

### Tasks

1. Replace mobile-first sheets where needed.
   - file picker and stats can become split views or panels

2. Improve keyboard navigation.
   - arrow/tab navigation for answers
   - return/space shortcuts
   - command shortcuts for sync/export/log actions

3. Improve layout for large screens.
   - sidebar for course/file navigation
   - persistent stats panel
   - wider review/results layout

4. Add menu bar commands.
   - Sync now
   - Export log
   - Open dashboard URL
   - Reload bundled data if useful

### Deliverable

A usable macOS UX, not just an iOS UI stretched onto desktop.

## Phase 5: Audit file system behavior on macOS

### Objective

Ensure local persistence works correctly on both platforms.

### Tasks

1. Verify SQLite storage paths.
   - event log DB in `Application Support`
   - ensure path is valid on macOS sandbox/non-sandbox runs

2. Verify export paths.
   - JSONL export should land in a user-visible location
   - on macOS, likely `Downloads` or exported through `NSSavePanel`

3. Verify any file sharing APIs.
   - `ShareLink` may need macOS review
   - add desktop-appropriate save/open behavior

4. Ensure local server URLs and dashboard links work.
   - opening browser via `NSWorkspace.shared.open`

### Deliverable

Reliable persistence and export behavior on desktop.

## Phase 6: Make the logging/sync stack fully cross-platform

### Objective

Ensure the new remote log system behaves the same on macOS.

### Tasks

1. Reuse `QuizLogController` in the macOS target.
2. Add the same event hooks in the shared session engine.
3. Add macOS UI for:
   - sync configuration
   - manual sync
   - JSONL export
   - dashboard opening
4. Verify ATS/network settings for macOS target too.
5. Verify background behavior differences.
   - iOS scene lifecycle and macOS app lifecycle differ
   - define sync triggers per platform

### Deliverable

Desktop and mobile both produce the same structured event stream.

## Phase 7: Distribution-ready macOS build

### Objective

Make the macOS app actually installable outside Xcode.

### Tasks

1. Decide distribution model.
   - direct signed `.app`
   - `.dmg`
   - Mac App Store

2. Configure signing.
   - Developer ID Application certificate for outside-App-Store distribution

3. Notarize the app.
   - required for frictionless installation on modern macOS

4. Produce distributable artifacts.
   - `.app` zipped for notarization
   - optional `.dmg`

5. Add release scripts or CI jobs.
   - archive
   - codesign
   - notarize
   - staple

### Deliverable

A signed, notarized macOS build that another user can install without Xcode.

## Phase 8: Testing strategy

### Objective

Prevent platform regressions.

### Tasks

1. Unit tests for shared logic.
   - loader
   - scheduling
   - logging
   - sync payloads

2. Backend tests.
   - ingest
   - summary
   - export

3. UI smoke tests.
   - iOS build
   - macOS build

4. Bundle validation tests.
   - dataset exists
   - display overrides resolve
   - exam dates parse

### Deliverable

Confidence that iOS and macOS stay aligned.

## Phase 9: CI and automation

### Objective

Make future releases repeatable.

### Tasks

1. Add CI jobs for:
   - Python tests
   - iOS simulator build
   - macOS app build

2. Add dataset validation to CI.

3. Add release scripts:
   - `scripts/build_macos_release.sh`
   - `scripts/notarize_macos_release.sh`

4. Optionally add GitHub Actions for packaged artifacts.

### Deliverable

One-command or one-workflow macOS release generation.

## Suggested implementation order

1. Extract shared core files.
2. Add macOS target.
3. Add macOS build phase for `quiz_data`.
4. Verify loader and log stack on macOS.
5. Add minimal macOS UI.
6. Add export/open-dashboard support.
7. Add signed release pipeline.
8. Add notarization and packaging.

## MVP definition

The minimum useful macOS deliverable is:

- macOS target builds and runs
- quiz data bundles correctly
- quiz session works
- local event log works
- remote sync works
- JSONL export works

This can happen before:

- polished desktop UX
- DMG packaging
- notarization

## Final target state

The final desired state is:

- one shared quiz engine
- one shared log/sync stack
- iOS app
- macOS app
- installable signed macOS release
- reproducible packaging pipeline
