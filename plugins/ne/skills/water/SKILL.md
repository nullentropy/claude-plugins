---
name: water
description: Budget a track's work against the user's weekly limit. Records the limit percentages the user reports, estimates where the limit stands now and whether the remaining units fit before the stop line, and sets how many workers run at once. Use before dispatching work, when the user gives a percentage like "82%", and for "will this finish before the limit", "how much do we have left", "are we going to run out".
---

# Water

Claude Code does not show the weekly limit to a script. The user reads it and
tells you a percentage. `scripts/water.py` turns those readings into a rate,
counting the tokens in this machine's transcripts between them.

- When the user gives a reading, record it right away:
  `python3 -I scripts/water.py mark <sietch dir> <percent>`. Then save the
  sietch.
- Before dispatching, and when asked, run
  `python3 -I scripts/water.py report <sietch dir>` and give its verdict in
  one sentence. The sietch dir is what `sietch.sh open` prints.

The estimate counts only work on this machine. Cloud workers spend from the
same limit without showing up here, so while they run, ask the user for a
fresh reading before deciding anything close to the line.

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
