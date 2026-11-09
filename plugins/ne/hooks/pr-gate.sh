#!/usr/bin/env bash
# Refuses to open a PR, or mark one ready, until a fresh review of HEAD came
# back clean. The user can waive it for one PR by saying "skip review" in the
# message that asked for it. Exit 2 blocks the tool call and hands stderr to
# the agent.
set -uo pipefail
. "$(dirname "$0")/../lib/state.sh"

input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
grep -Eq '(^|[^[:alnum:]_-])gh[[:space:]]+pr[[:space:]]+(create|ready)([[:space:]]|$)' <<<"$cmd" || exit 0

dir=$(jq -r '.cwd // empty' <<<"$input")
lead=$(sed -nE 's/^[[:space:]]*cd[[:space:]]+"?([^"&;]+)"?[[:space:]]*(&&|;).*/\1/p' <<<"$cmd" | head -1)
if [ -n "$lead" ]; then
  lead=${lead%"${lead##*[![:space:]]}"}
  case "$lead" in /*) dir=$lead ;; "~"*) dir="$HOME${lead#\~}" ;; *) dir="$dir/$lead" ;; esac
fi
git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

transcript=$(jq -r '.transcript_path // empty' <<<"$input")
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  # -c keeps each message on one line, so tail picks the last whole message.
  last_user=$(tail -n 2000 "$transcript" | jq -c '
    select(.type == "user" and (.isMeta | not))
    | .message.content
    | if type == "string" then .
      elif type == "array" and (map(.type) | index("tool_result") | not)
        then map(select(.type == "text") | .text) | join("\n")
      else empty end' 2>/dev/null | tail -n 1)
  if grep -Eiq 'skip(ping)?( the)? review' <<<"$last_user"; then exit 0; fi
fi

record=$(ne_review_file "$dir") || exit 0
if [ -f "$record" ] && grep -q '^verdict: clean' "$record"; then exit 0; fi

sha=$(git -C "$dir" rev-parse --short HEAD)
cat >&2 <<EOF
No clean review is recorded for HEAD ($sha), so opening the PR is blocked.
Use the ne:truthsayer skill: a fresh-context review of the
branch, fixes for what it finds, and a recorded clean verdict for the commit
you open the PR from. A commit made after the review needs its own review.
Only the user can waive this, by saying "skip review".
EOF
exit 2
