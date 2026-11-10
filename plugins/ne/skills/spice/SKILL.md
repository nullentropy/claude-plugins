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
4. A release tag, named like `v1.2` or `1.2`.
5. Merge to the default branch.

If the line it detects is wrong for the repository, ask the user where
production is and write it as `harvest:` in `orders.md`. Without `gh`, the
GitHub steps are skipped.

## What counts

Only units in a ledger count. Work done outside a track does not. The script
takes each unit's latest row with a head commit and finds where that work
landed: the same commit, the merge commit of a pull request from the unit's
branch, or commits with the same patches. A unit's own commits are the ones
past where it meets the default branch and not under the head of another
unit in any track, so a unit built on another unit's branch is matched on its
own work. Patches count only when all of those commits arrived, or all of
them squashed into one. If the unit's own commits do not match, the script
tries again with the whole span, which counts a stacked unit squashed
together with the one below it. A unit that still has no match counts when a
unit stacked on it matched over its whole span, since that squash carries the
lower unit's work too. The unit
is harvested when that commit first crossed the line, and it is counted when
that time is inside the window.

The time a commit crossed is the time of the merge that brought it onto the
line. A branch line is often promoted by fast-forward, and that leaves no
commit to date the promotion by, so on a branch line the time is the later of
that merge and the first position in the branch's reflog that contains the
commit, when the reflog reaches back that far. The reflog records when this
clone saw the branch move, which can be later than when it happened.

A unit with more than 50 commits of its own was cut from another branch, so
patch matching is skipped for it. Its work counts
only through its own commit or its pull request.

## Yield

Yield is the units harvested per percent of the weekly limit spent in the same
window. The script reads the rise from the `water.tsv` readings in the window
of every track it reports. A reading more than 10 points below the highest so
far means the limit reset, and it counts as spent from zero. A smaller fall is
a correction or a rounding difference between tracks, and is ignored. With fewer than two
readings in the window there is
no figure. Ask for a reading through ne:water rather than guessing one.
