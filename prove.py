"""Proof that the checks can fail: small deliberate breaks, each of which a named test or check must notice.

The list is docs/agents/local/breaks.json: entries with an `id`, the `file` to change, the text to
`find` (exactly once in that file), the text to `replace` it with, a `why` in one sentence, and what
proves it: `test` (one pytest test, by its id) or `check` (the name of a check in CHECKS), never both.

    python3 prove.py           prove every break; by hand only, never one of the checks
    python3 prove.py --pick    prove that picking hides no break: each break proved by a test is made, and
                               `checks.py --quick --pick <its check>` (unit or walks) must go red in place of the test

A list with a fault stops it before anything runs. Each break is made in a fresh copy of the files
git tracks, as they are on disk, in a temporary folder whose `.venv` is a link to this one's; the
working folder is never touched. Its test or check runs unbroken (it must be green) and broken (it
must be red: pytest's exit code 1, a test that ran and failed, or `checks.py <name>` ending 1).
Each break is caught, stayed green, red before the change, or could not run (stopped at its time
limit, or ended some other way). Each run has a limit of two minutes and nothing it starts outlives
it. Exit 0 only when every break was caught and the list is not empty. One line per run is appended
to .checks/proof.jsonl.

With --pick, the copy also carries what the picker reads in the working folder: git's history (a clone that shares
this repo's objects, so the base commit is there), the run log (.checks/runs.jsonl, whose last green run of every
check is the base) and the unit record (.testmondata*). Its unbroken run is the named test; its broken run is the
picked check, which must end 1. Each line says how many the pick ran of how many there are: a break whose pick ran
everything is "caught, but nothing was picked", and one whose pick stayed green is "hidden". A pick of everything
stopped at the time limit is "could not run, but nothing was picked" and does not make the proof red: nothing was
picked, so picking hid nothing, and the plain proof says whether the test catches it. Exit 0 only when no break was
hidden, stopped in a smaller pick, red before the change or otherwise not run. Breaks proved by a check are left to the
plain proof. Its log line carries "picked": true.
"""

from __future__ import annotations

import ast
import datetime
import functools
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile

import checks

BREAKS = "docs/agents/local/breaks.json"
FIELDS = ("id", "file", "find", "replace", "why")


def list_problems(breaks, root, check_names=None) -> list[str]:
    """`<id>: <fault>` for everything wrong with a list of breaks over the repo at `root`: a field
    missing, both or neither of test and check, a repeated id, a file that does not exist, find text
    absent or there more than once, find and replace the same, a test or check that does not exist.
    The checks are the names in `check_names`, by default the ones checks.py runs."""
    names = [name for name, *_ in checks.CHECKS] if check_names is None else list(check_names)
    problems, seen = [], set()
    for number, item in enumerate(breaks, start=1):
        faults = [f"has no {field}" for field in FIELDS
                  if not isinstance(item.get(field), str) or (field != "replace" and not item[field])]
        if "test" in item and "check" in item:
            faults.append("names both a test and a check; it takes one")
        elif "test" in item:
            faults += named_test_problems(str(item["test"]), root)
        elif "check" in item:
            if item["check"] not in names:
                faults.append(f"{item['check']} is not one of the checks ({', '.join(names)})")
        else:
            faults.append("names neither a test nor a check")
        if item.get("id") and item["id"] in seen:
            faults.append("the id is used more than once")
        seen.add(item.get("id"))
        faults += text_problems(item, root)
        problems += [f"{item.get('id') or f'entry {number}'}: {fault}" for fault in faults]
    return problems


def text_problems(item, root) -> list[str]:
    """The entry's file is missing, its find text is not there exactly once, or the change changes nothing."""
    file, find = item.get("file"), item.get("find")
    if not isinstance(file, str) or not file or not isinstance(find, str) or not find:
        return []
    path = pathlib.Path(root) / file
    if not path.is_file():
        return [f"{file} does not exist"]
    faults = []
    count = path.read_text(encoding="utf-8").count(find)
    if count == 0:
        faults.append(f"the find text is not in {file}")
    elif count > 1:
        faults.append(f"the find text occurs {count} times in {file}; it must occur once")
    if find == item.get("replace"):
        faults.append("find and replace are the same, so nothing breaks")
    return faults


def named_test_problems(test, root) -> list[str]:
    """The pytest id `<file>::<test>` (or `<file>::<Class>::<test>`, with any `[parameters]`) names
    a file that is not there or a test function it does not define."""
    file, _, name = test.partition("::")
    if not name:
        return ["the test is not one test, written <file>::<test>"]
    path = pathlib.Path(root) / file
    if not path.is_file():
        return [f"the test file {file} does not exist"]
    *classes, function = name.split("[")[0].split("::")
    body = ast.parse(path.read_text(encoding="utf-8")).body
    for cls in classes:
        body = next((node.body for node in body if isinstance(node, ast.ClassDef) and node.name == cls), [])
    if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function for node in body):
        return [f"{file} has no test {name.split('[')[0]}"]
    return []


GRACE_SECONDS = 10


def copy_of(root, into) -> pathlib.Path:
    """The files git tracks in `root`, as they are on disk, copied into `into`, with `.venv` a link to root's."""
    root, copy = pathlib.Path(root), pathlib.Path(into) / "copy"
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=True)
    for name in filter(None, listed.stdout.split("\0")):
        source = root / name
        if source.is_file() or source.is_symlink():
            (copy / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, copy / name, follow_symlinks=False)
    copy.mkdir(exist_ok=True)
    if (root / ".venv").exists():
        (copy / ".venv").symlink_to((root / ".venv").resolve())
    return copy


RECORD = ".testmondata*"
RUN_LOG = ".checks/runs.jsonl"


def copy_for_pick(root, into) -> pathlib.Path:
    """A copy of root as copy_of makes it, that is also a git clone sharing root's objects (with root's branches, so
    `main` is there), and that carries root's run log and unit record: the picker then picks in it as it would in
    root, and a break made in it is the only change since that pick's base, when root is clean at it."""
    root, copy = pathlib.Path(root), pathlib.Path(into) / "copy"
    quiet = {"cwd": copy, "capture_output": True, "check": True}
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", str(root), str(copy)], capture_output=True, check=True)
    subprocess.run(["git", "fetch", "-q", "--update-head-ok", "origin", "+refs/heads/*:refs/heads/*"], **quiet)
    subprocess.run(["git", "reset", "-q"], **quiet)
    copy_of(root, into)
    (copy / ".checks").mkdir(exist_ok=True)
    for source in [root / RUN_LOG, *root.glob(RECORD)]:
        if source.is_file():
            shutil.copy2(source, copy / source.relative_to(root))
    return copy


def run_in(command, copy, minutes, output) -> int | None:
    """Run one command in the copy into its output file: its exit code, or None when it passed its
    time limit. As in checks.py, the command's whole process group never outlives this, nor does a
    check that checks.py started in a session of its own: the group is asked to stop and given ten
    seconds to stop what it started, then killed. Nothing it
    runs writes bytecode: a change of the same length within the same second would otherwise run
    the module cached before it."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    with open(output, "w") as out:
        process = subprocess.Popen(command, cwd=copy, stdout=out, stderr=subprocess.STDOUT, env=env,
                                   start_new_session=True)
        try:
            return process.wait(timeout=minutes * 60)
        except subprocess.TimeoutExpired:
            return None
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    if group_has_live_member(process.pid):
                        raise
                process.wait()


def group_has_live_member(pgid) -> bool:
    """Whether any process in the group is running: one that has exited but is not yet reaped does not count."""
    listed = subprocess.run(["ps", "-A", "-o", "pgid=,stat="], capture_output=True, text=True, check=True)
    return any(fields[0] == str(pgid) and not fields[1].startswith("Z")
               for fields in map(str.split, listed.stdout.splitlines()) if len(fields) == 2)


def prove_one(item, root, minutes) -> tuple[str, str, list[str]]:
    """Make one break in a fresh copy of root: (outcome, why, the end of the run's output). The
    outcome is caught, stayed green, red before the change or could not run."""
    with tempfile.TemporaryDirectory(prefix="prove-") as scratch:
        copy = copy_of(root, scratch)
        if "test" in item:
            runner = "pytest"
            command = [str(copy / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", item["test"]]
        else:
            runner = "checks.py"
            command = [sys.executable, "checks.py", item["check"]]
        before = pathlib.Path(scratch) / "before.txt"
        code = run_in(command, copy, minutes, before)
        if code != 0:
            return ("could not run", f"stopped after {minutes} minutes, before the change", tail(before)) if code is None \
                else ("red before the change", f"{runner} ended {code}", tail(before))
        path = copy / item["file"]
        path.write_text(path.read_text(encoding="utf-8").replace(item["find"], item["replace"]), encoding="utf-8")
        after = pathlib.Path(scratch) / "after.txt"
        code = run_in(command, copy, minutes, after)
        if code == 1:
            return "caught", "", []
        if code == 0:
            return "stayed green", "", tail(after)
        why = f"stopped after {minutes} minutes" if code is None else f"{runner} ended {code}: it did not run and fail"
        return "could not run", why, tail(after)


def prove_picked(item, root, minutes) -> tuple[str, str, list[str], dict]:
    """Make one break proved by a test in a copy that carries the picker's base and record, then run its check picked:
    (outcome, why, the end of the run's output, {"check", "ran", "of", "why"} of the pick, empty when it made none).
    The outcome is caught, caught but nothing was picked, hidden, red before the change or could not run."""
    check = "walks" if item["test"].startswith("walks/") else "unit"
    with tempfile.TemporaryDirectory(prefix="prove-") as scratch:
        copy = copy_for_pick(root, scratch)
        before = pathlib.Path(scratch) / "before.txt"
        named = [str(copy / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", item["test"]]
        code = run_in(named, copy, minutes, before)
        if code != 0:
            return ("could not run", f"stopped after {minutes} minutes, before the change", tail(before), {}) if code is None \
                else ("red before the change", f"pytest ended {code}", tail(before), {})
        path = copy / item["file"]
        path.write_text(path.read_text(encoding="utf-8").replace(item["find"], item["replace"]), encoding="utf-8")
        after = pathlib.Path(scratch) / "after.txt"
        code = run_in([sys.executable, "checks.py", "--quick", "--pick", check], copy, minutes, after)
        said = last_pick(copy, check) if code is not None else printed_pick(after, check)
        pick = {"check": check, **said} if said else {}
        whole = pick.get("ran") is not None and pick.get("ran") == pick.get("of")
        if code == 1:
            return ("caught, but nothing was picked" if whole else "caught"), "", [], pick
        if code == 0:
            return "hidden", "", tail(after), pick
        if code is None and whole:
            return "could not run, but nothing was picked", f"stopped after {minutes} minutes", [], pick
        why = f"stopped after {minutes} minutes" if code is None else f"checks.py ended {code}: it did not run and fail"
        return "could not run", why, tail(after), pick


def last_pick(copy, check) -> dict:
    """What the last run in the copy's log picked for the check: {"ran", "of", "why"}, empty when it says nothing."""
    try:
        run = json.loads((pathlib.Path(copy) / RUN_LOG).read_text().splitlines()[-1])
        said = next(p for p in run.get("picks", []) if p.get("check") == check)
    except (OSError, ValueError, IndexError, StopIteration, AttributeError):
        return {}
    return {key: said.get(key) for key in ("ran", "of", "why")}


def printed_pick(output, check) -> dict:
    """What checks.py printed it picked for the check, {"ran", "of", "why"}: a run stopped at its limit logs nothing."""
    for line in output.read_text(errors="replace").splitlines():
        found = re.match(rf"{check}\s+picked (\d+) of (\d+) [a-z]+ [a-z]+: (.*)$", line)
        if found:
            return {"ran": int(found.group(1)), "of": int(found.group(2)), "why": found.group(3)}
    return {}


NOUNS = {"unit": "unit tests", "walks": "walk files"}
FINE = ("caught", "caught, but nothing was picked", "could not run, but nothing was picked")


def picked_words(pick) -> str:
    if not pick:
        return ""
    ran, of = ("?" if pick.get(key) is None else pick[key] for key in ("ran", "of"))
    return f"picked {ran} of {of} {NOUNS[pick['check']]}: {pick.get('why')}"


def tail(output, lines=20) -> list[str]:
    return output.read_text(errors="replace").splitlines()[-lines:]


def prove(root=checks.ROOT, minutes=2, out=functools.partial(print, flush=True), pick=False) -> int:
    """Prove every break in root's list; 0 only when each one was caught. With `pick`, prove picking instead
    (prove_pick)."""
    root = pathlib.Path(root)
    try:
        breaks = json.loads((root / BREAKS).read_text(encoding="utf-8"))
        problems = list_problems(breaks, root)
    except (OSError, ValueError, AttributeError, TypeError) as error:
        breaks, problems = [], [f"{BREAKS} does not read as a list of entries: {error}"]
    if problems or not breaks:
        for problem in problems:
            out(problem)
        count = f"{len(problems)} fault{'s' if len(problems) != 1 else ''}"
        log(root, [], "red", pick)
        out(f"proof: the list of breaks has {count}; nothing was run" if problems
            else "proof: the list of breaks is empty, so nothing is proved")
        return 1
    if pick:
        return prove_pick(breaks, root, minutes, out)
    outcomes = []
    for item in breaks:
        outcome, why, output = prove_one(item, root, minutes)
        outcomes.append({"id": item["id"], "outcome": outcome})
        out(f"{item['id']}  {item.get('test') or item.get('check')}  {outcome}{f' ({why})' if why else ''}")
        for text in output:
            out(f"    {text}")
    caught = sum(o["outcome"] == "caught" for o in outcomes)
    green = bool(outcomes) and caught == len(outcomes)
    log(root, outcomes, "green" if green else "red")
    out(f"proof: {caught} of {len(outcomes)} breaks caught")
    return 0 if green else 1


def prove_pick(breaks, root, minutes, out) -> int:
    """Prove that picking hides none of the breaks proved by a test; 0 only when each was caught and there was one."""
    outcomes, by_check = [], 0
    for item in breaks:
        if "test" not in item:
            by_check += 1
            out(f"{item['id']}  {item['check']}  left to python3 prove.py: it is proved by a check, which runs whole")
            continue
        outcome, why, output, said = prove_picked(item, root, minutes)
        outcomes.append({"id": item["id"], "outcome": outcome, "ran": said.get("ran"), "of": said.get("of")})
        check = "walks" if item["test"].startswith("walks/") else "unit"
        words = "  ".join(filter(None, [f"{outcome}{f' ({why})' if why else ''}", picked_words(said)]))
        out(f"{item['id']}  {check}  {words}")
        for text in output:
            out(f"    {text}")
    caught = sum(o["outcome"].startswith("caught") for o in outcomes)
    smaller = sum(o["outcome"] == "caught" for o in outcomes)
    stopped = sum(o["outcome"] == "could not run, but nothing was picked" for o in outcomes)
    green = bool(outcomes) and all(o["outcome"] in FINE for o in outcomes)
    log(root, outcomes, "green" if green else "red", True)
    out(f"proof --pick: {caught} of {len(outcomes)} breaks caught, {smaller} by a pick smaller than the whole; "
        + (f"{stopped} stopped at the limit, but {'its pick' if stopped == 1 else 'their picks'} ran everything; " if stopped else "")
        + f"{by_check} proved by a check left to python3 prove.py")
    return 0 if green else 1


def log(root, outcomes, result, pick=False) -> None:
    """One line for this run in .checks/proof.jsonl: when, which commit, the result, each break's outcome."""
    (root / ".checks").mkdir(exist_ok=True)
    line = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commit": checks.git("rev-parse", "--short", "HEAD", root=root),
            "dirty": bool(checks.git("status", "--porcelain", root=root)),
            "result": result, "breaks": outcomes}
    if pick:
        line["picked"] = True
    with open(root / ".checks" / "proof.jsonl", "a") as file:
        file.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    for stop in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop, lambda *_: sys.exit(143))
    sys.exit(prove(pick="--pick" in sys.argv[1:]))
