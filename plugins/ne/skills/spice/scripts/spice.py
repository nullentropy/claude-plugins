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
  a release tag, named like v1.2 or 1.2
  merge to the default branch

A unit's work may reach the line as the same commit, as a pull request's
merge or squash commit, or cherry-picked; all three count. Patches count only
when every one of the unit's commits arrived, or their sum as one squash.
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
RELEASE_TAGS = None
# A smaller fall in the readings is a correction or rounding between tracks; a larger one is the weekly reset.
RESET_DROP = 10.0


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
            "tag": "a release tag, named like v1.2 or 1.2" if self.arg is RELEASE_TAGS else f"a tag matching {self.arg}",
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


_deployments = {}


def deployments(repo, env):
    if (repo, env) not in _deployments:
        out = gh("api", "--paginate", f"repos/{repo}/deployments?environment={env}&per_page=100") or ""
        items = []
        for chunk in re.split(r"(?<=\])\s*(?=\[)", out.strip()):
            try:
                items.extend(json.loads(chunk))
            except ValueError:
                pass
        _deployments[(repo, env)] = sorted(((parse_ts(d["created_at"]), d["sha"], d["id"]) for d in items), key=lambda x: x[0])
    return _deployments[(repo, env)]


_statuses = {}


def deploy_succeeded(repo, dep_id):
    if dep_id not in _statuses:
        out = gh("api", f"repos/{repo}/deployments/{dep_id}/statuses", "-q", "[.[].state]")
        _statuses[dep_id] = bool(out) and "success" in out
    return _statuses[dep_id]


def tag_matches(name, glob):
    if glob is RELEASE_TAGS:
        return re.fullmatch(r"v?\d+(\.\d+)+", name) is not None
    return fnmatch.fnmatch(name, glob)


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
            envs = gh("api", "--paginate", f"repos/{repo}/environments?per_page=100", "-q", ".environments[].name") or ""
            for env in envs.split():
                recent = deployments(repo, env)[-10:] if env.lower() in PROD_ENVS else []
                if any(deploy_succeeded(repo, dep_id) for _, _, dep_id in reversed(recent)):
                    line = Line("deploy", env, "found successful GitHub deployments")
                    break
        if not line:
            for b in PROD_BRANCHES:
                if resolve(f"origin/{b}"):
                    line = Line("branch", b, "found the branch on origin")
                    break
        if not line and any(tag_matches(t, RELEASE_TAGS) for t in (git("tag", "--list", ok=True) or "").split()):
            line = Line("tag", RELEASE_TAGS, "found release tags")
        if not line:
            line = Line("merge", default_branch(), "nothing else found")
    prepare(line)
    return line


def prepare(line):
    if line.kind in ("branch", "merge"):
        line.refname = f"refs/remotes/origin/{line.arg}" if resolve(f"origin/{line.arg}") else f"refs/heads/{line.arg}"
        line.ref = resolve(line.refname)
        if not line.ref:
            raise SystemExit(f"The harvest line {line.describe()} names a branch this clone does not have.")
    elif line.kind == "tag":
        tags = []
        for row in (git("for-each-ref", "--sort=creatordate", "--format=%(refname:short)\t%(creatordate:iso-strict)", "refs/tags/") or "").splitlines():
            name, _, when = row.partition("\t")
            if tag_matches(name, line.arg):
                tags.append((parse_ts(when), name))
        line.tags = tags
    elif line.kind == "deploy":
        repo = gh_repo()
        if not repo:
            raise SystemExit("The harvest line is a GitHub deployment, but gh cannot see this repository.")
        line.repo = repo
        line.deploys = deployments(repo, line.arg)


def crossed(line, commit):
    """When commit first reached the line, or None."""
    if line.kind in ("branch", "merge"):
        if not is_ancestor(commit, line.ref):
            return None
        path = git("rev-list", "--first-parent", "--ancestry-path", "--reverse", f"{commit}..{line.ref}").split()
        # rev-list leaves commit itself out, so when commit is on the first-parent chain, path[0] is the commit after it.
        merged = commit_time(path[0] if path and git("rev-parse", f"{path[0]}^1", ok=True) != commit else commit)
        if line.kind == "branch":
            # A promotion by fast-forward, of the commit or of the merge that carries it, is dated only by when this
            # clone saw the branch move, so the crossing is the later of the two.
            moved = reflog(line.refname)
            if moved and not is_ancestor(commit, moved[0][1]):
                return max(merged, next(t for t, sha in moved if is_ancestor(commit, sha)))
        return merged
    if line.kind == "tag":
        containing = set((git("tag", "--contains", commit, ok=True) or "").split())
        return next((t for t, name in line.tags if name in containing), None)
    made = commit_time(commit)
    for t, sha, dep_id in line.deploys:
        if t >= made and is_ancestor(commit, sha) and deploy_succeeded(line.repo, dep_id):
            return t
    return None


_reflogs = {}


def reflog(refname):
    """(time, sha) for each position the ref has held in this clone, oldest first."""
    if refname not in _reflogs:
        rows = []
        for row in (git("log", "-g", "--date=iso-strict", "--format=%H %gd", refname, ok=True) or "").splitlines():
            sha, _, sel = row.partition(" ")
            m = re.search(r"@\{(.+)\}", sel)
            if m:
                rows.append((parse_ts(m.group(1)), sha))
        _reflogs[refname] = rows[::-1]
    return _reflogs[refname]


# Where a unit's work landed

def landed(head, branch, targets, others):
    """Commits that carry the unit's work: the head itself, a pull request's merge commit, or the same patches."""
    yield head
    for sha in merged_prs().get(branch, ()):
        if resolve(sha):
            yield sha
    made = commit_time(head)
    for target in targets:
        mb = git("merge-base", head, target.ref, ok=True)
        if not mb:
            continue
        # Commits under another unit's head belong to that unit, so a unit stacked on it is matched on its own work.
        span = span_of(head, target)
        below = [h for h in others if h != head and h in span]
        # Stacked units may ship one at a time or squashed together, so try the unit's own commits and then the whole span.
        hit = (below and patch_match(head, [mb, *below], target, made)) or whole_match(head, target)
        if not hit and len(span) <= MAX_UNIT_COMMITS:
            # A unit squashed together with one stacked on it shipped in that unit's squash.
            hit = next((h for h in (whole_match(a, target) for a in others if a != head and head in span_of(a, target)) if h), None)
        if hit:
            yield hit


_spans = {}


def span_of(head, target):
    """The commits on head since it left the target branch."""
    if (head, target.ref) not in _spans:
        mb = git("merge-base", head, target.ref, ok=True)
        _spans[(head, target.ref)] = set(git("rev-list", f"{mb}..{head}").split()) if mb else set()
    return _spans[(head, target.ref)]


_wholes = {}


def whole_match(head, target):
    """Where everything on head since it left the target branch landed, matched by patches."""
    if (head, target.ref) not in _wholes:
        mb = git("merge-base", head, target.ref, ok=True)
        _wholes[(head, target.ref)] = mb and patch_match(head, [mb], target, commit_time(head))
    return _wholes[(head, target.ref)]


def patch_match(head, stop, target, made):
    own = git("rev-list", "--reverse", "--no-merges", head, "--not", *stop).split()
    if not own or len(own) > MAX_UNIT_COMMITS:
        return None
    mine = {row[0] for row in pid_of(git("log", "-p", "--no-merges", head, "--not", *stop, ok=True))}
    whole = pid_of(git("diff", f"{own[0]}^", head, ok=True))
    whole = whole[0][0] if whole else None
    found = {pid: (t, sha) for t, sha, pid in target.commits(made) if pid == whole or pid in mine}
    if whole in found:
        return found[whole][1]
    if mine and mine <= found.keys():
        return max(found[p] for p in mine)[1]
    return None


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
    """A branch's commits with their patch ids, read on first use from the earliest time any unit could need."""

    def __init__(self, ref, since, first_parent=False):
        self.ref, self.since, self.first_parent = ref, since, first_parent
        self.all = None

    def commits(self, since):
        if self.all is None:
            args = ["--no-merges", f"--since={self.since.isoformat()}"] + (["--first-parent"] if self.first_parent else [])
            times = {}
            for row in (git("log", *args, "--format=%H %cI", self.ref, ok=True) or "").splitlines():
                sha, t = row.split()
                times[sha] = parse_ts(t)
            log = git("log", "-p", *args, self.ref, ok=True)
            self.all = [(times[sha], sha, pid) for pid, sha in pid_of(log) if sha in times]
        return [c for c in self.all if c[0] >= since]


def harvest_time(line, targets, r, others):
    head = resolve(r["head"].strip())
    if not head:
        return None, "head not in this clone"
    seen = set()
    for c in landed(head, (r.get("branch") or "").strip(), targets, others):
        if c in seen:
            continue
        seen.add(c)
        t = crossed(line, c)
        if t:
            return t, None
    return None, None


def rise(rows, start):
    """Percent spent across the readings. After a reset, the new reading was spent from zero."""
    rows = sorted((r for r in rows if r[0] >= start), key=lambda r: r[0])
    if not rows:
        return 0.0, 0
    spent, level = 0.0, rows[0][1]
    for _, p in rows[1:]:
        if p < level - RESET_DROP:
            spent, level = spent + p, p
        elif p > level:
            spent, level = spent + p - level, p
    return spent, len(rows)


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
    heads = {resolve(r["head"].strip()) for us in all_units.values() for r in us.values()} - {None}
    made = [commit_time(h) for h in heads]
    # A unit can be stacked on one from another track, so every track's heads mark where units begin.
    every = tracks(None) if only else tr
    others = {resolve(r["head"].strip()) for read in every.values() for r in units(read).values()} - {None}
    targets = []
    if made:
        base = resolve(f"origin/{default_branch()}") or resolve(default_branch())
        targets = [Target(base, min(made))]
        if line.ref and line.ref != base:
            # Its merges from the default branch are already read through base; only commits made on it directly are new.
            targets.append(Target(line.ref, min(made), first_parent=True))
    total, waiting, missing, water = 0, 0, 0, []
    for name, read in tr.items():
        got = []
        for unit, r in all_units[name].items():
            t, problem = harvest_time(line, targets, r, others)
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
    if n < 2:
        print("Yield: no figure. It needs two weekly-limit readings in the window (ne:water).")
    elif used <= 0:
        print(f"Yield: no figure. The {n} readings in the window show no water spent.")
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
