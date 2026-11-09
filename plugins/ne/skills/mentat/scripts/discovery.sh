#!/usr/bin/env bash
# discovery.sh path           print the discovery record for this branch, creating its directory
# discovery.sh status         print the record's status: open, agreed, skipped, or none
# discovery.sh skip "<why>"   record that discovery does not apply, and why
# Run it from inside the repository the work is in.
set -euo pipefail
. "$(dirname "$0")/../../../lib/state.sh"

record=$(ne_discovery_file "$PWD") || {
  echo "Not on a branch inside a git repository." >&2
  exit 1
}
mkdir -p "$(dirname "$record")"

case "${1:-}" in
  path) echo "$record" ;;
  status)
    s=$(ne_status "$record")
    echo "${s:-none}"
    ;;
  skip)
    reason="${2:-}"
    [ -n "$reason" ] || { echo "Give the reason discovery does not apply." >&2; exit 1; }
    printf 'status: skipped\nreason: %s\nrecorded: %s\n' "$reason" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$record"
    echo "Recorded: $reason"
    ;;
  *)
    sed -n '2,4p' "$0" | sed 's/^# //' >&2
    exit 1
    ;;
esac
