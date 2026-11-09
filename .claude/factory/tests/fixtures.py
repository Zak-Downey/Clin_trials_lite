"""Shared fixtures for the gate tests: a throwaway repository with a tracker, and the gate run in it."""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY = os.path.dirname(HERE)
GATE = os.path.join(FACTORY, "gate.py")
sys.path.insert(0, FACTORY)  # the tests import the gate package from the folder they sit in

TICKET = """# {n}: Ticket {n}

**What to build:** something.

**Blocked by:** {blocked}

**Status:** {status}
{touches}
{boxes}

## Comments

- [ ] a box under Comments is not an acceptance box
"""

GOOD_BOXES = """- [x] Saves the record — test: saves the record and reads it back
- [x] The form opens above the map — walk: 01 the form is on top; shot: shots/01.png
- [ ] Wording reads well — needs-human: judge the Not saved wording on shots/02.png"""

# A hook runs with GIT_DIR and friends set; the fixtures must not follow them into another repository.
CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@example.com"] + list(args),
                   check=True, capture_output=True, env=CLEAN_ENV)


class Repo:
    def __init__(self, checks=None, legacy=False, forbid=None, test_dirs=None, extra=None, tracker=".scratch"):
        self.tracker = tracker
        self.root = tempfile.mkdtemp(prefix="gate-test-")
        atexit.register(shutil.rmtree, self.root, True)
        git(self.root, "init", "-q", "-b", "feature/x")
        self.write("docs/agents/local/factory.json", json.dumps({
            "tracker": tracker,
            "checks": [{"name": "unit", "command": "true"}] if checks is None else checks,
            "evidence": {"test": test_dirs or ["test"], "walk": ["walks"]},
            "forbid": forbid or [],
            "legacy_features": ["feat"] if legacy else [],
            **(extra or {}),
        }))
        self.write(tracker + "/feat/spec.md", "# Feat\n")
        self.write("test/a.test.js", "test('saves the record and reads it back', () => {});\n")
        self.write("walks/01.walk.js", "walk('01 the form is on top of the map', async () => {});\n")
        self.write("docs/agents/local/repo.md", "# Repo\n\n## Stand-ins\n\n| Stand-in | Replaces | Fidelity check | Last checked |\n|---|---|---|---|\n| stub.js | The real feed | none yet | never |\n| Node | The browser | walks | each run |\n")

    def write(self, path, text):
        full = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(text)

    def ticket(self, n, status="done", blocked="None (can start immediately)", boxes=GOOD_BOXES, touches="", slug="thing", kind=""):
        line = ("\n**Kind:** %s\n" % kind if kind else "") + ("\n**Touches:** %s\n" % touches if touches else "")
        self.write("%s/feat/issues/%s-%s.md" % (self.tracker, n, slug), TICKET.format(n=n, status=status, blocked=blocked, boxes=boxes, touches=line))

    def commit(self):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "state")

    def head(self):
        return subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.strip()

    def review(self, blocking=(), notes=(), tip=None, label="01"):
        lines = ["# Review: ticket %s" % label, "Tip reviewed: %s." % (tip or self.head()[:7]), "## Blocking"]
        lines += ["%d. %s" % (i, f) for i, f in enumerate(blocking, 1)]
        lines += ["## Notes"] + ["%d. %s" % (i, f) for i, f in enumerate(notes, 1)]
        lines += ["## Not checked", "Nothing."]
        self.write("%s/feat/reviews/%s.md" % (self.tracker, label), "\n".join(lines) + "\n")

    def gate_at(self, cwd, *args):
        return gate_in(cwd, *args)

    def gate(self, *args):
        result = subprocess.run([sys.executable, GATE] + list(args), cwd=self.root, capture_output=True, text=True, env=CLEAN_ENV)
        return result.returncode, result.stdout + result.stderr


NEW = "brand new check"

RED12 = ".scratch/feat/red/01-unit-run.txt"


def merged_repo(status, audit=None, red=True, noise=(), extra=None, rules=None):
    """feature/feat with ticket 01's branch merged (--no-ff, subject `Merge ticket 01: ...`) and the ticket's Status as given."""
    repo = Repo(extra=extra)
    boxes = "- [x] Does the new thing \u2014 test: %s%s; doc: docs/a.md#gate-py-red" % (NEW, "; red: " + RED12 if red else "")
    repo.ticket("01", status="ready-for-agent", boxes=boxes)
    repo.write("docs/a.md", "# A\n")
    if audit is not None:
        repo.write(".claude/factory/gate.py", audit)
    if rules is not None:
        repo.write(".claude/factory/RULES", rules)
    repo.commit()
    git(repo.root, "checkout", "-q", "-b", "feature/feat")
    git(repo.root, "checkout", "-q", "-b", "ticket/01")
    repo.write("src/work.js", "work\n")
    repo.ticket("01", status="ready-for-agent", boxes=boxes, touches="src/work.js")  # the branch changes its own issue file
    repo.commit()
    before = repo.head()
    repo.write("test/new.test.js", "test('%s', () => {});\n" % NEW)
    repo.write("docs/a.md", "# A\n\n## gate.py red\n")
    repo.commit()
    repo.write(RED12, "# tip %s\nnot ok 1 - %s\n" % (before[:7], NEW))
    repo.commit()
    git(repo.root, "checkout", "-q", "feature/feat")
    git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01: the new thing", "ticket/01")
    for kind in noise:
        if kind == "later-merge":  # a later merge whose subject starts `Merge ticket 01 ` without the colon
            git(repo.root, "checkout", "-q", "-b", "ticket/01-fixes")
            repo.write("src/fix.js", "fix\n")
            repo.commit()
            git(repo.root, "checkout", "-q", "feature/feat")
            git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01 foundation fixes: tidy", "ticket/01-fixes")
        if kind == "side-commit":  # a commit on another ticket's branch whose subject imitates the merge's
            git(repo.root, "checkout", "-q", "-b", "ticket/02")
            repo.write("src/two.js", "two\n")
            repo.commit()
            # dated later than the real merge, so only the first-parent walk keeps it out of the way
            subprocess.run(["git", "-C", repo.root, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty",
                            "-m", "Merge ticket 01: noise on a side branch"], check=True, capture_output=True,
                           env=dict(CLEAN_ENV, GIT_COMMITTER_DATE="2099-01-01T00:00:00", GIT_AUTHOR_DATE="2099-01-01T00:00:00"))
            git(repo.root, "checkout", "-q", "feature/feat")
            git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 02: other", "ticket/02")
    if status == "done":
        repo.ticket("01", status="done", boxes=boxes)
        repo.commit()
    return repo


FOLLOW_UP_CHECK = "second brand new check"
FOLLOW_UP_RED = ".scratch/feat/red/01-unit-second.txt"
FOLLOW_UP_RULES = "red-audit\nfollow-up\n"


def follow_up_branch(cite_red=True, rules=FOLLOW_UP_RULES):
    """merged_repo('done') plus branch ticket/01-fixes cut from the integration tip: a new test, a red run made before
    it passed, and a new ticked box citing both. The repo is left on feature/feat; nothing is merged."""
    repo = merged_repo("done", rules=rules)
    git(repo.root, "checkout", "-q", "-b", "ticket/01-fixes")
    before = repo.head()
    repo.write("test/second.test.js", "test('%s', () => {});\n" % FOLLOW_UP_CHECK)
    repo.commit()
    repo.write(FOLLOW_UP_RED, "# tip %s\nnot ok 1 - %s\n" % (before[:7], FOLLOW_UP_CHECK))
    with open(os.path.join(repo.root, ".scratch/feat/issues/01-thing.md"), encoding="utf-8") as handle:
        text = handle.read()
    box = "- [x] Does the second thing \u2014 test: %s%s\n" % (FOLLOW_UP_CHECK, "; red: " + FOLLOW_UP_RED if cite_red else "")
    repo.write(".scratch/feat/issues/01-thing.md", text.replace("\n## Comments", box + "\n## Comments", 1))
    repo.commit()
    git(repo.root, "checkout", "-q", "feature/feat")
    return repo


def two_feature_line():
    """merged_repo('done') with, above ticket 01's merge on feature/feat, feature `feat-review`'s own
    `Merge ticket 01:` (a name a prefix match on the folder would also take). Returns (repo, feat's merge, feat-review's merge)."""
    repo = merged_repo("done", rules=FOLLOW_UP_RULES)
    mine = subprocess.run(["git", "-C", repo.root, "log", "--format=%H", "--grep=^Merge ticket 01:"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.split()[0]
    repo.write(".scratch/feat-review/spec.md", "# Feat review\n")
    repo.write(".scratch/feat-review/issues/01-other.md", TICKET.format(n="01", status="ready-for-agent", blocked="None", boxes="- [ ] x \u2014 needs-human: y", touches=""))
    repo.commit()
    git(repo.root, "checkout", "-q", "-b", "ticket/01-other")
    repo.write(".scratch/feat-review/issues/01-other.md", TICKET.format(n="01", status="done", blocked="None", boxes="- [ ] x \u2014 needs-human: y", touches=""))
    repo.commit()
    git(repo.root, "checkout", "-q", "feature/feat")
    git(repo.root, "merge", "-q", "--no-ff", "-m", "Merge ticket 01: the review feature's ticket", "ticket/01-other")
    return repo, mine, repo.head()


def linked_worktree(repo, branch):
    """A linked worktree of repo on branch, removed at exit."""
    wt = tempfile.mkdtemp(prefix="gate-wt-")
    atexit.register(shutil.rmtree, wt, True)
    shutil.rmtree(wt)
    git(repo.root, "worktree", "add", "-q", wt, branch)
    return wt


def gate_in(cwd, *args):
    """(exit code, output) of the gate run with cwd as the working directory."""
    result = subprocess.run([sys.executable, GATE] + list(args), cwd=cwd, capture_output=True, text=True, env=CLEAN_ENV)
    return result.returncode, result.stdout + result.stderr


class Place:
    """One state the gate is run in during a build: a name and the working directory to run it from."""

    def __init__(self, name, root, merged):
        self.name, self.root, self.merged = name, root, merged

    def gate(self, *args):
        return gate_in(self.root, *args)

    def stamp(self, text):
        """Write the ready stamp this checkout's git would read (`git rev-parse --git-path factory-ready`)."""
        path = subprocess.run(["git", "-C", self.root, "rev-parse", "--git-path", "factory-ready"], check=True, capture_output=True,
                              text=True, env=CLEAN_ENV).stdout.strip()
        with open(os.path.join(self.root, path), "w", encoding="utf-8") as handle:
            handle.write(text)


PLACE_NAMES = ("branch", "staged merge", "integration tip", "worktree", "main with another stamp")


def places(missing_red=False, rename_heading=False, bad_evidence=False):
    """A feature with one ticket (01) whose branch changed code, a test, a doc heading and a red run, shown in
    the five states the gate is run in: the branch in its checkout; a staged, uncommitted merge of it in the
    integration checkout; the integration tip after `Merge ticket 01:` landed; a linked ticket worktree; the main
    checkout with another feature's ready stamp. `missing_red` cites a red run made at a commit the branch lacks;
    `bad_evidence` adds a second ticked box citing a test nobody wrote; `rename_heading` renames the doc heading after the merge (so only the post-merge places have it)."""
    repo = Repo()
    boxes = "- [x] Does the new thing — test: %s; red: %s; doc: docs/a.md#gate-py-red" % (NEW, RED12)
    if bad_evidence:
        boxes += "\n- [x] Cites nothing real \u2014 test: a title nobody wrote"
    repo.ticket("01", status="ready-for-agent", boxes=boxes)
    repo.write("docs/a.md", "# A\n")
    repo.write(".claude/factory/RULES", "red-audit\n")  # the gate the ticket merged with held the red audit
    repo.commit()
    git(repo.root, "checkout", "-q", "-b", "feature/feat")
    git(repo.root, "checkout", "-q", "-b", "side")
    repo.write("src/side.js", "side\n")
    repo.commit()
    side = repo.head()
    git(repo.root, "checkout", "-q", "feature/feat")
    git(repo.root, "checkout", "-q", "-b", "ticket/01")
    repo.write("src/work.js", "work\n")
    repo.ticket("01", status="ready-for-agent", boxes=boxes, touches="src/work.js")  # the branch changes its own issue file
    repo.commit()
    before = repo.head()
    repo.write("test/new.test.js", "test('%s', () => {});\n" % NEW)
    repo.write("docs/a.md", "# A\n\n## gate.py red\n")
    repo.commit()
    repo.write(RED12, "# tip %s\nnot ok 1 - %s\n" % ((side if missing_red else before)[:7], NEW))
    repo.commit()
    git(repo.root, "checkout", "-q", "feature/feat")
    repo.write("other.txt", "another ticket merged meanwhile\n")
    repo.commit()

    def copy(name):
        root = tempfile.mkdtemp(prefix="gate-place-")
        atexit.register(shutil.rmtree, root, True)
        shutil.rmtree(root)
        shutil.copytree(repo.root, root, symlinks=True)
        return root

    def land(root):
        git(root, "merge", "-q", "--no-ff", "--no-commit", "ticket/01")
        Repo.ticket(_At(root), "01", status="done", boxes=boxes)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "Merge ticket 01: the new thing")
        if rename_heading:
            _At(root).write("docs/a.md", "# A\n\n## The red-run gate\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "rename the heading")

    found = {}
    root = copy("branch")
    git(root, "checkout", "-q", "ticket/01")
    found["branch"] = Place("branch", root, False)
    root = copy("staged merge")
    git(root, "merge", "-q", "--no-ff", "--no-commit", "ticket/01")
    found["staged merge"] = Place("staged merge", root, False)
    root = copy("integration tip")
    land(root)
    found["integration tip"] = Place("integration tip", root, True)
    root = copy("worktree")
    wt = tempfile.mkdtemp(prefix="gate-wt-")
    atexit.register(shutil.rmtree, wt, True)
    shutil.rmtree(wt)
    git(root, "worktree", "add", "-q", wt, "ticket/01")
    found["worktree"] = Place("worktree", wt, False)
    found["worktree"].main = root  # the checkout it hangs from, which holds another feature's stamp
    with open(os.path.join(root, ".git", "factory-ready"), "w", encoding="utf-8") as handle:
        handle.write("%s\nother-feature\n2026-11-07T10:00:00\n" % ("0" * 40))
    root = copy("main with another stamp")
    land(root)
    stamped = Place("main with another stamp", root, True)
    stamped.stamp("%s\nother-feature\n2026-11-07T10:00:00\n" % subprocess.run(
        ["git", "-C", root, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, env=CLEAN_ENV).stdout.strip())
    found["main with another stamp"] = stamped
    return [found[n] for n in PLACE_NAMES]


class _At:
    """Just enough of Repo (write, ticket) for a directory that is a copy of one."""

    tracker = ".scratch"

    def __init__(self, root):
        self.root = root

    write = Repo.write
