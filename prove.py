"""Proof that the checks can fail: small deliberate breaks, each of which a named test or check must notice.

The list is docs/agents/local/breaks.json: entries with an `id`, the `file` to change, the text to
`find` (exactly once in that file), the text to `replace` it with, a `why` in one sentence, and what
proves it: `test` (one pytest test, by its id) or `check` (the name of a check in CHECKS), never both.

    python3 prove.py    prove every break; by hand only, never one of the checks

A list with a fault stops it before anything runs. Each break is made in a fresh copy of the files
git tracks, as they are on disk, in a temporary folder whose `.venv` is a link to this one's; the
working folder is never touched. Its test or check runs unbroken (it must be green) and broken (it
must be red: pytest's exit code 1, a test that ran and failed, or `checks.py <name>` ending 1).
Each break is caught, stayed green, red before the change, or could not run (stopped at its time
limit, or ended some other way). Each run has a limit of two minutes and nothing it starts outlives
it. Exit 0 only when every break was caught and the list is not empty. One line per run is appended
to .checks/proof.jsonl.
"""

from __future__ import annotations

import ast
import datetime
import functools
import json
import os
import pathlib
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


def run_in(command, copy, minutes, output) -> int | None:
    """Run one command in the copy into its output file: its exit code, or None when it passed its
    time limit. As in checks.py, the command's whole process group never outlives this. Nothing it
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
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


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


def tail(output, lines=20) -> list[str]:
    return output.read_text(errors="replace").splitlines()[-lines:]


def prove(root=checks.ROOT, minutes=2, out=functools.partial(print, flush=True)) -> int:
    """Prove every break in root's list; 0 only when each one was caught."""
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
        log(root, [], "red")
        out(f"proof: the list of breaks has {count}; nothing was run" if problems
            else "proof: the list of breaks is empty, so nothing is proved")
        return 1
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


def log(root, outcomes, result) -> None:
    """One line for this run in .checks/proof.jsonl: when, which commit, the result, each break's outcome."""
    (root / ".checks").mkdir(exist_ok=True)
    line = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commit": checks.git("rev-parse", "--short", "HEAD", root=root),
            "dirty": bool(checks.git("status", "--porcelain", root=root)),
            "result": result, "breaks": outcomes}
    with open(root / ".checks" / "proof.jsonl", "a") as file:
        file.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    for stop in (signal.SIGTERM, signal.SIGHUP):  # stopped from outside: leave through the finally blocks
        signal.signal(stop, lambda *_: sys.exit(143))
    sys.exit(prove())
