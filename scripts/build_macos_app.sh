#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
project="$repo_root/QuizProgApp/QuizProg/QuizProg.xcodeproj"
scheme="QuizProg"
derived_data="$repo_root/.build/DerivedData-maccatalyst"
configuration="${CONFIGURATION:-Release}"
destination="platform=macOS,variant=Mac Catalyst"
output_dir="$repo_root/dist/macos"

rm -rf "$derived_data"
mkdir -p "$output_dir"

xcodebuild \
  -project "$project" \
  -scheme "$scheme" \
  -configuration "$configuration" \
  -destination "$destination" \
  -derivedDataPath "$derived_data" \
  build

app_path="$(find "$derived_data/Build/Products" -path '*-maccatalyst/QuizProg.app' -print -quit)"
if [[ -z "${app_path:-}" ]]; then
  echo "Could not locate built QuizProg.app in DerivedData." >&2
  exit 1
fi

rm -rf "$output_dir/QuizProg.app"
cp -R "$app_path" "$output_dir/QuizProg.app"

echo "Built macOS app at:"
echo "$output_dir/QuizProg.app"
