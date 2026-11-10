#!/usr/bin/env bash
# Prints the status line, and keeps the account's latest rate limits in
# rate-limits.json in the config dir, where the ne plugin's prompt hook and
# ne:water read them. Claude Code hands rate limits to nothing but this script.
input=$(cat)
conf="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

limits=$(jq -c '.rate_limits // empty' <<<"$input" 2>/dev/null)
if [ -n "$limits" ] && [ "$limits" != "{}" ]; then
  tmp=$(mktemp "$conf/.rate-limits.XXXXXX") &&
    jq -c --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '{at: $at} + .' <<<"$limits" >"$tmp" &&
    mv "$tmp" "$conf/rate-limits.json"
fi

when() {
  date -r "$1" "+$2" 2>/dev/null || date -d "@$1" "+$2" 2>/dev/null
}

paint() {
  local p=${1%.*}
  if [ "$p" -ge 80 ]; then printf '\033[31m%s%%\033[0m' "$1"
  elif [ "$p" -ge 50 ]; then printf '\033[33m%s%%\033[0m' "$1"
  else printf '\033[32m%s%%\033[0m' "$1"; fi
}

model=$(jq -r '.model.display_name // empty' <<<"$input")
cwd=$(jq -r '.workspace.current_dir // .cwd // empty' <<<"$input")
ctx=$(jq -r '.context_window.used_percentage // empty' <<<"$input")

parts=()
[ -n "$model" ] && parts+=("$model")
if [ -n "$cwd" ]; then
  branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
  parts+=("${cwd##*/}${branch:+ ($branch)}")
fi
[ -n "$ctx" ] && parts+=("ctx $(printf '%.0f' "$ctx")%")

for w in five_hour:5h:%H:%M seven_day:7d:%a\ %H:%M; do
  key=${w%%:*}; rest=${w#*:}; label=${rest%%:*}; fmt=${rest#*:}
  pct=$(jq -r ".rate_limits.$key.used_percentage // empty" <<<"$input")
  [ -n "$pct" ] || continue
  pct=$(printf '%.0f' "$pct")
  reset=$(jq -r ".rate_limits.$key.resets_at // empty" <<<"$input")
  parts+=("$label $(paint "$pct")${reset:+ until $(when "${reset%.*}" "$fmt")}")
done

out=""
for p in "${parts[@]}"; do out+="${out:+ · }$p"; done
printf '%b\n' "$out"
