#!/usr/bin/env bash
# pr-thread.sh reply PR COMMENT_ID BODY   reply in the thread that holds COMMENT_ID
# pr-thread.sh resolve THREAD_ID          mark a review thread resolved
# pr-thread.sh comment PR BODY            post a top-level comment on the PR
# IDs come from pr-state.sh. Run it from inside the repository the PR belongs to.
set -euo pipefail

usage() { sed -n '2,5p' "$0" | sed 's/^# //' >&2; exit 1; }
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

case "${1:-}" in
  reply)
    [ $# -eq 4 ] || usage
    gh api -X POST "repos/$repo/pulls/$2/comments/$3/replies" -f body="$4" --jq .html_url
    ;;
  resolve)
    [ $# -eq 2 ] || usage
    gh api graphql -f id="$2" -f query='
      mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }' \
      --jq '.data.resolveReviewThread.thread.isResolved'
    ;;
  comment)
    [ $# -eq 3 ] || usage
    gh pr comment "$2" --body "$3"
    ;;
  *) usage ;;
esac
