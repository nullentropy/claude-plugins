---
name: water
description: Budget a track's work against the user's weekly limit. Records the limit percentages the user reports, estimates where the limit stands now and whether the remaining units fit before the stop line, and sets how many workers run at once. Use before dispatching work, when the user gives a percentage like "82%", and for "will this finish before the limit", "how much do we have left", "are we going to run out".
---

# Water

Claude Code gives the weekly limit only to the status line command. The
plugin's `statusline.sh` keeps it in `rate-limits.json` in the config dir, and
the `limits.sh` hook puts it in the context of every prompt. When the status
line is set up, the figure in the prompt context is the reading: do not ask
the user for one. `scripts/water.py` records it as a reading whenever it moves
and turns the readings into a rate, counting the tokens in this machine's
transcripts between them, so a unit's tokens become percent.

- Before dispatching, and when asked, run
  `python3 -I scripts/water.py report <sietch dir>` and give its verdict in
  one sentence. The sietch dir is what `sietch.sh open` prints. Save the
  sietch afterwards if `water.tsv` changed.
- When the user gives a reading, record it right away:
  `python3 -I scripts/water.py mark <sietch dir> <percent>`. Then save the
  sietch. `mark` with no percent records the status line's figure.

Without the status line, the figure now is an estimate from local work only.
Cloud workers spend from the same limit without showing up here, so while
they run, ask the user for a fresh reading before deciding anything close to
the line. The status line's figure counts every session on the account.

## Rules

- The stop line is 90% unless `orders.md` sets another (`NE_STOP_LINE`
  overrides it for the script). At the stop line, dispatch nothing, finish or
  checkpoint the units already running, and pause the track with the reason.
- If the remaining units do not fit, say so before starting them and propose
  which to drop or defer.
- Run at most three workers at once unless `orders.md` says otherwise, and on
  the laptop at most one heavy command (a full build, a full test run) at a
  time.
- Use Sonnet for workers that follow an existing pattern; keep the default
  model for hard design.
