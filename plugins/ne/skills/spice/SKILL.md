---
name: spice
description: Report which units of a sietch track reached production, and the yield against the weekly limit that ne:water tracks. Use for "what shipped", "what did we harvest", "what reached production this week", "was it worth the water", "yield", or to see which tracks are paying off.
---

# Spice

Water is what work costs. Spice is what it delivers: a unit counts once its
work has reached production, not when it merges. `scripts/spice.py` reads the
sietch ledgers and the repository and writes nothing.

From inside the code repository:

```
python3 -I scripts/spice.py report [TRACK] [--days N]
```

With a track, it reports that track. Without one, it reports every track in
the repository. The window is the last 7 days unless `--days` says otherwise.
Give the user the harvested units, the line used, and the yield in a few
sentences.

## The harvest line

The script takes the first of these the repository has, and says which:

1. `NE_HARVEST`, or a line `harvest: <spec>` in a track's `orders.md`, where
   the spec is `deploy:<environment>`, `branch:<name>`, `tag:<glob>` or
   `merge`.
2. A successful GitHub deployment to an environment named `production` or
   `prod`.
3. A branch on origin named `production`, `prod`, `release` or `live`.
4. A tag.
5. Merge to the default branch.

If the line it detects is wrong for the repository, ask the user where
production is and write it as `harvest:` in `orders.md`. Without `gh`, the
GitHub steps are skipped.

## What counts

Only units in a ledger count. Work done outside a track does not. The script
takes each unit's latest row with a head commit and finds where that work
landed: the same commit, the merge commit of a pull request from the unit's
branch, or commits with the same patches (a cherry-pick or a squash). The unit
is harvested when that commit first crossed the line, and it is counted when
that time is inside the window.

A unit with more than 50 commits past where it meets the default branch was
cut from another branch, so patch matching is skipped for it. Its work counts
only through its own commit or its pull request.

## Yield

Yield is the units harvested per percent of the weekly limit spent in the same
window. The script reads the rise from the `water.tsv` readings in the window
of every track it reports. With fewer than two readings in the window there is
no figure. Ask for a reading through ne:water rather than guessing one.
