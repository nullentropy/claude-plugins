---
name: swordmaster
description: Take open PRs to green and fully answered. For each PR, brings it up to date with its base and resolves conflicts, fixes real CI failures and reruns flaky ones, fixes valid review comments from people and bots, pushes back on nitpicks and wrong ones, replies in and resolves every thread, and confirms the push. Use for "fix <PR number>", "babysit the PR", "there are comments on", "copilot has comments", "the build is failing", "has conflicts", "address the review", "did you respond to", or a list of PR numbers.
---

# Swordmaster

Every PR named comes back green, current with its base, and with every thread
answered and resolved. Do all of it in one pass without being asked for each
part. Work through several PRs one after another.

The scripts call GitHub for you. Run them from inside the repository.
`scripts/pr-state.sh <pr>` prints the PR's mergeability, failing and pending
checks, and every unresolved thread with its IDs. `scripts/pr-thread.sh`
replies, resolves and comments.

## For each PR

1. **Read the state** with `pr-state.sh`. If the PR was opened by someone
   other than the user, fix nothing on it unless the user said to; review and
   comment instead.

2. **Check out the branch** in a worktree of its own, never in a checkout the
   user is working in. Use the repository's worktree convention if it has
   one.

3. **Bring it up to date.** Merge the base into the branch when it conflicts
   or is behind; do not rebase a branch other people may have pulled.
   Resolve conflicts by reading both sides. When the PR is in a stack, fix the
   lowest PR first, then merge each PR into the one stacked on it.

4. **Triage every open thread,** from people and bots alike. Read the code it
   points at before deciding.
   - **Valid:** fix it.
   - **Nitpick or wrong:** do not change the code. Reply with the reason in a
     sentence or two.
   - **A question about how the product should behave:** ask the user. Do not
     decide it in a reply.

5. **Fix CI.** For each failing check, read the failed log
   (`gh run view <run> --log-failed`). Fix a real failure. If the failure is
   unrelated to the change and passes on rerun, rerun it
   (`gh run rerun <run> --failed`) and say it was a flake. Do not run full
   suites locally; run only the test you are fixing.

6. **Push,** then reply in every thread: what changed and the commit, or why
   nothing changed. Resolve each thread you fixed or answered. Leave a thread
   open only when it waits on the user.

7. **Confirm.** Check that the branch is not ahead of its remote, then run
   `pr-state.sh` again. If checks are still running and the session can wait,
   check again when they finish, and fix again if they fail.

## Report

One line per PR: green or not, how many threads were fixed, answered and
left open and why, and anything that needs the user.
