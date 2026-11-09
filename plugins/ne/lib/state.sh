# Where the gates keep their records. Sourced by the hooks and the skill scripts.
#
# Records live outside the repository so no edit gate stands in front of them
# and none of them can be committed by accident. They are keyed by the git
# common dir, so every worktree of one clone shares them.

ne_root() {
  echo "${NE_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/ne}"
}

ne_hash() {
  if command -v shasum >/dev/null 2>&1; then
    printf %s "$1" | shasum -a 256 | cut -c1-16
  else
    printf %s "$1" | sha256sum | cut -c1-16
  fi
}

# ne_repo_dir DIR: the record directory for the clone DIR belongs to.
ne_repo_dir() {
  local common
  common=$(git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 1
  echo "$(ne_root)/$(ne_hash "$common")"
}

ne_is_default_branch() {
  case "$1" in main | master | trunk | develop) return 0 ;; *) return 1 ;; esac
}

# ne_discovery_file DIR: the discovery record for DIR's current branch.
# Fails on a detached HEAD, where there is no branch to hold one.
ne_discovery_file() {
  local branch
  branch=$(git -C "$1" symbolic-ref --quiet --short HEAD 2>/dev/null) || return 1
  echo "$(ne_repo_dir "$1")/discovery/${branch//\//__}.md"
}

# ne_review_file DIR: the review record for DIR's HEAD commit.
ne_review_file() {
  local sha
  sha=$(git -C "$1" rev-parse HEAD 2>/dev/null) || return 1
  echo "$(ne_repo_dir "$1")/reviewed/$sha.md"
}

# ne_status FILE: the value of the first "status:" line, or nothing.
ne_status() {
  [ -f "$1" ] || return 0
  sed -n 's/^status:[[:space:]]*//p' "$1" | head -1 | tr -d '[:space:]'
}

# ne_existing_dir PATH: PATH's nearest directory that exists, so a Write to a
# file in a directory not created yet still resolves to its repository.
ne_existing_dir() {
  local d
  d=$(dirname "$1")
  while [ ! -d "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do d=$(dirname "$d"); done
  echo "$d"
}
