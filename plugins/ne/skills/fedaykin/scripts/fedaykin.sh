#!/usr/bin/env bash
# fedaykin.sh prompt TRACK UNIT   print the prompt that runs UNIT, after checking it may run
# Refuses when the track is paused or the brief is missing or not yet pushed.
# Run it from inside the code repository.
set -euo pipefail
. "$(dirname "$0")/../../../lib/state.sh"

[ "${1:-}" = prompt ] && [ -n "${2:-}" ] && [ -n "${3:-}" ] || {
  sed -n '2,4p' "$0" | sed 's/^# //' >&2
  exit 1
}
track=$2
unit=$3
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
