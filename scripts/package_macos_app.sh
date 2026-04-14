#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
dist_dir="$repo_root/dist/macos"

"$repo_root/scripts/build_macos_app.sh"

app_path="$dist_dir/QuizProg.app"
zip_path="$dist_dir/QuizProg-macOS.zip"

if [[ ! -d "$app_path" ]]; then
  echo "Missing built app at $app_path" >&2
  exit 1
fi

rm -f "$zip_path"
ditto -c -k --keepParent "$app_path" "$zip_path"

echo "Packaged macOS app archive at:"
echo "$zip_path"
