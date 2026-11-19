---
name: fedaykin
description: Dispatch one unit of a sietch track to a worker, in a Claude cloud session by default or as a local background agent, with a self-contained prompt built from its brief. Use to launch, spawn, dispatch or send out work from a track, to run a slice unattended, or to move heavy work off the laptop.
---

# Fedaykin

A fedaykin is one worker on one unit of a track. It reads its brief and the
standing orders from the sietch branch, works on its own branch, and writes
its report back to the sietch. The prompt is self-contained, so the worker
needs no plugin, no memory and no one to ask.

## Before dispatching

1. The unit has a brief at `briefs/<unit>.md` in the sietch. A brief names:
   the unit, the branch to create and the base commit to cut it from, the
   context (what exists, what is missing, with file paths), the goal, what
   done means and how it is checked, which standing orders matter most,
   whether to open a PR, and a timebox. Write briefs for a worker with no
   memory of this session. ne:navigator writes them.
2. Save the sietch so the brief is pushed. A cloud worker reads it from
   origin.
3. Ask ne:water whether the budget allows it, and respect the concurrency
   limit in `orders.md`. With no limit there, run at most three at once.

## Dispatch

Run `scripts/fedaykin.sh` from inside the code repository. It refuses if the
track is paused or the brief is not pushed. Do not dispatch around a refusal.

- **Cloud, the default.** Run it as a one-time cloud routine. `claude --cloud`
  does not work here: it refuses to start without an interactive terminal.
  The Agent tool's `isolation: "remote"` does not either: it has run workers
  in a worktree on the laptop.
  1. Push the base the brief names, because the cloud session clones from
     GitHub.
  2. Find the cloud environment ID (`env_...`). Take it from the track's last
     routine (`RemoteTrigger get` on the trigger ID in the ledger), or from
     another routine on the same repository (`RemoteTrigger list`). If there
     is none, ask the user which environment to use.
  3. Build the body with
     `scripts/fedaykin.sh routine <track> <unit> <env_id> [model]` and pass it
     to `RemoteTrigger` with `action: "create"`. It fires at the next whole
     minute. The model defaults to claude-opus-5-5; pass claude-sonnet-5-5 for
     work that follows an existing pattern.
  4. Record the trigger ID it returns. `RemoteTrigger list_runs` with that ID
     gives the session, and `get_run_log` shows what the worker is doing.
- **Local,** when the user asks for it or the work needs this machine. Use the
  Agent tool in the background with worktree isolation and the output of
  `scripts/fedaykin.sh prompt <track> <unit>`. Use Sonnet for work that
  follows an existing pattern and the default model for hard design.

Append a ledger row: `dispatched`, the branch, and the trigger ID or agent
name as evidence. Save the sietch.

## When a unit reports

Read `reports/<unit>.md` after `sietch.sh open`, or the agent's final message.
Check its claims in the code: the commits exist, the tests it names pass in
CI, the brief's done condition holds. Record `reported`, then `landed`,
`held` with why, or `needs follow-up` with a new brief. Put the tokens a local
agent used in the ledger's tokens column so ne:water can estimate the rest.
