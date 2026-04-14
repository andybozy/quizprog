# QuizProg on macOS

QuizProg can now be built as a Mac Catalyst app from the existing `QuizProg` target.

This gives you:

- a single shared Swift codebase
- the same bundled quiz data on iPhone and macOS
- the same local/remote event logging stack
- a real `.app` bundle you can run on this Mac

## Build the macOS app

From the repo root:

```bash
chmod +x scripts/build_macos_app.sh scripts/package_macos_app.sh
./scripts/build_macos_app.sh
```

The built app is copied to:

```text
dist/macos/QuizProg.app
```

You can open it directly:

```bash
open dist/macos/QuizProg.app
```

## Create a distributable archive

```bash
./scripts/package_macos_app.sh
```

This produces:

```text
dist/macos/QuizProg-macOS.zip
```

## Install on this Mac

After `build_macos_app.sh`:

1. Open `dist/macos/`
2. Drag `QuizProg.app` into `/Applications`
3. Launch it from Applications

Or via terminal:

```bash
cp -R dist/macos/QuizProg.app /Applications/
open /Applications/QuizProg.app
```

## Notes

- This is a Mac Catalyst build, not yet a separate native macOS target.
- It is suitable for local installation on this Mac.
- If you want frictionless distribution to other Macs, the next step is signing + notarization.

## Verify the build

```bash
xcodebuild -project QuizProgApp/QuizProg/QuizProg.xcodeproj -scheme QuizProg -destination 'platform=macOS,variant=Mac Catalyst' build
```
