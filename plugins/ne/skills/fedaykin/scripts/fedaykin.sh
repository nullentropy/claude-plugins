#!/usr/bin/env bash
# fedaykin.sh prompt TRACK UNIT              print the prompt that runs UNIT, after checking it may run
# fedaykin.sh routine TRACK UNIT ENV [MODEL]  print the RemoteTrigger create body that runs it in the cloud
# Refuses when the track is paused or the brief is missing or not yet pushed.
# Run it from inside the code repository.
set -euo pipefail
. "$(dirname "$0")/../../../lib/state.sh"

usage() { sed -n '2,5p' "$0" | sed 's/^# //' >&2; exit 1; }
cmd=${1:-}
track=${2:-}
unit=${3:-}
[ -n "$track" ] && [ -n "$unit" ] || usage
case "$cmd" in
  prompt) ;;
  routine)
    env=${4:-}
    model=${5:-claude-opus-5-5}
    [ -n "$env" ] || usage
    # Read the URL as configured: get-url applies insteadOf rewrites.
    url=$(git config --get remote.origin.url) || { echo "No origin remote. A cloud worker clones from GitHub." >&2; exit 1; }
    case "$url" in
      git@github.com:*) url="https://github.com/${url#git@github.com:}" ;;
      ssh://git@github.com/*) url="https://github.com/${url#ssh://git@github.com/}" ;;
    esac
    url=${url%.git}
    ;;
  *) usage ;;
esac
sietch="$(dirname "$0")/../../sietch/scripts/sietch.sh"
p=$("$sietch" open "$track")

status=$(sed -n 's/^Status:[[:space:]]*//p' "$p/RESUME.md" | head -1)
case "$status" in
  PAUSED* | DONE*)
    echo "Track $track is $status. Nothing is dispatched until the user resumes it." >&2
    exit 1
    ;;
esac
[ -f "$p/briefs/$unit.md" ] || { echo "No brief at $p/briefs/$unit.md. Write it first." >&2; exit 1; }
if git -C "$p" remote get-url origin >/dev/null 2>&1; then
  git -C "$p" fetch -q origin "sietch/$track" 2>/dev/null || true
  if ! git -C "$p" cat-file -e "origin/sietch/$track:briefs/$unit.md" 2>/dev/null ||
    [ -n "$(git -C "$p" status --porcelain)" ]; then
    echo "The brief is not pushed. Run: $sietch save $track \"Brief $unit\"" >&2
    exit 1
  fi
fi

prompt_text() {
  cat <<EOF
You are fedaykin unit $unit for the track $track, working in this repository.
Nobody can answer questions during this run. Your final message is your
report.

1. Read your brief and the standing orders. They live on the branch
   sietch/$track, not in your working tree:
     git fetch origin sietch/$track
     git show FETCH_HEAD:briefs/$unit.md
     git show FETCH_HEAD:orders.md
   Then read the repository's AGENTS.md or CLAUDE.md and follow them.
2. Work on the branch and base the brief names. Commit as you go, with
   explicit paths; every commit must build. Push your branch.
3. Do not launch reviewer agents and do not open a PR unless the brief says
   to. Do not run full test suites; run the tests your change needs, unless
   the brief says otherwise.
4. If the brief leaves a decision about how the product behaves open, do not
   guess. Leave that part undone and put the question in your report.
5. Write your report to reports/$unit.md on the sietch branch and push it:
     git worktree add --detach /tmp/sietch-$track-$unit FETCH_HEAD
     (write /tmp/sietch-$track-$unit/reports/$unit.md)
     git -C /tmp/sietch-$track-$unit add reports/$unit.md
     git -C /tmp/sietch-$track-$unit commit -m "Report $unit"
     git -C /tmp/sietch-$track-$unit push origin HEAD:sietch/$track
   If the push is rejected, fetch sietch/$track again, rebase onto it, and
   push again. Never force-push it.

The report says: branch, head commit, commits, what was done, what remains,
the tests and commands you ran with their results, open questions, and every
place you departed from the brief and why. Do not claim anything you did not
check.
EOF
}
prompt=$(prompt_text)

if [ "$cmd" = prompt ]; then
  printf '%s\n' "$prompt"
  exit 0
fi

# The next whole minute, so the routine fires as soon as it is created.
at=$(date -u -v+1M +%Y-%m-%dT%H:%M:00Z 2>/dev/null || date -u -d '+1 minute' +%Y-%m-%dT%H:%M:00Z)
jq -n --arg name "$track: $unit" --arg at "$at" --arg env "$env" --arg model "$model" \
  --arg url "$url" --arg prompt "$prompt" --arg uuid "$(uuidgen | tr '[:upper:]' '[:lower:]')" '{
  name: $name,
  enabled: true,
  run_once_at: $at,
  job_config: {ccr: {
    environment_id: $env,
    session_context: {
      model: $model,
      sources: [{git_repository: {url: $url}}],
      allowed_tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
    },
    events: [{data: {
      type: "user", uuid: $uuid, session_id: "", parent_tool_use_id: null,
      message: {role: "user", content: $prompt}
    }}]
  }}
}'
