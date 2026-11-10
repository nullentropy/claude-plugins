---
name: sietch
description: The shared record of a long-running track of work, kept on its own git branch so any session, laptop or cloud, can pick it up with no memory of earlier ones. Use to start a track, checkpoint it, hand it off, resume it, pause it, or report its status in percentages. Triggers on "hand this off", "make sure another agent can pick this up", "resume", "keep going on", "status report", "% report", "pause", "stop spawning".
---

# Sietch

A sietch is one track's record: what the job is, the standing orders, where
things are, what is done and what is next. It lives on the branch
`sietch/<name>` in the code repository, which shares no history with the code,
so it never reaches a PR. `scripts/sietch.sh` manages it. Run the script from
inside the code repository.

| File | Holds | Changes |
|---|---|---|
| `HANDOFF.md` | The job, the user's ask verbatim, what done means, where things live, the loop | Rarely |
| `orders.md` | Standing orders every unit reads. Order 0 is the stop line | When the user rules on something |
| `RESUME.md` | Status, head, progress in percentages, next steps in order | Every checkpoint |
| `ledger.tsv` | One row per unit event: dispatched, reported, landed, held | Every outcome |
| `decisions.tsv` | Each decision, why, and the evidence | When one is made |
| `water.tsv` | Weekly-limit readings, the user's and the status line's | When the user gives one, or a water report records one |
| `briefs/`, `reports/` | One brief per unit, one report per unit | Per unit |

## Start a track

`sietch.sh new <name>` creates the branch and a worktree from the templates
and prints its path. Fill `HANDOFF.md` with the user's ask word for word and
what done means, and put any rulings the user has already given in
`orders.md`. Save it.

## Checkpoint

After every unit outcome, before you stop, when the user asks for a handoff,
and whenever the remaining budget is low:

1. Rewrite `RESUME.md`. Status first: `RUNNING`, `PAUSED by <who> <date>:
   <why>`, or `DONE`. Then the head commit the state refers to, progress as
   `done of total, percent, counted by how`, and the next steps in order, each
   with enough detail that an agent with no memory of this session can start
   it.
2. Append ledger and decision rows. A row says what happened and the evidence,
   not what was hoped.
3. `sietch.sh save <name> "<what changed>"`. It commits, rebases on origin and
   pushes. If the push fails, say so.

## Resume

`sietch.sh open <name>` prints the worktree path, fetching it if this machine
has never seen it. Read `HANDOFF.md`, `orders.md`, `RESUME.md` and the last 15
ledger rows. Before acting on them, check them against the repository: the
head exists, the branches named exist, the PRs named are in the state
recorded. Then take step 1 of Next. If the status is `PAUSED`, do nothing
until the user says to resume, and then set it back to `RUNNING`.

## Status report

Quote the progress lines from `RESUME.md` after checking them against the
repository, then one sentence: on track, blocked on what, or done. Add the
ne:water estimate when the user asks about the limit, and the ne:spice harvest
when they ask what reached production.

## Pause

Set the status to `PAUSED by <who> <date>: <why>`, write it as order 0 in
`orders.md` too, and save. ne:fedaykin refuses to dispatch while a track is
paused.

`sietch.sh list` shows every track in the repository and its status.
