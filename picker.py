"""What a change can reach. `changed` says which files differ from a base commit (`base`: the last whole green run
in the run log, else where the branch left main), `walks` picks the walk files a set of changed files reaches on a map of the pages
(walk_map.py says what a map holds), and `unit` says whether the unit tests may be selected; both are pure, and read no
test output.
"""

from __future__ import annotations

import fnmatch
import json
import pathlib
import subprocess

from walk_map import WALKS, matches


def walks(changed, the_map: dict, every: list[str], walk_files=WALKS) -> tuple[list[str], str]:
    """(the walk files to run, the reason in one sentence). `changed` is the changed files, None when that cannot be
    told; `every` is every walk file there is. A shared file, a file the map places nowhere or None: every walk.
    Otherwise each touched area's walks, each changed walk file that still exists, and `always`, which is in every
    answer."""
    if changed is None:
        return sorted(every), "every walk: cannot tell what changed"
    shared = [name for name in changed if matches(name, the_map.get("shared", []))]
    if shared:
        return sorted(every), f"every walk: {quoted(shared)} {'is' if len(shared) == 1 else 'are'} shared"
    areas = the_map.get("areas", [])
    placing = the_map.get("none", []) + [pattern for area in areas for pattern in area.get("files", [])]
    tests = [name for name in changed if fnmatch.fnmatchcase(name, walk_files)]
    nowhere = [name for name in changed if name not in tests and not matches(name, placing)]
    if nowhere:
        return sorted(every), f"every walk: the map places {quoted(nowhere)} nowhere"
    picked, why = {walk for walk in every if matches(walk, the_map.get("always", []))}, []
    for area in areas:
        hits = [name for name in changed if matches(name, area.get("files", []))]
        if hits:
            picked.update(walk for walk in every if matches(walk, area.get("walks", [])))
            why.append(f"{area.get('name')}, because {quoted(hits)} changed")
    kept = [name for name in tests if name in every]
    if kept:
        picked.update(kept)
        why.append(f"the changed walk {'file' if len(kept) == 1 else 'files'} {quoted(kept)}")
    if why:
        return sorted(picked), "; ".join(why) + "; and the walks that always run"
    if not changed:
        return sorted(picked), "only the walks that always run: nothing changed"
    return sorted(picked), f"only the walks that always run: {quoted(changed)} reach no walk"


RECORDS = ".scratch/"


def unit(changed, apart=()) -> tuple[bool, str]:
    """(whether the unit tests may be selected by the record of which test ran which code, the reason in one sentence).
    That record sees only Python run inside the test process, so any other changed file outside the build's records,
    a changed file that matches `apart` (the Python the tests run only as a separate program; None when the map that
    lists it cannot be read), or None (cannot tell what changed), runs the whole suite."""
    if changed is None:
        return False, "the whole suite: cannot tell what changed"
    changed = [name for name in changed if not name.startswith(RECORDS)]
    other = [name for name in changed if not name.endswith(".py")]
    if other:
        return False, f"the whole suite: {quoted(other)} {'is' if len(other) == 1 else 'are'} not Python, which the record of what each test ran cannot see"
    if changed and apart is None:
        return False, "the whole suite: no map says which Python the tests run as a separate program"
    separate = [name for name in changed if matches(name, apart or [])]
    if separate:
        return False, (f"the whole suite: the tests run {quoted(separate)} as a separate program, which the record of "
                       "what each test ran cannot see")
    if not changed:
        return True, f"the tests whose code changed since their last run: no file changed outside `{RECORDS}`"
    return True, f"the tests that ran the changed Python, {quoted(changed)}"


def changed(root, main="main") -> tuple[list[str] | None, str]:
    """(the files that differ between the base and the working folder, uncommitted and untracked ones included and a
    renamed file under both names, or None when that cannot be told; the base, in words)."""
    commit, why = base(root, main)
    if commit is None:
        return None, why
    done = subprocess.run(["git", "diff", "-z", "--name-only", "--no-renames", commit], cwd=root, capture_output=True, text=True)
    if done.returncode != 0:
        return None, f"cannot tell: git could not compare the working folder with {commit[:7]}"
    new = git(root, "ls-files", "-z", "--others", "--exclude-standard")
    return sorted(set(done.stdout.split("\0") + new.split("\0")) - {""}), why


def base(root, main="main", log=".checks/runs.jsonl") -> tuple[str | None, str]:
    """(the commit changes are measured from, or None when it cannot be told; where it came from, in words).
    The last green run in the log that ran every check, on a clean folder, unpicked, at a commit this branch has;
    with none, where the branch left `main`."""
    path = pathlib.Path(root) / log
    lines = path.read_text().splitlines() if path.is_file() else []
    for line in reversed(lines):
        try:
            run = json.loads(line)
        except ValueError:
            continue
        whole = (isinstance(run, dict) and run.get("result") == "green" and run.get("every") is True
                 and run.get("dirty") is False and not run.get("picked"))
        commit = whole and git(root, "rev-parse", "--verify", "--quiet", f"{run.get('tip')}^{{commit}}")
        if commit and contains(root, commit):
            return commit, f"since the last green run of every check, at {run['tip']}"
    left = git(root, "merge-base", main, "HEAD")
    if left:
        return left, f"since where the branch left {main}, at {left[:7]} (no green run of every check in the log)"
    return None, f"cannot tell: no green run of every check on a clean folder in the log, and no {main} to compare with"


def contains(root, commit) -> bool:
    """Whether the branch checked out has the commit."""
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root, capture_output=True).returncode == 0


def git(root, *args) -> str:
    """What a git command prints, or "" when it fails."""
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def quoted(names) -> str:
    return ", ".join(f"`{name}`" for name in names)
