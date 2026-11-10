"""Report which sietch units reached production, and what they yielded against the weekly limit.

  spice.py report [TRACK] [--days N]   harvest over the last N days (7 by default), one track or all of them

Run it from inside the code repository. It only reads: nothing in the sietch
changes.

A unit is harvested when the commit it landed as has crossed the harvest line.
The line is the first of these that the repository has:

  NE_HARVEST, or a "harvest:" line in a track's orders.md
      deploy:<environment>, branch:<name>, tag:<glob>, or merge
  a successful GitHub deployment to an environment named production or prod
  a remote branch named production, prod, release or live
  a tag
  merge to the default branch

A unit's work may reach the line as the same commit, as a pull request's
merge or squash commit, or cherry-picked; all three count.
"""

import csv
import datetime as dt
import fnmatch
import hashlib
import io
import json
import os
import re
import subprocess
import sys

PROD_ENVS = ("production", "prod")
PROD_BRANCHES = ("production", "prod", "release", "live")
# A unit with more commits than this past the branch was cut from somewhere else,
# and matching its patches would diff that branch's whole history.
MAX_UNIT_COMMITS = 50


def git(*args, ok=False):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if p.returncode != 0:
        if ok:
            return None
        raise SystemExit(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout.strip()


def gh(*args):
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def parse_ts(s):
    s = s.strip().replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s) if "T" in s or " " in s else dt.datetime.fromisoformat(s + "T00:00:00+00:00")
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def commit_time(sha):
    return parse_ts(git("show", "-s", "--format=%cI", sha))


def is_ancestor(a, b):
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], capture_output=True).returncode == 0


def resolve(rev):
    return git("rev-parse", "--verify", "--quiet", rev + "^{commit}", ok=True)


# Tracks

def state_root():
    base = os.environ.get("NE_STATE") or os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"), "ne")
    common = os.path.realpath(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    return os.path.join(base, hashlib.sha256(common.encode()).hexdigest()[:16])


def tracks(only):
    names = set()
    for ref in (git("for-each-ref", "--format=%(refname)", "refs/heads/sietch/", "refs/remotes/origin/sietch/") or "").splitlines():
        names.add(ref.split("/sietch/", 1)[1])
    if only:
        if only not in names:
            raise SystemExit(f"No track named {only}. Tracks here: {', '.join(sorted(names)) or 'none'}.")
        names = {only}
    root = os.path.join(state_root(), "sietch")
    out = {}
    for name in sorted(names):
        wt = os.path.join(root, name)

        def read(f, wt=wt, name=name):
            if os.path.exists(os.path.join(wt, ".git")):
                path = os.path.join(wt, f)
                return open(path).read() if os.path.exists(path) else ""
            for ref in (f"sietch/{name}", f"origin/sietch/{name}"):
                text = git("show", f"{ref}:{f}", ok=True)
                if text is not None:
                    return text
            return ""

        out[name] = read
    return out


def units(read):
    latest = {}
    for r in csv.DictReader(io.StringIO(read("ledger.tsv")), delimiter="\t"):
        if r.get("unit") and (r.get("head") or "").strip():
            latest[r["unit"]] = r
    return latest


def readings(read):
    rows = []
    for r in csv.DictReader(io.StringIO(read("water.tsv")), delimiter="\t"):
        try:
            rows.append((parse_ts(r["when"]), float(r["percent"])))
        except (KeyError, ValueError, TypeError):
            pass
    return rows


# The harvest line

class Line:
    def __init__(self, kind, arg, why):
        self.kind, self.arg, self.why = kind, arg, why
        self.ref = None
        self.deploys = None
        self.tags = None

    def describe(self):
        return {
            "deploy": f"a successful GitHub deployment to {self.arg}",
            "branch": f"the branch {self.arg}",
            "tag": f"a tag matching {self.arg}",
            "merge": f"merge to {self.arg}",
        }[self.kind] + f" ({self.why})"


def default_branch():
    head = git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", ok=True)
    if head:
        return head.split("/", 1)[1]
    for b in ("main", "master", "trunk"):
        if resolve(f"origin/{b}") or resolve(b):
            return b
    return git("symbolic-ref", "--short", "HEAD")


def gh_repo():
    out = gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    return out.strip() if out else None


def deployments(repo, env):
    out = gh("api", "--paginate", f"repos/{repo}/deployments?environment={env}&per_page=100")
    if out is None:
        return []
    items = []
    for chunk in re.split(r"(?<=\])\s*(?=\[)", out.strip()):
        try:
            items.extend(json.loads(chunk))
        except ValueError:
            pass
    return sorted(((parse_ts(d["created_at"]), d["sha"], d["id"]) for d in items), key=lambda x: x[0])


def detect(tracks_read):
    spec = os.environ.get("NE_HARVEST", "").strip()
    why = "NE_HARVEST"
    if not spec:
        for name, read in tracks_read.items():
            m = re.search(r"^\s*harvest:\s*(\S+)", read("orders.md"), re.M)
            if m:
                spec, why = m.group(1), f"orders.md of {name}"
                break
    if spec:
        kind, _, arg = spec.partition(":")
        if kind not in ("deploy", "branch", "tag", "merge"):
            raise SystemExit(f"Unknown harvest line {spec!r}. Use deploy:<env>, branch:<name>, tag:<glob> or merge.")
        line = Line(kind, arg or (default_branch() if kind == "merge" else "*"), why)
    else:
        line = None
        repo = gh_repo()
        if repo:
            envs = gh("api", f"repos/{repo}/environments", "-q", ".environments[].name") or ""
            for env in envs.split():
                if env.lower() in PROD_ENVS and deployments(repo, env):
                    line = Line("deploy", env, "found GitHub deployments")
                    break
        if not line:
            for b in PROD_BRANCHES:
                if resolve(f"origin/{b}"):
                    line = Line("branch", b, "found the branch on origin")
                    break
        if not line and git("tag", "--list", ok=True):
            line = Line("tag", "*", "found tags")
        if not line:
            line = Line("merge", default_branch(), "nothing else found")
    prepare(line)
    return line


def prepare(line):
    if line.kind in ("branch", "merge"):
        line.ref = resolve(f"origin/{line.arg}") or resolve(line.arg)
        if not line.ref:
            raise SystemExit(f"The harvest line {line.describe()} names a branch this clone does not have.")
    elif line.kind == "tag":
        tags = []
        for row in (git("for-each-ref", "--sort=creatordate", "--format=%(refname:short)\t%(creatordate:iso-strict)", "refs/tags/") or "").splitlines():
            name, _, when = row.partition("\t")
            if fnmatch.fnmatch(name, line.arg):
                tags.append((parse_ts(when), name))
        line.tags = tags
    elif line.kind == "deploy":
        repo = gh_repo()
        if not repo:
            raise SystemExit("The harvest line is a GitHub deployment, but gh cannot see this repository.")
        line.repo = repo
        line.deploys = deployments(repo, line.arg)
        line.status = {}


def deploy_succeeded(line, dep_id):
    if dep_id not in line.status:
        out = gh("api", f"repos/{line.repo}/deployments/{dep_id}/statuses", "-q", "[.[].state]")
        line.status[dep_id] = bool(out) and "success" in out
    return line.status[dep_id]


def crossed(line, commit):
    """When commit first reached the line, or None."""
    if line.kind in ("branch", "merge"):
        if not is_ancestor(commit, line.ref):
            return None
        path = git("rev-list", "--first-parent", "--ancestry-path", "--reverse", f"{commit}..{line.ref}").split()
        return commit_time(path[0] if path else commit)
    if line.kind == "tag":
        containing = set((git("tag", "--contains", commit, ok=True) or "").split())
        return next((t for t, name in line.tags if name in containing), None)
    made = commit_time(commit)
    for t, sha, dep_id in line.deploys:
        if t >= made and is_ancestor(commit, sha) and deploy_succeeded(line, dep_id):
            return t
    return None


# Where a unit's work landed

def landed(head, branch, targets):
    """Commits that carry the unit's work: the head itself, a pull request's merge commit, or the same patches."""
    yield head
    for sha in merged_prs().get(branch, ()):
        if resolve(sha):
            yield sha
    made = commit_time(head)
    for target in targets:
        mb = git("merge-base", head, target.ref, ok=True)
        if not mb or int(git("rev-list", "--count", f"{mb}..{head}")) > MAX_UNIT_COMMITS:
            continue
        mine = {row[0] for row in pid_of(git("log", "-p", "--no-merges", f"{mb}..{head}", ok=True))}
        whole = pid_of(git("diff", mb, head, ok=True))
        whole = whole[0][0] if whole else None
        hits = [(t, sha) for t, sha, pid in target.commits(made) if pid == whole or pid in mine]
        if hits:
            yield max(hits)[1]


_merged = None


def merged_prs():
    """Merge commits of merged pull requests by head branch, from one gh call."""
    global _merged
    if _merged is None:
        _merged = {}
        out = gh("pr", "list", "--state", "merged", "--limit", "1000", "--json", "headRefName,mergeCommit",
                 "-q", '.[] | select(.mergeCommit) | "\\(.headRefName) \\(.mergeCommit.oid)"')
        for row in (out or "").splitlines():
            b, _, sha = row.partition(" ")
            _merged.setdefault(b, []).append(sha)
    return _merged


def pid_of(text):
    p = subprocess.run(["git", "patch-id", "--stable"], input=text or "", capture_output=True, text=True)
    return [row.split() for row in p.stdout.splitlines() if row]


class Target:
    """A branch's commits with their patch ids, read once from the earliest time any unit asks for."""

    def __init__(self, ref, since):
        self.ref = ref
        when = f"--since={since.isoformat()}"
        times = {}
        for row in (git("log", "--no-merges", "--format=%H %cI", when, ref, ok=True) or "").splitlines():
            sha, t = row.split()
            times[sha] = parse_ts(t)
        log = git("log", "-p", "--no-merges", when, ref, ok=True)
        self.all = [(times[sha], sha, pid) for pid, sha in pid_of(log) if sha in times]

    def commits(self, since):
        return [c for c in self.all if c[0] >= since]


def harvest_time(line, targets, r):
    head = resolve(r["head"].strip())
    if not head:
        return None, "head not in this clone"
    seen = set()
    for c in landed(head, (r.get("branch") or "").strip(), targets):
        if c in seen:
            continue
        seen.add(c)
        t = crossed(line, c)
        if t:
            return t, None
    return None, None


def rise(rows, start):
    rows = sorted(r for r in rows if r[0] >= start)
    return sum(max(0.0, b - a) for (_, a), (_, b) in zip(rows, rows[1:])), len(rows)


def report(only, days):
    git("fetch", "-q", "--tags", "origin", ok=True)
    tr = tracks(only)
    if not tr:
        print("No tracks in this repository. spice counts sietch units only.")
        return
    line = detect(tr)
    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    print(f"Harvest line: {line.describe()}.")
    print(f"Window: the last {days:g} days, since {start:%Y-%m-%d %H:%M} UTC.")
    all_units = {name: units(read) for name, read in tr.items()}
    heads = [resolve(r["head"].strip()) for us in all_units.values() for r in us.values()]
    made = [commit_time(h) for h in heads if h]
    targets = []
    if made:
        refs = [resolve(f"origin/{default_branch()}") or resolve(default_branch()), line.ref]
        targets = [Target(ref, min(made)) for ref in dict.fromkeys(filter(None, refs))]
    total, waiting, missing, water = 0, 0, 0, []
    for name, read in tr.items():
        got = []
        for unit, r in all_units[name].items():
            t, problem = harvest_time(line, targets, r)
            if problem:
                missing += 1
            elif t is None:
                waiting += 1
            elif t >= start:
                got.append((t, unit))
        water.extend(readings(read))
        if got or only:
            print(f"\n{name}: {len(got)} unit(s) harvested")
            for t, unit in sorted(got):
                print(f"  {t:%Y-%m-%d}  {unit}")
        total += len(got)
    print(f"\nHarvested: {total} unit(s). Not past the line yet: {waiting}.", end="")
    print(f" Heads missing from this clone: {missing}." if missing else "")
    used, n = rise(water, start)
    if n < 2 or used <= 0:
        print("Yield: no figure. It needs two weekly-limit readings in the window (ne:water).")
    else:
        print(f"Water spent in the window: {used:g}% of the weekly limit, from {n} readings.")
        print(f"Yield: {total / used:.2f} unit(s) per percent.")


def main():
    args = sys.argv[1:]
    if not args or args[0] != "report":
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(1)
    days, rest = 7.0, []
    it = iter(args[1:])
    for a in it:
        if a == "--days":
            days = float(next(it, "7"))
        else:
            rest.append(a)
    report(rest[0] if rest else None, days)


if __name__ == "__main__":
    main()
