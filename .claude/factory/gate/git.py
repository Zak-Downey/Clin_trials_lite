"""Git, worktrees, the merge commit of a ticket, the ready stamp, and which rules a commit's gate held."""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess

from gate import MONOLITH_FILE, MONOLITH_MARKERS, RULES_FILE
from gate.config import read


def run_git(root: str, *args: str):
    try:
        result = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def find_root() -> str:
    top = run_git(os.getcwd(), "rev-parse", "--show-toplevel")
    return top or os.getcwd()


def branch_head(root: str) -> str:
    """The branch under judgement: MERGE_HEAD in a staged merge (`merge --no-commit`), else HEAD."""
    return run_git(root, "rev-parse", "-q", "--verify", "MERGE_HEAD^{commit}") or "HEAD"


def own_files(root: str, commit: str, label: str, feature):
    """What a merge commit changed of the ticket's own files in its feature: (issue file changed, follow-up review
    file changed). The diff is from the first parent, so a branch's earlier commits count as the merge's."""
    out = run_git(root, "diff", "--name-only", "%s^1" % commit, commit) or ""
    folder = re.escape(os.path.relpath(feature.dir, feature.root).replace(os.sep, "/"))  # one spelling, whatever the config wrote
    number = re.escape(label)
    issue = re.compile(r"^%s/issues/%s(?:-[^/]*)?\.md$" % (folder, number))
    review = re.compile(r"^%s/reviews/%s-followup(?:-\d+)?\.md$" % (folder, number))
    names = out.split("\n")
    return any(issue.match(n) for n in names), any(review.match(n) for n in names)


def merge_subjects(root: str, tip: str, protected, label: str, feature, pattern: str, follow_up: bool):
    """The commits on the integration line (newest first) whose subject matches `pattern` for the ticket, looking only
    at commits the protected branches do not have, and which changed the ticket's own files in `feature`
    (`owns_merge`: a first merge by its issue file, a newest one by that or its follow-up review file): another feature's `Merge ticket NN:` is not this one's."""
    exclude = ["^%s" % b for b in protected if run_git(root, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % b)]
    out = run_git(root, "log", "--first-parent", "--format=%H %s", tip, *exclude) or ""
    found = []
    for line in out.split("\n"):
        commit, _, subject = line.partition(" ")
        if re.match(pattern % re.escape(label), subject) and owns_merge(root, commit, label, feature, follow_up):
            found.append(commit)
    return found


def merge_commit_for(root: str, tip: str, label: str, feature, protected=()):
    """The ticket's first merge: the newest commit whose subject starts `Merge ticket NN:` and which changed the
    ticket's issue file in `feature`. A follow-up merge (`Merge ticket NN follow-up:`) above it does not match."""
    found = merge_subjects(root, tip, protected, label, feature, r"^Merge ticket %s:", False)
    return found[0] if found else None


def newest_merge_commit_for(root: str, tip: str, label: str, feature, protected=()):
    """The ticket's newest merge, first or follow-up: one that changed its issue file or its follow-up review file
    (a follow-up that adds no box changes only the review file)."""
    found = merge_subjects(root, tip, protected, label, feature, r"^Merge ticket %s(?: follow-up)?:", True)
    return found[0] if found else None


def owns_merge(root: str, commit: str, label: str, feature, follow_up: bool) -> bool:
    """Whether a merge commit is the ticket's own in `feature`, the test the two lookups apply."""
    issue, review = own_files(root, commit, label, feature)
    return issue or review if follow_up else issue


def integration_ref(root: str, feature_name: str):
    """The integration branch's tip: feature/<name>. None when there is no such branch (nothing to compare with)."""
    return run_git(root, "rev-parse", "--verify", "-q", "refs/heads/feature/%s^{commit}" % feature_name)


def worktree_branches(root: str) -> list:
    out = run_git(root, "worktree", "list", "--porcelain") or ""
    names = []
    for line in out.split("\n"):
        if line.startswith("branch "):
            names.append(line.split("/")[-1])
    return names


def touches_clash(a: list, b: list):
    if "*" in a or "*" in b:
        return "*"  # a ticket that runs alone clashes with every other, whatever that one touches
    for x in a:
        for y in b:
            if x == y or x.startswith(y + "/") or y.startswith(x + "/") or fnmatch.fnmatch(x, y) or fnmatch.fnmatch(y, x):
                return x if len(x) >= len(y) else y
    return None


def stamp_path(root: str):
    path = run_git(root, "rev-parse", "--git-path", "factory-ready")
    if path and not os.path.isabs(path):
        path = os.path.join(root, path)
    return path


def run_text(root: str, *args: str):
    """(exit code, output) of `git <args>` in root, or (None, '') when git cannot be run."""
    try:
        done = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=600)
    except Exception:
        return None, ""
    return done.returncode, done.stdout + done.stderr


def read_stamp(root: str):
    """(tip, names, time, built tip or None) of the ready stamp, or None."""
    path = stamp_path(root)
    if not path or not os.path.isfile(path):
        return None
    lines = read(path).split("\n") + ["", "", "", ""]
    built = lines[3].split()[1] if lines[3].startswith("built ") else None
    return lines[0].strip(), lines[1].strip(), lines[2].strip(), built


def rule_in_force(root: str, commit: str, rule: str) -> bool:
    """Whether the gate a commit shipped with held `rule`. A ticket merged before a rule existed is not judged by it.
    Reads the RULES file at that commit; a commit with none falls back to the source test on the monolith's own
    path, which is kept for the gates that were one file; a commit with neither predates every rule."""
    listed = run_git(root, "show", "%s:%s" % (commit, RULES_FILE))
    if listed is not None:
        return rule in [line.strip() for line in listed.split("\n")]
    source = run_git(root, "show", "%s:%s" % (commit, MONOLITH_FILE))
    return source is not None and rule in MONOLITH_MARKERS and MONOLITH_MARKERS[rule] in source
