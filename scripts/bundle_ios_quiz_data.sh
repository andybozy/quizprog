#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <repo-root> <project-dir> <bundle-resources-dir>" >&2
  exit 1
fi

repo_root="$1"
project_dir="$2"
resources_dir="$3"

source_dir="$repo_root/quiz_data"
target_dir="$resources_dir/quiz_data"

if [[ ! -d "$source_dir" ]]; then
  echo "Missing source quiz_data directory: $source_dir" >&2
  exit 1
fi

mkdir -p "$resources_dir"
rm -rf "$target_dir"
mkdir -p "$target_dir"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/quizprog-quiz-data.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT

ditto "$source_dir" "$tmp_dir/quiz_data"
find "$tmp_dir/quiz_data" -name '.DS_Store' -delete
find "$tmp_dir/quiz_data" -name '.quiz_index.json' -delete

ditto "$tmp_dir/quiz_data" "$target_dir"

echo "Bundled quiz data from $source_dir into $target_dir"
