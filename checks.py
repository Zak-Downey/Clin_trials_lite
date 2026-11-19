"""Every check this repo has, in one command.

    python3 checks.py              run them all, cheapest first, stopping at the first red
    python3 checks.py unit walks   run the named ones
    python3 checks.py --quick      the same with the walks at the first window size only (WALK_QUICK=1);
                                   it combines with naming checks, and the run's line in the log says quick
    python3 checks.py --pick       the walks check runs only the walk files a change can reach (picker.py, on the map
                                   walk_map.py reads), and the unit check only the tests that ran the changed code
                                   (pytest-testmon), when every changed file outside .scratch/ is Python that the
                                   tests run in their own process (not in the map's run_apart); the other
                                   checks run whole. It combines with --quick and with naming checks. A picked run is
                                   never a full run, whatever it ran. A run that is not picked runs every unit test and
                                   refreshes the record of which test ran which code
    python3 checks.py --comments   list every comment the rule does not let through (comment_hits), then the total
                                   and how many files hold one; it fails nothing and ends 0

Each check's output goes to .checks/<name>.txt. One line is printed per check and one line is
appended to .checks/runs.jsonl per run, with "quick" true or false, "every" true when every check was asked for,
"picked" true or false, and for a picked run its "base" and its "picks" (per picked check: ran, of, why). Exit 1 when a check is red. Red is a non-zero exit code
or a timeout: nothing here reads a suite's output to decide.

The checks: `lint` (Ruff over the repo, with the version pinned in requirements-dev.txt and the
rules written in ruff.toml; it writes no cache), `patterns` (no file matches a forbidden pattern, PATTERNS below, and no file holds a comment
the rule does not let through, comment_faults), `escapes` (the
defect log reads, and each new line names the check that now catches its defect), `unit`
(pytest over tests/) and `walks` (the browser walks).
"""

from __future__ import annotations

import datetime
import functools
import io
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import tokenize

ROOT = pathlib.Path(__file__).resolve().parent
PYTHON = str(ROOT / ".venv" / "bin" / "python")

CHECKS = [
    ("lint", [PYTHON, "-m", "ruff", "check", "--no-cache", "."], 1),
    ("patterns", [sys.executable, str(ROOT / "checks.py"), "--patterns"], 1),
    ("escapes", [sys.executable, str(ROOT / "checks.py"), "--escapes"], 1),
    ("unit", [PYTHON, "-m", "pytest", "-q", "-n", "auto"], 3),
    ("walks", [PYTHON, "walks/run_walks.py"], 8),
]

PATTERNS = [
    {
        "rule": "R-005",
        "why": "a value compared with itself checks nothing (E-026)",
        "pattern": r"\(\s*\w+\s*,\s*(\w+)\s*\)\s*==\s*\([^()]*,\s*\1\s*\)",
        "globs": ["walks/**/*.py", "tests/**/*.py"],
    },
]

ESCAPES = "docs/agents/local/escapes.jsonl"
CHECK_REQUIRED_FROM = "2026-11-17"
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")


def pattern_hits(patterns=PATTERNS, root=ROOT) -> list[str]:
    """`<file>:<line>: <rule>: <why>` for every line a pattern matches."""
    hits = []
    for rule in patterns:
        regex = re.compile(rule["pattern"])
        for glob in rule["globs"]:
            for path in sorted(pathlib.Path(root).glob(glob)):
                if not path.is_file():
                    continue
                for number, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
                    if regex.search(line):
                        hits.append(f"{path.relative_to(root)}:{number}: {rule['rule']}: {rule['why']}")
    return hits


STATIC = "webapp/static/"
STATIC_MARKS = {".js": ("//", "/*"), ".css": ("//", "/*"), ".html": ("<!--",)}
DIRECTIVE = re.compile(r"#\s*noqa:\s*[A-Z]+[0-9]+\s+(?![A-Z]+[0-9]+\b)\S.*\w", re.I)


def python_comments(text: str) -> list[tuple[int, str]]:
    """(line, text) of every comment Python's tokenizer finds, but a `#!` first line and a linter directive that
    names one rule and gives its reason on the same line."""
    found = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        line, said = token.start[0], token.string
        if (line == 1 and said.startswith("#!")) or DIRECTIVE.match(said):
            continue
        found.append((line, said))
    return found


def static_comments(text: str, marks) -> list[tuple[int, str]]:
    """(line, the line from its first mark on) for every line holding one of `marks`."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        starts = [line.find(mark) for mark in marks if mark in line]
        if starts:
            found.append((number, line[min(starts):].strip()))
    return found


UNLISTED_SKIPPED = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}


def listed_files(root) -> list[str]:
    """The files git tracks in `root`; in a folder git cannot list (a copy with no history, an unpacked download),
    every file under it, but in a folder named in UNLISTED_SKIPPED and without following a linked folder."""
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True)
    if listed.returncode == 0:
        return [name for name in listed.stdout.split("\0") if name]
    names = []
    for folder, folders, files in os.walk(root):
        folders[:] = [name for name in folders if name not in UNLISTED_SKIPPED]
        names.extend(pathlib.Path(folder, name).relative_to(root).as_posix() for name in files)
    return names


KEPT = "docs/agents/local/comments-kept.json"
KEPT_CEILING = 10
KEPT_FIELDS = ("file", "text", "why")


def kept_entries(root=ROOT, kept=KEPT) -> tuple[list[dict], list[str]]:
    """(the entries of the kept list that have every field, what is wrong with the list). A missing list keeps nothing."""
    file = pathlib.Path(root) / kept
    if not file.is_file():
        return [], []
    try:
        entries = json.loads(file.read_text(encoding="utf-8"))
    except ValueError:
        entries = None
    if not isinstance(entries, list):
        return [], [f"{kept}: not a JSON list"]
    whole, problems = [], []
    for number, entry in enumerate(entries, start=1):
        if isinstance(entry, dict) and all(isinstance(entry.get(field), str) and entry[field].strip()
                                           for field in KEPT_FIELDS):
            whole.append(entry)
        else:
            problems.append(f"{kept}: entry {number} needs a `file`, the comment's exact `text` and `why` it must stay")
    if len(entries) > KEPT_CEILING:
        problems.append(f"{kept}: {len(entries)} entries, over the ceiling of {KEPT_CEILING}: "
                        "say the rest in a name or a test")
    return whole, problems


def comments_not_let_through(root=ROOT, kept=KEPT) -> tuple[list[tuple[str, int, str]], list[str]]:
    """(every comment comments() finds that no kept entry names, what is wrong with the kept list, including each
    entry whose text is no longer a comment in its file)."""
    entries, problems = kept_entries(root, kept)
    found = comments(root)
    present = {(name, said) for name, _, said in found}
    for number, entry in enumerate(entries, start=1):
        if (entry["file"], entry["text"]) not in present:
            problems.append(f"{kept}: entry {number} keeps `{entry['text']}`, which is no longer a comment in "
                            f"{entry['file']}: remove the entry")
    keeps = {(entry["file"], entry["text"]) for entry in entries}
    return [hit for hit in found if (hit[0], hit[2]) not in keeps], problems


def comment_hits(root=ROOT) -> list[str]:
    """`<file>:<line>: <the comment>` for every comment that comments_not_let_through() gives."""
    return [f"{name}:{line}: {said}" for name, line, said in comments_not_let_through(root)[0]]


COMMENT_ADVICE = "say it in a name, or in a test that fails without it; a comment is checked by nothing"


def comment_faults(root=ROOT) -> list[str]:
    """The `patterns` check's lines: what is wrong with the kept list, then for every comment not let through where it
    is, what to do instead and the comment."""
    found, problems = comments_not_let_through(root)
    return problems + [f"{name}:{line}: {COMMENT_ADVICE} ({said})" for name, line, said in found]


def comments(root=ROOT) -> list[tuple[str, int, str]]:
    """(file, line, the comment) for every comment in a file listed_files gives outside .scratch/: in Python, and in a
    script, style sheet or page under STATIC."""
    hits = []
    for name in sorted(n for n in listed_files(root) if not n.startswith(".scratch/")):
        path = pathlib.Path(root) / name
        if not path.is_file():
            continue
        if path.suffix == ".py":
            found = python_comments(path.read_text(errors="replace"))
        elif name.startswith(STATIC) and path.suffix in STATIC_MARKS:
            found = static_comments(path.read_text(errors="replace"), STATIC_MARKS[path.suffix])
        else:
            continue
        hits.extend((name, line, said) for line, said in found)
    return hits


def escape_problems(path=ESCAPES, root=ROOT, required_from=CHECK_REQUIRED_FROM) -> list[str]:
    """What is wrong with the defect log: a line that is not JSON, has no id or a repeated one, has
    no date written YYYY-MM-DD, or is from `required_from` on and its `check` names no file that exists."""
    problems, seen = [], set()
    file = pathlib.Path(root) / path
    if not file.is_file():
        return [f"{path}: missing"]
    for number, line in enumerate(file.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            problems.append(f"{path}:{number}: not JSON")
            continue
        ident = row.get("id", "")
        if not ident or ident in seen:
            problems.append(f"{path}:{number}: id missing or repeated ({ident!r})")
        seen.add(ident)
        date = str(row.get("date", ""))
        if not DATE.match(date):
            problems.append(f"{path}:{number}: {ident} has no date written YYYY-MM-DD ({date!r})")
        elif date >= required_from:
            check = str(row.get("check", "")).split("::")[0]
            if not check or not (pathlib.Path(root) / check).is_file():
                problems.append(f"{path}:{number}: {ident} names no check file that exists ({check!r})")
    return problems


def git(*args, root=ROOT) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def walk_feature(branch: str, root=ROOT) -> str | None:
    """The feature whose folder the walks write to: the branch's last part, when .scratch has it."""
    slug = branch.rsplit("/", 1)[-1]
    return slug if slug and (pathlib.Path(root) / ".scratch" / slug).is_dir() else None


def run_one(command, minutes, output, root=ROOT, env=None) -> tuple[str, float]:
    """Run one check into its output file. ('green' | 'red', minutes taken). A timeout stops the
    check's whole process group and is red."""
    started = time.monotonic()
    with open(output, "w") as out:
        try:
            process = subprocess.Popen(command, cwd=root, stdout=out, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
        except OSError as error:
            out.write(f"could not start {command[0]}: {error}\n")
            return "red", 0.0
        stopped = False
        try:
            code = process.wait(timeout=minutes * 60)
        except subprocess.TimeoutExpired:
            code, stopped = 1, True
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        if stopped:
            out.write(f"\nchecks.py: stopped after {minutes} minutes\n")
    return ("green" if code == 0 else "red"), round((time.monotonic() - started) / 60, 2)


def pick_walks(root, changed) -> tuple[list[str], dict]:
    """(the walk files to give the walk check, none when it is to run them all; {"ran", "of", "why"})."""
    import picker
    import walk_map
    every = sorted(str(path.relative_to(root)) for path in pathlib.Path(root).glob(walk_map.WALKS))
    try:
        the_map = walk_map.read(root)
    except (OSError, ValueError):
        return [], {"ran": len(every), "of": len(every), "why": f"every walk: no map of the pages at {walk_map.MAP}"}
    files, why = picker.walks(changed, the_map, every)
    return ([] if set(files) >= set(every) else files), {"ran": len(files), "of": len(every), "why": why}


def unit_map(root) -> dict:
    """The map's lists for the unit picker (walk_map.py says what they are); {"run_apart": None} when there is no map."""
    import walk_map
    try:
        return walk_map.read(root)
    except (OSError, ValueError):
        return {"run_apart": None}


def unit_always(root, why) -> tuple[list[str], str]:
    """(the unit test files a picked run gives when its record selected none, none for every test; the reason, said
    after `why`). They are the map's `unit_always`, so that green never means nothing ran."""
    import walk_map
    listed = unit_map(root).get("unit_always") or []
    files = [name for name in walk_map.repo_files(root) if walk_map.matches(name, listed)] if listed else []
    if not files:
        return [], f"{why}; none was selected, and the map names no test that always runs, so every test"
    return files, f"{why}; none was selected, so the tests that always run, {', '.join(f'`{name}`' for name in files)}"


SELECT, NOSELECT = "--testmon", "--testmon-noselect"

COUNTED = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)\b")
COLLECTED = re.compile(r"(\d+) tests? collected")


def unit_ran(output: str) -> int | None:
    """How many tests ran, from the summary line pytest ends with; None when it printed none."""
    for line in reversed(output.splitlines()):
        counts = COUNTED.findall(line)
        if counts:
            return sum(int(n) for n, _ in counts)
    return None


def unit_there_are(command, root, env) -> int | None:
    """How many unit tests there are, by collecting them without running any. A selecting run cannot say: across
    processors, pytest's summary leaves out the tests it deselected."""
    try:
        done = subprocess.run([*command, "--collect-only", "--no-testmon"], cwd=root, env=env,
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    found = COLLECTED.search(done.stdout)
    return int(found.group(1)) if found else None


QUICK = "WALK_QUICK"


def run(names=(), checks=None, root=ROOT, out=functools.partial(print, flush=True), quick=False, pick=False) -> int:
    checks = CHECKS if checks is None else checks
    known = [name for name, _, _ in checks]
    unknown = [name for name in names if name not in known]
    if unknown:
        out(f"checks.py: no check named {', '.join(unknown)}. The checks are: {', '.join(known)}")
        return 2
    root = pathlib.Path(root)
    folder = root / ".checks"
    folder.mkdir(exist_ok=True)
    branch = git("rev-parse", "--abbrev-ref", "HEAD", root=root)
    env = dict(os.environ)
    env.pop(QUICK, None)
    if quick:
        env[QUICK] = "1"
    if "WALK_FEATURE" not in env and walk_feature(branch, root):
        env["WALK_FEATURE"] = walk_feature(branch, root)
    started, results, red, picks = time.monotonic(), [], None, []
    changed = base = None
    if pick:
        import picker
        changed, base = picker.changed(root)
    for name, command, minutes in checks:
        if names and name not in names:
            continue
        output = folder / f"{name}.txt"
        shown = output.relative_to(root)
        if red:
            results.append({"name": name, "result": "not run", "minutes": 0.0, "output": str(shown)})
            out(f"{name:<9} not run ({red} was red)")
            continue
        if pick and name == "walks":
            files, said = pick_walks(root, changed)
            command = [*command, *files]
            picks.append({"check": name, **said})
            out(f"{name:<9} picked {said['ran']} of {said['of']} walk files: {said['why']}")
        select, unit_why, there_are = False, None, None
        if name == "unit":
            if pick:
                select, unit_why = picker.unit(changed, unit_map(root).get("run_apart", []))
                there_are = unit_there_are(command, root, env) if select else None
            given, command = command, [*command, SELECT if select else NOSELECT]
        result, took = run_one(command, minutes, output, root, env)
        if unit_why:
            ran = unit_ran(output.read_text(errors="replace"))
            if select and result == "green" and not ran:
                files, unit_why = unit_always(root, unit_why)
                result, more = run_one([*given, *files, NOSELECT], minutes, output, root, env)
                took, ran = round(took + more, 2), unit_ran(output.read_text(errors="replace"))
            of = there_are if select else ran
            picks.append({"check": name, "ran": ran, "of": of, "why": unit_why})
            counted = f"{'?' if ran is None else ran} of {'?' if of is None else of} unit tests"
            out(f"{name:<9} picked {counted}: {unit_why}")
        results.append({"name": name, "result": result, "minutes": took, "output": str(shown)})
        out(f"{name:<9} {result:<6} {took:>5.1f} min  {shown}")
        if result == "red":
            red = name
            for line in output.read_text(errors="replace").splitlines()[-20:]:
                out(f"    {line}")
    total = round((time.monotonic() - started) / 60, 2)
    line = {
        "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": branch,
        "tip": git("rev-parse", "--short", "HEAD", root=root),
        "dirty": bool(git("status", "--porcelain", root=root)),
        "result": "red" if red else "green",
        "minutes": total,
        "quick": quick,
        "every": set(known) <= set(names or known),
        "picked": pick,
        "base": base,
        "picks": picks,
        "checks": results,
    }
    with open(folder / "runs.jsonl", "a") as log:
        log.write(json.dumps(line) + "\n")
    said = [words for on, words in ((quick, "quick: walks at one window size"), (pick, "picked: not a full run")) if on]
    out(f"checks: {'red (' + red + ')' if red else 'green'} in {total:.1f} min{' (' + '; '.join(said) + ')' if said else ''}")
    return 1 if red else 0


def main(argv) -> int:
    if argv == ["--patterns"]:
        hits = pattern_hits() + comment_faults(ROOT)
        print("\n".join(hits) if hits else f"no file matches any of the {len(PATTERNS)} patterns, and no file holds a comment")
        return 1 if hits else 0
    if argv == ["--escapes"]:
        problems = escape_problems()
        print("\n".join(problems) if problems else f"{ESCAPES}: every line reads and names its check where it must")
        return 1 if problems else 0
    if argv == ["--comments"]:
        hits = comment_hits(ROOT)
        files = {hit.split(":", 1)[0] for hit in hits}
        print("\n".join([*hits, f"{len(hits)} comments in {len(files)} files"]))
        return 0
    options = {"--quick", "--pick"}
    return run([name for name in argv if name not in options], quick="--quick" in argv, pick="--pick" in argv)


if __name__ == "__main__":
    for stop in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop, lambda *_: sys.exit(143))
    sys.exit(main(sys.argv[1:]))
