# iOS Quiz Data Workflow

## Source of truth

All quiz data lives in the repository root:

- `quiz_data/`

Do not maintain a second copy under `QuizProgApp/QuizProg/QuizProg/`.

## How iOS bundles quiz data

The Xcode target `QuizProg` runs a build phase named `Bundle Quiz Data`.

That phase executes:

- `scripts/bundle_ios_quiz_data.sh`

It copies `quiz_data/` into the built app bundle as:

- `QuizProg.app/quiz_data/...`

Excluded from the bundle:

- `.DS_Store`
- `.quiz_index.json`

Included in the bundle:

- quiz JSON files
- `exam_dates.json`
- `display_overrides.json`

## Runtime expectations

The Swift loader expects quiz data at:

- `Bundle.main.resourceURL/quiz_data`

If that folder is missing or empty, the app shows an explicit warning on the start screen.

## Before building

Validate the dataset:

```bash
python3 scripts/validate_quiz_data.py
```

Warnings mean some questions will be skipped by the loader.

## Verify the built app bundle

After building:

```bash
find ~/Library/Developer/Xcode/DerivedData/QuizProg-*/Build/Products/Debug-iphonesimulator/QuizProg.app/quiz_data -maxdepth 2 -type f | sort
```

Expected:

- `quiz_data/<course>/<file>.json`
- `quiz_data/exam_dates.json`
- `quiz_data/display_overrides.json`

Not expected:

- top-level quiz JSON files directly under `QuizProg.app/`

## Display names

File display names shown by the iOS app are defined in:

- `quiz_data/display_overrides.json`

Course names are taken from the raw folder names.
