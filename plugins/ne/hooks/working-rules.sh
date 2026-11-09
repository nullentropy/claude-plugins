#!/usr/bin/env bash
# States how the user wants work done, once per session and again after a
# compaction drops it from context.
set -uo pipefail

IFS= read -r -d '' RULES <<'EOF'
How the user wants work done. These are standing preferences for every task.

Do the work.
- Finish the task. Do not hand the user a step you can do yourself, and do not
  propose a follow-up you could do now. If something blocks you, name it and
  what would unblock it.
- When work belongs on a branch, commit and push it before calling it done,
  and say which commit.
- Check a claim against the code, logs or docs before stating it. If it
  contradicts something said earlier, say which statement was wrong.
- When the user asks what to do, give the verdict first in one sentence (fine,
  broken, or act), then the exact command or step.
- If the request is ambiguous about behavior, ask. Do not fill the gap with an
  assumption about how the product should work.

What to add.
- For a bug: a failing regression test first, then the fix.
- A comment only where the code looks wrong until you know the reason.
- When a change alters documented behavior, update that doc or spec in the
  same change.

What not to add unless asked.
- Feature flags, rollout plans, persona or stakeholder sections, sign-off
  steps, or other process around the change.
- Comments that restate the code or record how it came to be.
- Tests that only check a function returns what it was handed.
- Compatibility shims, or an old and a new path side by side.
- Draft PRs, and reviewers or assignees on work nobody requested.
- Nitpicks in a review.
- Estimates in human days or weeks.
- A change that makes someone adjust a third-party setting when a code change
  would do.

Cost.
- Do not run full test suites, benchmarks or extra review agents unless the
  user or a skill asks. CI runs the suites. On a laptop (CLAUDE_CODE_REMOTE is
  unset), run only the targeted tests the change needs, one run at a time.
- Use a cheaper model, such as Sonnet, for mechanical subagent work: searching,
  reading files, renaming.

Gates. Two hooks enforce the ne plugin. A code edit in a repository is
refused until the branch's work is classified, through the ne:mentat
skill or a recorded skip. Opening a PR is refused until the
ne:truthsayer skill records a clean review of HEAD.

Tracks. Work that outlives one session is kept in a sietch (ne:sietch): the
job, standing orders, progress and next steps on the branch sietch/<name>.
Checkpoint it after every outcome and before stopping.
EOF

jq -cn --arg ctx "$RULES" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
