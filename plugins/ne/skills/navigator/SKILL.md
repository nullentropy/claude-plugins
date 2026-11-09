---
name: navigator
description: Pick what to work on next and write the briefs for it. Reads the sietch's next steps and ledger, the user's open PRs and assigned tickets, and proposes the next units in order with a reason for each; on the user's yes, writes each unit's brief for ne:fedaykin. Use for "what's next", "what do we work on next", "what should I work on today", "what can we pick up", or to plan the next slices of a track.
---

# Navigator

Propose the next units of work, get the user's yes, and write the briefs. Do
not dispatch; ne:fedaykin does that.

## Read

- The track, if there is one: `RESUME.md` Next, the last 15 ledger rows,
  `overview` or follow-up notes, and units held or needing follow-up.
- Open PRs by the user: `gh pr list --author @me --json number,title,isDraft,reviewDecision,mergeable,statusCheckRollup`.
  A red, conflicting or commented PR comes before new work; that is
  ne:swordmaster's job.
- Tickets assigned to the user that are not done:
  `gh issue list --assignee @me --state open`, and the repository's own
  ticket skill if it has one.
- The repository's plan or roadmap documents if the track names them.

Check what you read against the code. A step marked next may already be done.

## Propose

At most five units, in order. For each: what it does in one sentence, why it
comes now (it unblocks something, it is red, it is small and finishes a
section), what it depends on, whether it runs in the cloud or needs this
machine, and whether it is a feature that needs ne:mentat discovery first.
Then ask the user which to take.

## Write the briefs

For each unit the user takes, write `briefs/<unit>.md` in the sietch for a
worker with no memory of this session:

```
# <unit>: <one-line goal>

Branch: <new branch>, cut from <base commit>
PR: <open one after ne:truthsayer | no PR>
Timebox: <how much work before stopping to report>

## Context
<what exists, with file paths; what is missing>

## Goal
<what the change does>

## Done means
<what is true when it is finished, and how the worker checks it>

## Orders that matter most here
<numbers from orders.md, plus anything specific to this unit>
```

Add the units to Next in `RESUME.md` and save the sietch.
