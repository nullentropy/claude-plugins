---
name: truthsayer
description: Review a branch with fresh context, fix what matters, and record a clean verdict before a PR is opened. Use before opening a PR or marking one ready, when asked to review your own work before it goes up, and whenever the PR gate blocks gh pr create.
---

# Truthsayer

A PR goes up once a reviewer that never saw this session has read the change
and found nothing significant. Reviewers and teammates should not be the first
to find a bug.

The user can waive this for one PR by saying "skip review". Nobody else can.

## Steps

1. **Get the range.** Commit everything. Fetch, and find the base with
   `git merge-base HEAD origin/<default branch>`. If the branch is far behind,
   bring it up to date first, so the review sees what the PR will contain.

2. **Review.** Spawn the `ne:gom-jabbar` agent. Give it the repository
   path, the base and head commits, and the ask: the ticket text or the user's
   request, word for word. Give it nothing else. Your summary of the change,
   your reasoning and your doubts would steer it toward your own conclusions.

3. **Check each finding.** Read the code it points at. Keep a finding that
   holds and drop one that does not, with the reason. Never drop a finding
   because fixing it is work.

4. **Fix and re-review.** Fix every finding you kept and commit. Then review
   again with base set to the commit the last review covered, so the reviewer
   reads only the fixes. Stop after three rounds that still find something
   significant, and tell the user what keeps coming back.

5. **Record it.** Write the notes to a scratch file:

   ```
   verdict: clean
   head: <sha>
   rounds: <n>
   <each finding, and whether it was fixed or dropped and why>
   ```

   Run `scripts/record-review.sh <notes>` from inside the repository. The PR
   gate checks that this record exists for HEAD. A commit made after the
   record needs its own review.

6. **Open the PR** with the repository's own PR skill if it has one. The PR
   body does not mention this review.
