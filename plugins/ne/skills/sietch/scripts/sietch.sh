#!/usr/bin/env bash
# sietch.sh new NAME         create the track's branch and worktree from the templates
# sietch.sh open NAME        print the worktree path, fetching it from origin if needed
# sietch.sh save NAME MSG    commit everything in the worktree, rebase on origin, push
# sietch.sh status NAME      print the Status line of RESUME.md
# sietch.sh list             list this repository's tracks and their status
# Run it from inside the code repository the track belongs to.
set -euo pipefail
. "$(dirname "$0")/../../../lib/state.sh"

here=$(git rev-parse --show-toplevel)
cmd=${1:-}
name=${2:-}

usage() { sed -n '2,7p' "$0" | sed 's/^# //' >&2; exit 1; }
need_name() { [ -n "$name" ] || usage; }
path_of() { echo "$(ne_repo_dir "$here")/sietch/$1"; }
has_origin() { git -C "$here" remote get-url origin >/dev/null 2>&1; }
remote_has() { has_origin && git -C "$here" ls-remote --exit-code --heads origin "sietch/$1" >/dev/null 2>&1; }

ensure() {
  local p
  p=$(path_of "$1")
  if [ -e "$p/.git" ]; then echo "$p"; return 0; fi
  git -C "$here" worktree prune
  mkdir -p "$(dirname "$p")"
  if git -C "$here" show-ref --verify --quiet "refs/heads/sietch/$1"; then
    git -C "$here" worktree add -q "$p" "sietch/$1"
  elif remote_has "$1"; then
    git -C "$here" fetch -q origin "sietch/$1:refs/remotes/origin/sietch/$1"
    git -C "$here" worktree add -q --track -b "sietch/$1" "$p" "origin/sietch/$1"
  else
    echo "No sietch named $1 here or on origin. Create it with: sietch.sh new $1" >&2
    return 1
  fi
  echo "$p"
}

sync_from_origin() {
  local p=$1
  remote_has "$name" || return 0
  [ -z "$(git -C "$p" status --porcelain)" ] || return 0
  git -C "$p" pull -q --rebase origin "sietch/$name" || {
    git -C "$p" rebase --abort 2>/dev/null || true
    echo "Could not rebase sietch/$name onto origin. Resolve it by hand in $p." >&2
    return 1
  }
}

templates() {
  local p=$1 today
  today=$(date -u +%Y-%m-%d)
  mkdir -p "$p/briefs" "$p/reports"
  : >"$p/briefs/.keep"
  : >"$p/reports/.keep"
  cat >"$p/HANDOFF.md" <<EOF
# $name

Read this first if you are picking this track up with no memory of earlier
sessions. Then read orders.md, RESUME.md and the last 15 rows of ledger.tsv.

## The job

The user's ask, verbatim:

> (the ask)

Done means: (what is true when this track is finished)

## Where things live

| Thing | Where |
|---|---|
| This sietch | branch \`sietch/$name\`; open it with the ne:sietch skill |
| Code | (repository, base branch, integration branch if any) |
| Briefs | \`briefs/<unit>.md\`, one per unit of work |
| Reports | \`reports/<unit>.md\`, what each unit did, in its own words |
| Ledger | \`ledger.tsv\`, one row per unit event |
| Decisions | \`decisions.tsv\`, each decision and why |
| Water | \`water.tsv\`, the user's weekly-limit readings |

## The loop

1. ne:navigator picks the next units and writes their briefs.
2. ne:water says whether the budget allows them. Nothing is dispatched past
   the stop line.
3. ne:fedaykin dispatches each unit, in the cloud by default, and records it.
4. When a unit reports, read the report against its brief and check its
   claims in the code. Record the outcome in the ledger.
5. A PR goes up only after ne:truthsayer. ne:swordmaster handles comments, CI
   and conflicts on open PRs.
6. Checkpoint with ne:sietch after every outcome and before stopping.
EOF
  cat >"$p/orders.md" <<EOF
# Standing orders for $name

Every unit reads these before any work.

0. Stop line: none.
EOF
  cat >"$p/RESUME.md" <<EOF
Status: RUNNING
Updated: $today

Head: (the commit this state refers to)

Progress:
- (section): (done) of (total), (percent)%, counted by (how)

Next, in order:
1. (unit or step, with enough detail to start it cold)
EOF
  printf 'when\tunit\tstate\tbranch\thead\ttokens\tevidence\n' >"$p/ledger.tsv"
  printf 'when\tdecision\twhy\tevidence\n' >"$p/decisions.tsv"
  printf 'when\tpercent\tnote\n' >"$p/water.tsv"
}

case "$cmd" in
  new)
    need_name
    if git -C "$here" show-ref --verify --quiet "refs/heads/sietch/$name" || remote_has "$name"; then
      echo "sietch/$name already exists. Open it with: sietch.sh open $name" >&2
      exit 1
    fi
    p=$(path_of "$name")
    mkdir -p "$(dirname "$p")"
    git -C "$here" worktree prune
    git -C "$here" worktree add -q --orphan -b "sietch/$name" "$p"
    templates "$p"
    git -C "$p" add -A
    git -C "$p" commit -qm "Start sietch $name"
    echo "$p"
    ;;
  open)
    need_name
    p=$(ensure "$name")
    sync_from_origin "$p"
    echo "$p"
    ;;
  save)
    need_name
    msg=${3:-Checkpoint}
    p=$(ensure "$name")
    git -C "$p" add -A
    git -C "$p" commit -qm "$msg" || true
    if ! has_origin; then echo "Saved locally. There is no origin to push to."; exit 0; fi
    if remote_has "$name"; then
      git -C "$p" pull -q --rebase origin "sietch/$name" || {
        git -C "$p" rebase --abort 2>/dev/null || true
        echo "Saved locally. Rebasing onto origin conflicted; resolve it by hand in $p." >&2
        exit 1
      }
    fi
    if git -C "$p" push -q -u origin "HEAD:sietch/$name" 2>/dev/null; then
      echo "Saved and pushed sietch/$name at $(git -C "$p" rev-parse --short HEAD)."
    else
      echo "Saved locally at $(git -C "$p" rev-parse --short HEAD). The push failed; run save again." >&2
      exit 1
    fi
    ;;
  status)
    need_name
    p=$(ensure "$name")
    sed -n 's/^Status:[[:space:]]*//p' "$p/RESUME.md" | head -1
    ;;
  list)
    has_origin && git -C "$here" fetch -q origin 'refs/heads/sietch/*:refs/remotes/origin/sietch/*' 2>/dev/null || true
    git -C "$here" for-each-ref --format='%(refname)' refs/heads/sietch refs/remotes/origin/sietch |
      sed -E 's#^refs/(heads|remotes/origin)/sietch/##' | sort -u | while read -r n; do
        ref="sietch/$n"
        git -C "$here" show-ref --verify --quiet "refs/heads/$ref" || ref="origin/sietch/$n"
        s=$(git -C "$here" show "$ref:RESUME.md" 2>/dev/null | sed -n 's/^Status:[[:space:]]*//p' | head -1)
        printf '%s\t%s\n' "$n" "${s:-unknown}"
      done
    ;;
  *) usage ;;
esac
