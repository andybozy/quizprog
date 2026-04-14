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

rsync -a --delete --delete-excluded \
  --exclude '.DS_Store' \
  --exclude '.quiz_index.json' \
  "$source_dir"/ "$target_dir"/

echo "Bundled quiz data from $source_dir into $target_dir"
