#!/usr/bin/env bash
# Tells the agent the account's usage limits on every prompt, from the
# rate-limits.json a status line keeps in the config dir. Claude Code gives
# rate limits only to the status line, so without one this says nothing.
set -uo pipefail

f="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/rate-limits.json"
[ -f "$f" ] || exit 0

ctx=$(jq -r --argjson now "$(date +%s)" '
  def clock: strftime("%a %d %b %H:%M UTC");
  def window($name; $w):
    if $w.used_percentage == null then empty
    elif ($w.resets_at // 0) > 0 and $w.resets_at <= $now then "\($name): reset since this reading"
    else "\($name) \($w.used_percentage | round)% used" + (if $w.resets_at then ", resets \($w.resets_at | floor | clock)" else "" end)
    end;
  [window("5-hour window"; .five_hour // {}), window("Weekly"; .seven_day // {})] as $parts
  | if ($parts | length) == 0 then empty
    else "Usage limits for this account, as Claude Code reported them at \(.at): \($parts | join(". "))."
    end
' "$f" 2>/dev/null)

[ -n "$ctx" ] || exit 0
jq -cn --arg ctx "$ctx" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$ctx}}'
