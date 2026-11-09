"""Estimate where the weekly limit stands and whether a track's remaining work fits.

  water.py mark SIETCH_DIR PERCENT [NOTE]   record the user's reading of the weekly limit
  water.py report SIETCH_DIR                estimate the limit now and what the rest of the track costs

Claude Code does not expose the weekly limit to a script, so this calibrates
against the readings the user gives. Between two readings it counts the tokens
in this machine's transcripts and divides by the change in percent. Work done
in cloud sessions is not in local transcripts, so the estimate is low when
cloud workers are running; a fresh reading corrects it.
"""

import csv
import datetime as dt
import glob
import json
import os
import sys

ROOTS = [os.path.expanduser(p) for p in ("~/.claude/projects", os.environ.get("NE_EXTRA_TRANSCRIPTS", "~/.claude-2/projects"))]
STOP_LINE = float(os.environ.get("NE_STOP_LINE", "90"))


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


def mark(sietch, pct, note):
    path = os.path.join(sietch, "water.tsv")
    new = not os.path.exists(path)
    with open(path, "a") as f:
        if new:
            f.write("when\tpercent\tnote\n")
        f.write(f"{now().strftime('%Y-%m-%dT%H:%M:%SZ')}\t{pct}\t{note}\n")
    print(f"Recorded {pct}%.")


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
    marks = read_marks(sietch)
    if not marks:
        print("No readings yet. Ask the user for the weekly limit percentage and run: water.py mark <sietch> <percent>")
        return
    marks.sort()
    events = list(usage_events(marks[0][0] - dt.timedelta(hours=1)))
    rates = []
    for (t1, p1), (t2, p2) in zip(marks, marks[1:]):
        if p2 > p1:
            rates.append(tokens_between(events, t1, t2) / (p2 - p1))
    last_t, last_p = marks[-1]
    since = tokens_between(events, last_t, now())
    age = (now() - last_t).total_seconds() / 3600
    print(f"Last reading: {last_p:g}% at {last_t:%Y-%m-%d %H:%M} UTC, {age:.1f} hours ago.")
    if not rates:
        print(f"Tokens on this machine since then: {since:,.0f}. One more reading after some work gives a rate.")
        return
    rate = sorted(rates)[len(rates) // 2]
    est = last_p + since / rate
    print(f"Rate: about {rate:,.0f} weighted tokens per percent, from {len(rates)} interval(s).")
    print(f"Estimate now: {est:.0f}% (local work only). Stop line: {STOP_LINE:g}%.")
    n, cost = remaining_units(sietch), unit_cost(sietch)
    if n and cost:
        need = n * cost / rate
        verdict = "fits" if est + need <= STOP_LINE else "does not fit"
        print(f"Remaining: {n} unit(s) at about {cost:,.0f} tokens each, about {need:.0f}% more: {verdict} before the stop line.")
    elif n:
        print(f"Remaining: {n} unit(s). The ledger has no token counts yet, so their cost is unknown.")


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "mark":
        mark(sys.argv[2], float(sys.argv[3].rstrip("%")), " ".join(sys.argv[4:]))
    elif len(sys.argv) == 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
