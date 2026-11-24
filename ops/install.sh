#!/usr/bin/env bash
set -euo pipefail

project="${1:-}"
force=0
if [[ "${2:-}" == "--force" ]]; then force=1; fi
if [[ -z "$project" ]]; then
  echo "usage: install.sh <projet> [--force]" >&2
  exit 2
fi

source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
brain_source="$source_dir/.opencode"
brain_target="$project/.opencode"
mkdir -p "$brain_target"

while IFS= read -r -d '' file; do
  relative="${file#"$brain_source"/}"
  destination="$brain_target/$relative"
  mkdir -p "$(dirname "$destination")"
  if [[ -e "$destination" && "$force" -eq 0 ]]; then
    echo "SKIP $relative"
    continue
  fi
  cp "$file" "$destination"
  echo "COPIED $relative"
done < <(find "$brain_source" -type f -print0)

rites_target="$project/RITES.md"
if [[ -e "$rites_target" && "$force" -eq 0 ]]; then
  echo "SKIP RITES.md"
else
  cp "$source_dir/MODELE_RITES.md" "$rites_target"
  echo "COPIED RITES.md"
fi
