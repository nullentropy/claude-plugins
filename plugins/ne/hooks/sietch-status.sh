#!/usr/bin/env bash
# Names the tracks this repository has, so a new session knows to resume one
# rather than start over. Local branches only: no network at session start.
set -uo pipefail

dir=$(jq -r '.cwd // empty' 2>/dev/null)
[ -n "$dir" ] || dir=$PWD
git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

lines=$(git -C "$dir" for-each-ref --format='%(refname:short)' refs/heads/sietch refs/remotes/origin/sietch 2>/dev/null |
  sed -E 's#^(origin/)?sietch/##' | sort -u | while read -r n; do
    ref="sietch/$n"
    git -C "$dir" show-ref --verify --quiet "refs/heads/$ref" || ref="origin/sietch/$n"
    s=$(git -C "$dir" show "$ref:RESUME.md" 2>/dev/null | sed -n 's/^Status:[[:space:]]*//p' | head -1)
    echo "- $n: ${s:-unknown}"
  done)
[ -n "$lines" ] || exit 0

jq -cn --arg ctx "Tracks in this repository (ne:sietch):
$lines
To pick one up, open it with the ne:sietch skill and read its HANDOFF.md first." \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
