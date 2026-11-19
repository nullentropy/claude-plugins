#!/usr/bin/env bash
# Checks the body fedaykin.sh routine prints for RemoteTrigger create.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export NE_STATE="$tmp/state"

git init -q --bare "$tmp/origin.git"
git clone -q "$tmp/origin.git" "$tmp/repo" 2>/dev/null
cd "$tmp/repo"
git commit -q --allow-empty -m init
git push -q origin HEAD:main
git remote set-url origin https://github.com/acme/widgets.git
git remote set-url --push origin "$tmp/origin.git"
git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
# The fetch URL is GitHub for the body; fetches in the test go to the bare repo.
git config url."$tmp/origin.git".insteadOf https://github.com/acme/widgets.git

"$here/../../sietch/scripts/sietch.sh" new demo >/dev/null
p=$("$here/../../sietch/scripts/sietch.sh" open demo)
mkdir -p "$p/briefs"
echo "# u1" >"$p/briefs/u1.md"
"$here/../../sietch/scripts/sietch.sh" save demo "Brief u1" >/dev/null

fail() { echo "FAIL: $*" >&2; exit 1; }

body=$("$here/fedaykin.sh" routine demo u1 env_test123)
jq -e . >/dev/null <<<"$body" || fail "body is not JSON"
[ "$(jq -r .job_config.ccr.environment_id <<<"$body")" = env_test123 ] || fail "environment"
[ "$(jq -r '.job_config.ccr.session_context.sources[0].git_repository.url' <<<"$body")" = https://github.com/acme/widgets ] || fail "repository url"
jq -r '.job_config.ccr.events[0].data.message.content' <<<"$body" | grep -q "fedaykin unit u1 for the track demo" || fail "prompt"
[ "$(jq -r .name <<<"$body")" = "demo: u1" ] || fail "name"
jq -r .run_once_at <<<"$body" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:00Z$' || fail "run_once_at"

if "$here/fedaykin.sh" routine demo u1 2>/dev/null; then fail "ran without an environment"; fi
echo ok
