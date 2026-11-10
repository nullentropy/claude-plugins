"""Estimate where the weekly limit stands and whether a track's remaining work fits.

  water.py mark SIETCH_DIR [PERCENT] [NOTE]   record a reading of the weekly limit, the status line's when PERCENT is left out
  water.py report SIETCH_DIR                  where the limit stands now and what the rest of the track costs

Claude Code gives the weekly limit only to the status line command. When that
command keeps it in rate-limits.json in the config dir, every report records it
as a reading and reports it as the figure now. Without one, the user's readings
are all there is, and the figure now is an estimate: between two readings this
counts the tokens in this machine's transcripts and divides by the change in
percent. Cloud sessions are not in local transcripts, so that estimate is low
while cloud workers run. Either way the readings give the rate that turns a
unit's tokens into percent.
"""

import csv
import datetime as dt
import glob
import json
import os
import sys

ROOTS = [os.path.expanduser(p) for p in ("~/.claude/projects", os.environ.get("NE_EXTRA_TRANSCRIPTS", "~/.claude-2/projects"))]
STOP_LINE = float(os.environ.get("NE_STOP_LINE", "90"))
LIMITS = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "rate-limits.json")
LIVE_FOR = dt.timedelta(minutes=30)


def parse_ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def now():
    return dt.datetime.now(dt.timezone.utc)


def usage_events(since):
    """Yield (timestamp, weighted tokens) for each API request after since, once per request."""
    seen = set()
    cutoff = since.timestamp() - 3600
    for root in ROOTS:
        for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            try:
                if os.path.getmtime(path) < cutoff:
                    continue
                f = open(path, errors="replace")
            except OSError:
                continue
            with f:
                for line in f:
                    if '"usage"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                    except ValueError:
                        continue
                    msg = d.get("message") or {}
                    u = msg.get("usage")
                    ts = d.get("timestamp")
                    if not u or not ts:
                        continue
                    key = d.get("requestId") or msg.get("id") or (path, ts)
                    if key in seen:
                        continue
                    seen.add(key)
                    t = parse_ts(ts)
                    if t <= since:
                        continue
                    # Cache reads are far cheaper than fresh input, so they count for a tenth.
                    w = (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                         + u.get("output_tokens", 0) + 0.1 * u.get("cache_read_input_tokens", 0))
                    yield t, w


def tokens_between(events, a, b):
    return sum(w for t, w in events if a < t <= b)


def read_marks(sietch):
    path = os.path.join(sietch, "water.tsv")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return [(parse_ts(r["when"]), float(r["percent"])) for r in rows if r.get("when") and r.get("percent")]


def live_reading():
    """The status line's weekly figure as (when, percent, resets_at), or None when it is old or its window has reset."""
    try:
        with open(LIMITS) as f:
            d = json.load(f)
        w = d.get("seven_day") or {}
        pct, at, resets = w.get("used_percentage"), parse_ts(d["at"]), w.get("resets_at")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    if pct is None or now() - at > LIVE_FOR or (resets and float(resets) <= now().timestamp()):
        return None
    return at, float(pct), resets


def mark(sietch, pct, note, when=None, quiet=False):
    path = os.path.join(sietch, "water.tsv")
    new = not os.path.exists(path)
    with open(path, "a") as f:
        if new:
            f.write("when\tpercent\tnote\n")
        f.write(f"{(when or now()).strftime('%Y-%m-%dT%H:%M:%SZ')}\t{pct:g}\t{note}\n")
    if not quiet:
        print(f"Recorded {pct:g}%.")


def record_live(sietch, live):
    """Keep the status line's figure as a reading when it moved since the last one, so the rate calibrates itself."""
    at, pct, _ = live
    marks = sorted(read_marks(sietch))
    if marks and (marks[-1][0] >= at.replace(microsecond=0) or marks[-1][1] == pct):
        return
    mark(sietch, pct, "status line", when=at, quiet=True)


def remaining_units(sietch):
    path = os.path.join(sietch, "RESUME.md")
    if not os.path.exists(path):
        return 0
    lines = open(path).read().split("Next, in order:", 1)
    if len(lines) < 2:
        return 0
    return sum(1 for l in lines[1].splitlines() if l[:1].isdigit() and "(unit or step" not in l)


def unit_cost(sietch):
    path = os.path.join(sietch, "ledger.tsv")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        vals = []
        for r in csv.DictReader(f, delimiter="\t"):
            try:
                vals.append(float(r.get("tokens") or ""))
            except ValueError:
                pass
    return sum(vals) / len(vals) if vals else None


def report(sietch):
    live = live_reading()
    if live:
        record_live(sietch, live)
    marks = sorted(read_marks(sietch))
    if not marks:
        print("No readings yet. Ask the user for the weekly limit percentage and run: water.py mark <sietch> <percent>")
        return
    events = list(usage_events(marks[0][0] - dt.timedelta(hours=1)))
    rates = []
    for (t1, p1), (t2, p2) in zip(marks, marks[1:]):
        if p2 > p1:
            rates.append(tokens_between(events, t1, t2) / (p2 - p1))
    rate = sorted(rates)[len(rates) // 2] if rates else None
    if live:
        at, est, resets = live
        print(f"Weekly limit: {est:g}% at {at:%Y-%m-%d %H:%M} UTC, from the status line. It counts every session on the account, cloud ones too.")
        if resets:
            print(f"It resets {dt.datetime.fromtimestamp(float(resets), dt.timezone.utc):%a %Y-%m-%d %H:%M} UTC.")
    else:
        last_t, last_p = marks[-1]
        since = tokens_between(events, last_t, now())
        age = (now() - last_t).total_seconds() / 3600
        print(f"Last reading: {last_p:g}% at {last_t:%Y-%m-%d %H:%M} UTC, {age:.1f} hours ago.")
        if not rate:
            print(f"Tokens on this machine since then: {since:,.0f}. One more reading after some work gives a rate.")
            return
        est = last_p + since / rate
        print(f"Estimate now: {est:.0f}% (local work only).")
    print(f"Stop line: {STOP_LINE:g}%.")
    if rate:
        print(f"Rate: about {rate:,.0f} weighted tokens per percent, from {len(rates)} interval(s).")
    n, cost = remaining_units(sietch), unit_cost(sietch)
    if n and cost and rate:
        need = n * cost / rate
        verdict = "fits" if est + need <= STOP_LINE else "does not fit"
        print(f"Remaining: {n} unit(s) at about {cost:,.0f} tokens each, about {need:.0f}% more: {verdict} before the stop line.")
    elif n and cost:
        print(f"Remaining: {n} unit(s). Turning their tokens into percent needs two readings with work between them.")
    elif n:
        print(f"Remaining: {n} unit(s). The ledger has no token counts yet, so their cost is unknown.")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "mark":
        try:
            pct, note = float(sys.argv[3].rstrip("%")), " ".join(sys.argv[4:])
        except (IndexError, ValueError):
            live = live_reading()
            if not live:
                print("The status line has no recent weekly figure. Ask the user for one.", file=sys.stderr)
                sys.exit(1)
            mark(sys.argv[2], live[1], ("status line " + " ".join(sys.argv[3:])).strip(), when=live[0])
            return
        mark(sys.argv[2], pct, note)
    elif len(sys.argv) == 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
