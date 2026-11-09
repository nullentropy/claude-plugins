#!/usr/bin/env bash
# pr-state.sh PR   print what needs doing on PR: mergeability, failing checks, open threads
# Run it from inside the repository the PR belongs to.
set -euo pipefail

pr=${1:?usage: pr-state.sh PR}
read -r owner repo < <(gh repo view --json owner,name --jq '"\(.owner.login) \(.name)"')

gh api graphql -F o="$owner" -F r="$repo" -F n="$pr" -f query='
query($o: String!, $r: String!, $n: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $n) {
      number title url state isDraft headRefName baseRefName mergeable mergeStateStatus
      commits(last: 1) { nodes { commit { oid statusCheckRollup { state
        contexts(first: 100) { nodes {
          ... on CheckRun { name conclusion status detailsUrl }
          ... on StatusContext { context state targetUrl }
        } } } } } }
      reviewThreads(first: 100) { nodes {
        id isResolved isOutdated path line
        comments(first: 30) { nodes { databaseId author { login } body } }
      } }
    }
  }
}' --jq '
.data.repository.pullRequest as $p
| ($p.commits.nodes[0].commit) as $c
| {
    pr: $p.number, title: $p.title, url: $p.url, state: $p.state, draft: $p.isDraft,
    head: $p.headRefName, base: $p.baseRefName, headSha: $c.oid[0:9],
    mergeable: $p.mergeable, mergeState: $p.mergeStateStatus,
    checks: ($c.statusCheckRollup.state // "NONE"),
    failing: [ $c.statusCheckRollup.contexts.nodes[]?
      | select((.conclusion // .state) as $s | $s == "FAILURE" or $s == "ERROR" or $s == "TIMED_OUT" or $s == "CANCELLED" or $s == "ACTION_REQUIRED")
      | {name: (.name // .context), url: (.detailsUrl // .targetUrl)} ],
    pending: [ $c.statusCheckRollup.contexts.nodes[]?
      | select(.status == "IN_PROGRESS" or .status == "QUEUED" or .state == "PENDING")
      | (.name // .context) ],
    openThreads: [ $p.reviewThreads.nodes[] | select(.isResolved | not)
      | { thread: .id, path, line, outdated: .isOutdated,
          comments: [ .comments.nodes[] | {id: .databaseId, by: .author.login, body: (.body | .[0:600])} ] } ]
  }'
