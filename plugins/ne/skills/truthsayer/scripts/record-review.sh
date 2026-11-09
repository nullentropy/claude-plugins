#!/usr/bin/env bash
# record-review.sh NOTES   record NOTES as the review of HEAD
# NOTES must contain the line "verdict: clean". Run it from inside the
# repository, with every change committed: the record covers HEAD only.
set -euo pipefail
. "$(dirname "$0")/../../../lib/state.sh"

notes="${1:-}"
[ -f "$notes" ] || { echo "Usage: record-review.sh NOTES" >&2; exit 1; }
grep -q '^verdict: clean' "$notes" || {
  echo "The notes do not say \"verdict: clean\". Fix what the review found first." >&2
  exit 1
}
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "There are uncommitted changes. Commit them; the review covers HEAD only." >&2
  exit 1
fi

record=$(ne_review_file "$PWD")
mkdir -p "$(dirname "$record")"
cp "$notes" "$record"
echo "Recorded a clean review of $(git rev-parse --short HEAD)."
