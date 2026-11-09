#!/usr/bin/env bash
# Refuses a file edit inside a git repository until the work on this branch is
# classified: discovery agreed with the user, or skipped with a stated reason.
# Exit 2 blocks the tool call and hands stderr to the agent.
set -uo pipefail
. "$(dirname "$0")/../lib/state.sh"

input=$(cat)
file=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input")
[ -n "$file" ] || exit 0
case "$file" in /*) ;; *) file="$(jq -r '.cwd // empty' <<<"$input")/$file" ;; esac

dir=$(ne_existing_dir "$file")
git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
# The git directory itself is not the work.
gitdir=$(git -C "$dir" rev-parse --path-format=absolute --git-dir 2>/dev/null)
case "$file" in "$gitdir"/*) exit 0 ;; esac

record=$(ne_discovery_file "$dir") || exit 0
branch=$(git -C "$dir" symbolic-ref --quiet --short HEAD)
# A sietch holds records about the work, not the work.
case "$branch" in sietch/*) exit 0 ;; esac
discover="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/skills/mentat/scripts/discovery.sh"

# On a default branch one record would otherwise unlock every later task, so
# it lasts a working day.
if [ -f "$record" ] && ne_is_default_branch "$branch"; then
  mtime=$(stat -f %m "$record" 2>/dev/null || stat -c %Y "$record")
  if [ $(($(date +%s) - mtime)) -gt 43200 ]; then rm -f "$record"; fi
fi

status=$(ne_status "$record")
case "$status" in
  agreed | skipped) exit 0 ;;
  open)
    cat >&2 <<EOF
Discovery on branch "$branch" has open questions, so code edits are blocked.
Ask the user the open questions in $record with AskUserQuestion, record the
answers, and set "status: agreed" once every question is settled. Do not
answer them yourself.
EOF
    exit 2
    ;;
  *)
    cat >&2 <<EOF
Before the first edit on branch "$branch", classify the work.

If it is a feature, a user story, an enhancement, or anything that says what a
person should be able to do, use the ne:mentat skill and agree how it
should work with the user before building.

Otherwise record why discovery does not apply, in one line, with:
  $discover skip "<reason>"
Valid reasons: a bug with a clear reproduction and expected behavior, a
refactor with no change in behavior, a docs, test or config change, or the
user said to skip discovery. Tell the user the reason you recorded.
EOF
    exit 2
    ;;
esac
