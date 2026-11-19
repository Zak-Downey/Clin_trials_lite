"""Build the one page a build ends with: .scratch/<feature>/hand-over/index.html.

    python3 handover.py <feature> [--base <ref>] [--tip <ref> --branch <name>] [--no-walk] [--no-open]

Run from the repo root. The page is one file: its pictures, its styles and its one small script are inside it (a
screenshot over 1.5 MB stays a file beside it), and it loads nothing from outside its own folder. When it is built
it opens in the browser. The facts on the page are computed here, from git and from
machine-readable files; the only words an agent writes are the what / so what / now
what of hand-over.json, the title and legend of each part of its walk_through, and the words inside findings and fates. Wherever the page prints them it says whose they
are and that it did not check them, and what they say never changes a colour, a count or the page's own list of
things to look at. Whether one exists does, in one place: a `not-a-defect` outcome with no reason written is listed
for the owner. Nothing here reads Markdown.

The page is written for the owner, who has neither the code nor the records open, so its fixed text follows
.claude/rules/human-facing-writing.md. It leads with what happened and why that matters, and keeps each issue's
whole record folded under it. Its words for the records' fields: a finding is an issue, a fate an outcome, a fate's
check a test, a finder a review (the `walker` finder is exploratory testing; "browser tests" is kept for the `walks`
check), a pass a review round, the recorded run of walks the walk-through (one walk in it is a part), and a checks run a run
of the automated checks.
The field names themselves are unchanged.

Reads (all optional; what is missing is shown as missing, never as zero):
  git                                   the commits of <base>..<tip>
  .checks/runs.jsonl                    one line per checks run; a quick one (checks.py --quick) or a picked one
                                        (checks.py --pick) is never the full run
  .scratch/<feature>/findings/*.jsonl   one line per finding; an empty file is a look that found nothing
  .scratch/<feature>/fates.jsonl        one line per finding id: what became of it
  .scratch/<feature>/hand-over.json     {"what": [...], "so_what": [...], "now_what": [...], "walk_through": [...]}
  .scratch/<feature>/walks/flaky.jsonl  one line per run of the browser tests: the ones red with the others and green
                                        alone. Each is listed for the owner; where the build's last run of them has no
                                        line, the page says the record is missing (earlier runs may predate it)
  this computer (lsof, ps)              the project's programs still listening on a port: one started during the build
                                        is listed for the owner, since a test may have left it running

Writes, beside index.html: the walk-through. It is one recording in parts: a part is a walk this build added or changed
(a test function in walks/test_*.py with an added or changed line of its own) that hand-over.json lists under
walk_through, with the title and the legend the page prints for it; each part is recorded as clips/<walk>.webm and the
page plays them one after another. A build that added or changed no walk gets the standing walk through the whole app
instead, as recording.webm. The page plays them from beside itself. Also
recording.json (which walks, when, on which commit and how each ended), shots/*.png and walk-output.txt.
A walk that fails is said on the page and in one printed line; the exit code is still 0.
"""

from __future__ import annotations

import argparse
import ast
import base64
import datetime
import html
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.parse
import webbrowser
import xml.etree.ElementTree

import checks

ROOT = pathlib.Path(__file__).resolve().parent

# The walk recorded when the build added or changed none of its own: the whole journey, keyboard only, Chromium at
# 1440 x 900. The build's own walks are recorded at VIEW, the same window size.
MAIN = "main"  # the branch a build is merged into (CLAUDE.md, "When the owner accepts a build")
WALK = "walks/test_acceptance_walk.py::test_walk_the_whole_journey_by_keyboard_alone[chromium-1440x900]"
VIEW = "1440x900"
# A walk the build wrote is a few steps long, so it is recorded with a longer pause after each step than a walk
# records at by itself (walks/helper.py): at that pace its video would be over in a second or two.
OWN_SLOW_MO = "800"
CHECK_NAMES = [name for name, _, _ in checks.CHECKS]  # a checks run is "full" when it lists every one of these

# The page's own words. The record files say finding, fate, finder, pass and check; the page says issue, outcome,
# review, round and test, because its reader has not read the record formats (.claude/rules/human-facing-writing.md).
FINDERS = {"walker": "Exploratory testing", "review": "Code review", "early-read": "Early code review"}
FINDER_NOTES = {
    "walker": "Agents use the running app in a real browser and try to break it.",
    "review": "Agents read the build's code changes for faults the tests would not catch.",
    "early-read": "One agent reads the code after the build's first piece of work, before the rest is built on it. "
                  "The code review that follows reads its fixes, so it has no re-check of its own.",
}
PASSES = {"first": "First review", "recheck": "Re-check after the fixes"}
SEVERITIES = {"blocks": "blocks use", "wrong": "wrong", "cosmetic": "cosmetic"}  # the three the format names, most serious first
OUTCOMES = {"fixed": "fixed", "left": "left unfixed", "not-a-defect": "not a defect"}  # the three fates, in the page's words
# What the record says happened to an issue, in the order the page shows the groups: heading, look, drawn open.
# What each group means to the reader is state_said's.
STATES = {
    "no-fate": ("No outcome recorded", "bad", True),
    "left": ("Left unfixed", "warn", True),
    "fixed-not-found": ("Marked fixed, proof incomplete", "warn", True),
    "fixed-no-check": ("Marked fixed, no test named", "note", False),
    "fixed": ("Marked fixed, test named", "", False),
    "not-a-defect": ("Not a defect", "", False),
}
FOUND = (" This page found each test's file in the build's last commit and each commit in the repository. "
         "It did not run the tests.")
FOUND_ONE = " This page found the test's file in the build's last commit and the commit in the repository. It did not run the test."
WALK_ENDS = {"failed": "failed", "did not run": "did not run", "did not finish": "did not finish"}
RUN_ENDS = {"green": "passed", "red": "failed"}  # the run log's words for a result, and the page's
SUMMARY_LINES, LINE_LENGTH = 5, 200  # what and so_what: at most this many lines; any line of hand-over.json: at most this long
TITLE_LENGTH, LEGEND_LENGTH = 80, 300  # a part of the walk-through: its title and its legend, at most this long
CODE_NAME = re.compile(r"[\w.:/]*(?:\w_\w|::)[\w.:/]*")  # a name from the code (test_walk_x, file::name): never in a title or a legend
WALKS_CHECK = "walks"  # checks.py's name for the browser tests: a run that lists it ran them
FLAKY_RECORD = "flaky.jsonl"  # walks/run_walks.py's FLAKY_RECORD, beside its output in .scratch/<feature>/walks/
PICTURE_BYTES = 1_500_000  # a screenshot up to this size is put inside the page; a larger one stays a file beside it


# Reading.

def read_jsonl(path: pathlib.Path) -> list[dict]:
    """The JSON objects of a .jsonl file, one per line; blank lines skipped. A broken line stops the run."""
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as error:
            raise SystemExit(f"handover: {path} line {number} is not JSON: {error}")
        if not isinstance(row, dict):
            raise SystemExit(f"handover: {path} line {number} is not a JSON object")
        rows.append(row)
    return rows


def read_findings(feature_dir: pathlib.Path) -> dict[str, list[dict]]:
    """{file name: its findings} for every findings/*.jsonl file, in file-name order. Two findings sharing
    an id stop the run: a fate is matched by id alone, so the page would give both the fate of one."""
    files, seen = {}, {}
    for path in sorted((feature_dir / "findings").glob("*.jsonl")):
        files[path.name] = read_jsonl(path)
        for row in files[path.name]:
            ident = str(row.get("id", ""))
            if ident in seen:
                where = f"twice in {path}" if seen[ident] == path else f"in both {seen[ident]} and {path}"
                raise SystemExit(f"handover: finding id {ident!r} is {where}. Give the later finding a new id, "
                                 "and check which line of fates.jsonl belongs to which finding.")
            seen[ident] = path
    return files


def read_fates(feature_dir: pathlib.Path) -> dict[str, dict]:
    """fates.jsonl by finding id (a later line for the same id replaces an earlier one)."""
    path = feature_dir / "fates.jsonl"
    return {str(row.get("id", "")): row for row in read_jsonl(path)} if path.exists() else {}


def read_json(path: pathlib.Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise SystemExit(f"handover: {path} is not JSON: {error}")


def read_summary(feature_dir: pathlib.Path) -> dict | None:
    """hand-over.json: the what / so what / now what an agent wrote. None when there is no file.
    A file of another shape stops the run, and so does a line too long to be read at a glance."""
    path = feature_dir / "hand-over.json"
    summary = read_json(path)
    lists = [summary.get(key, []) for key in ("what", "so_what", "now_what")] if isinstance(summary, dict) else [None]
    if summary is not None and not all(isinstance(lines, list) and all(isinstance(line, str) for line in lines) for lines in lists):
        raise SystemExit(f"handover: {path} must be an object whose what, so_what and now_what are each a list of sentences")
    for key in ("what", "so_what", "now_what") if summary else ():
        lines = summary.get(key, [])
        if key != "now_what" and len(lines) > SUMMARY_LINES:
            raise SystemExit(f"handover: {path}: {key} has {len(lines)} lines; the page gives it at most {SUMMARY_LINES}. Cut it to what the owner must know.")
        for index, line in enumerate(lines, 1):
            if len(line) > LINE_LENGTH:
                raise SystemExit(f"handover: {path}: {key} line {index} is {len(line)} characters; the page gives a line at most "
                                 f"{LINE_LENGTH}. Say one thing in it, shorter, or split it in two.")
    parts = summary.get("walk_through", []) if summary else []
    if not (isinstance(parts, list) and all(isinstance(part, dict) and all(
            isinstance(part.get(key), str) and part[key].strip() for key in ("test", "title", "legend")) for part in parts)):
        raise SystemExit(f"handover: {path}: walk_through must be a list of objects, each with a test, a title and a legend")
    for index, part in enumerate(parts, 1):
        for key, most in (("title", TITLE_LENGTH), ("legend", LEGEND_LENGTH)):
            if len(part[key]) > most:
                raise SystemExit(f"handover: {path}: walk_through entry {index}: the {key} is {len(part[key])} characters; the page "
                                 f"gives it at most {most}.")
            name = CODE_NAME.search(part[key])
            if name:
                raise SystemExit(f"handover: {path}: walk_through entry {index}: the {key} holds a name from the code "
                                 f"({name.group(0)}). The owner reads it as written: say what a user does and sees, in plain words.")
    return summary


def read_runs(path: pathlib.Path) -> list[dict] | None:
    """The checks run log, oldest first. None when the file does not exist."""
    return read_jsonl(path) if path.exists() else None


def git(repo: pathlib.Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"handover: git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def git_ok(repo: pathlib.Path, *args: str) -> bool:
    """Whether a git command succeeds: for a question git answers with its exit status."""
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).returncode == 0


# Computing.

def ask(*command: str) -> str | None:
    """What a program of this computer printed, or None when it could not be run. Its exit code is not read: lsof
    exits 1 when it has nothing to list."""
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=30, env={**os.environ, "LC_ALL": "C"}).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def listeners(root: pathlib.Path) -> list[dict] | None:
    """Each program now listening on a network port that was started with a file of this project (run.py, a test's
    server, a test file): its process number, when it started and its ports, oldest first. The app is such a program,
    and so is a copy of it a test started and never stopped; a program that only has this folder as its working
    folder is not. None when this computer could not be asked (it has no lsof or no ps, or ps gave a time this could
    not read)."""
    listening = ask("lsof", "-a", "-iTCP", "-sTCP:LISTEN", "-P", "-n", "-Fpn")
    if listening is None:
        return None
    ports: dict[int, set[int]] = {}
    pid = None
    for line in listening.splitlines():
        if line[:1] == "p" and line[1:].isdigit():
            pid = int(line[1:])
        elif line[:1] == "n" and pid is not None and line.rsplit(":", 1)[-1].isdigit():
            ports.setdefault(pid, set()).add(int(line.rsplit(":", 1)[-1]))
    if not ports:
        return []
    pids = ",".join(str(pid) for pid in sorted(ports))
    # -ww: whole command lines (Linux's ps otherwise cuts them to the terminal's width, 80 columns when piped)
    folders, programs = ask("lsof", "-a", "-d", "cwd", "-p", pids, "-Fpn"), ask("ps", "-ww", "-o", "pid=,lstart=,command=", "-p", pids)
    if folders is None or programs is None:
        return None
    folder, pid = {}, None
    for line in folders.splitlines():
        if line[:1] == "p" and line[1:].isdigit():
            pid = int(line[1:])
        elif line[:1] == "n" and pid is not None:
            folder[pid] = pathlib.Path(line[1:])
    found = []
    for line in programs.splitlines():
        number, *words = line.split()
        if not number.isdigit() or not any(of_project(root, folder.get(int(number)), word) for word in words[5:]):
            continue
        try:  # ps gives this computer's own time: "Tue Nov 17 22:03:50 2026"
            started = datetime.datetime.strptime(" ".join(words[:5]), "%a %b %d %H:%M:%S %Y").astimezone(datetime.timezone.utc)
        except ValueError:
            return None
        found.append({"pid": int(number), "started": started.isoformat(timespec="seconds"), "ports": sorted(ports[int(number)])})
    return sorted(found, key=lambda copy: moment(copy["started"]))


def of_project(root: pathlib.Path, folder: pathlib.Path | None, word: str) -> bool:
    """Whether one word of a program's command names a file of this project: as it is, or from the program's working folder."""
    try:
        named = ((folder or root) / word.split("::")[0]).resolve()
        return named.is_file() and named.is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def moment(stamp: str) -> datetime.datetime:
    """An ISO-8601 time as a datetime with a zone (git and the run log write UTC as Z; a time with no zone is read as UTC)."""
    read = datetime.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    return read if read.tzinfo else read.replace(tzinfo=datetime.timezone.utc)


def tests_changed(diff: str, sign: str) -> int:
    """How many `def test_` lines a diff adds (sign "+") or removes (sign "-")."""
    return len(re.findall(rf"^{re.escape(sign)}\s*(?:async\s+)?def test_\w*\(", diff, re.M))


def git_facts(repo: pathlib.Path, base: str, tip: str) -> dict:
    """What git knows of base..tip: commits, first and last commit time, minutes between, the size of the diff."""
    times = sorted(git(repo, "log", "--format=%cI", f"{base}..{tip}").split(), key=moment)
    first, last = (times[0], times[-1]) if times else (None, None)
    span = moment(last) - moment(first) if times else None
    files = removed = 0
    added = {"product": 0, "tests and browser tests": 0, "build records and agent instructions (.scratch/, .claude/)": 0}
    for line in git(repo, "diff", "--numstat", f"{base}...{tip}").splitlines():
        plus, minus, path = line.split("\t", 2)
        path = re.sub(r"\{[^{}]* => ([^{}]*)\}", r"\1", path).split(" => ")[-1].replace("//", "/")  # a renamed file: its new path
        kind = list(added)[2 if path.startswith((".scratch/", ".claude/")) else 1 if path.startswith(("tests/", "walks/")) else 0]
        files += 1
        added[kind] += int(plus) if plus.isdigit() else 0  # a binary file has "-" for both
        removed += int(minus) if minus.isdigit() else 0
    tests = git(repo, "diff", f"{base}...{tip}", "--", "tests", "walks")
    # Already merged: the range holds commits and its last one is part of main. Main as last fetched from the remote is
    # asked first, so a merge made only in this folder, which the owner never saw, does not count; the local branch is
    # asked only when the folder has no remote main. None when it has neither.
    main = next((ref for ref in (f"refs/remotes/origin/{MAIN}", f"refs/heads/{MAIN}")
                 if git_ok(repo, "rev-parse", "--verify", "--quiet", ref)), None)
    merged = (bool(times) and git_ok(repo, "merge-base", "--is-ancestor", tip, main)) if main else None
    # When it was merged: the time of the oldest commit on main's own line that holds the build's last commit (the
    # merge commit; for a build main was moved forward to, the commit that followed it, or its own last commit).
    after = git(repo, "log", "--first-parent", "--ancestry-path", "--format=%cI", f"{tip}..{main}").split() if merged else []
    return {
        "merged": merged, "merged_at": (after[-1] if after else last) if merged else None,
        "base": git(repo, "rev-parse", "--short", base), "tip": git(repo, "rev-parse", "--short", tip),
        "commits": len(times), "first": first, "last": last,
        "minutes": round(span.total_seconds() / 60) if span is not None else None,
        "files": files, "added": sum(added.values()), "added_by": added, "removed": removed,
        "tests_added": tests_changed(tests, "+"), "tests_removed": tests_changed(tests, "-"),
    }


def commit_gap(repo: pathlib.Path, commit, tip: str) -> tuple[int, int] | None:
    """(commits that `commit` has and the build's last commit does not, commits the last commit has and `commit` does
    not). None when git does not know the commit, so the page says nothing of the distance."""
    if not commit or not git_ok(repo, "cat-file", "-e", f"{commit}^{{commit}}"):
        return None
    ahead, behind = git(repo, "rev-list", "--left-right", "--count", f"{commit}...{tip}").split()
    return int(ahead), int(behind)


def run_facts(runs: list[dict] | None, branch: str, names=None) -> dict:
    """The checks runs of one branch: how many, how many red, each run's result in order (`history`), the last
    run of every check that was neither quick nor picked (`full`) and, for each check run again after it in a run of only some checks, that check's
    most recent result and when (`since`; with no full run, every logged run counts). A later pass of one check
    therefore never hides an earlier failure of another. None, with why, where the log does not say."""
    facts = {"runs": None, "red": None, "full": None, "since": {}, "history": [], "branch": branch,
             "names": list(CHECK_NAMES if names is None else names), "why_unknown": ""}
    if runs is None:
        return {**facts, "why_unknown": "No run of the checks was logged: the log file .checks/runs.jsonl does not exist."}
    own = [run for run in runs if run.get("branch") == branch]
    if not own:
        return {**facts, "why_unknown": f"The log of check runs (.checks/runs.jsonl) has no entry for this build's branch, {branch}."}
    full = [index for index, run in enumerate(own) if is_full(run, facts["names"])]
    since = {}
    for run in own[full[-1] + 1:] if full else own:  # oldest first, so a check's later result replaces its earlier one
        listed_ = [check for check in run.get("checks") or [] if check.get("result") != "not run"]
        for check in listed_ or [{"name": "a run that names no check", "result": run.get("result")}]:
            since[str(check.get("name", "?"))] = {"result": str(check.get("result")), "at": run.get("at")}
    history = [{"at": run.get("at"), "result": str(run.get("result")), "full": is_full(run, facts["names"]), "quick": run.get("quick") is True,
                "picked": run.get("picked") is True,
                "tip": run.get("tip"), "minutes": run.get("minutes"), "walks": ran_walks(run)} for run in own]
    return {**facts, "runs": len(own), "red": sum(run.get("result") == "red" for run in own), "history": history,
            "full": own[full[-1]] if full else None, "since": since}


def ran_walks(run: dict) -> bool:
    """Whether a run's line lists the browser tests as run (the `walks` check, with a result other than not run)."""
    return any(str(check.get("name")) == WALKS_CHECK and check.get("result") != "not run" for check in run.get("checks") or [])


def read_flaky(feature_dir: pathlib.Path) -> list[dict]:
    """The walk runner's record of browser tests red with the others and green alone, one line per run; [] when the
    file does not exist, which the page then says is missing for the build's runs of the browser tests."""
    path = feature_dir / "walks" / FLAKY_RECORD
    return read_jsonl(path) if path.exists() else []


def line_of(run: dict, before: list[dict], lines: list[dict]) -> dict | None:
    """The line of the walk runner's record written by this checks run, or None: of the lines on the same commit written
    while the run ran, the latest. The run's line is logged when it ends and the browser tests run last, so the record's
    line comes at or just before the run's end, at most the run's length (and a minute of slack) before it, and after the
    end of any run logged before it on the same commit (`before`, the branch's runs logged earlier), whose line it would
    otherwise be: a quick run followed at once by a full run on the same commit gets only its own line."""
    try:
        ended_at = moment(run.get("at"))
    except (TypeError, ValueError):
        return None
    took = datetime.timedelta(minutes=(run.get("minutes") if isinstance(run.get("minutes"), (int, float)) else 0) + 1)
    after = ended_at - took
    for earlier in before:
        try:
            if same_commit(earlier.get("tip"), run.get("tip")) and moment(earlier.get("at")) < ended_at:
                after = max(after, moment(earlier.get("at")))
        except (TypeError, ValueError):
            continue
    found = []
    for line in lines:
        try:
            written = moment(line.get("at"))
        except (TypeError, ValueError):
            continue
        if same_commit(line.get("tip"), run.get("tip")) and after < written <= ended_at:
            found.append((written, line))
    return max(found, key=lambda pair: pair[0])[1] if found else None


def flaky_facts(runs: dict, lines: list[dict] | None) -> dict | None:
    """The browser tests that were red with the others and green alone in the build's runs of them, each with the runs
    it happened in ({node id: [the run's time]}, in the order first seen), and whether the record is missing: true when
    the build's last run of the browser tests has no line in it. Earlier runs without a line are not called missing,
    since a build may have started before the runner kept the record. None when nobody read the record, or the build
    has no logged run of the browser tests."""
    history = runs.get("history") or []
    walk_runs = [index for index, run in enumerate(history) if run.get("walks")]
    if lines is None or not walk_runs:
        return None
    walks: dict[str, list] = {}
    own = {index: line_of(history[index], history[:index], lines) for index in walk_runs}
    for index in walk_runs:
        run = history[index]
        for nodeid in (own[index] or {}).get("flaky") or []:
            if run["at"] not in walks.setdefault(str(nodeid), []):
                walks[str(nodeid)].append(run["at"])
    return {"walks": walks, "missing": own[walk_runs[-1]] is None}


def since_result(runs: dict) -> str:
    """green, red or other for the checks run again after the last full run, taken together; green when none was."""
    results = {last["result"] for last in runs["since"].values()}
    return "red" if "red" in results else "green" if results <= {"green"} else "other"


def is_full(run: dict, names: list[str]) -> bool:
    """Whether a run's line is a full run: it lists every configured check and is not a quick run (checks.py --quick,
    which runs the browser tests at one window size) nor a picked run (checks.py --pick, which runs only the tests a
    change could reach), whatever checks such a run lists or happened to run. A line with no `quick` or `picked` field
    was written before such runs existed, and is read as not that kind of run."""
    return not missed(run, names) and run.get("quick") is not True and run.get("picked") is not True


def missed(run: dict, names: list[str]) -> list[str]:
    """The configured checks a run's line does not list."""
    ran = {str(check.get("name")) for check in run.get("checks") or []}
    return [name for name in names if name not in ran]


def missing_proof(repo: pathlib.Path, tip: str, fates: dict[str, dict]) -> dict[str, str]:
    """{finding id: what could not be found} for each fate recorded as fixed: a commit it names must be in the
    repository, and where it names a check, the check's file (the part before ::) must be in the tip commit and a
    commit must be named."""
    found = lambda name: subprocess.run(["git", "cat-file", "-e", name], cwd=repo, capture_output=True).returncode == 0  # noqa: E731 (a one-line helper local to this function)
    missing = {}
    for ident, fate in fates.items():
        check, commit = str(fate.get("check") or "").strip(), str(fate.get("commit") or "").strip()
        if fate.get("fate") != "fixed":
            continue
        lacks = []
        if check and not found(f"{tip}:{check.split('::')[0]}"):
            lacks.append(f"the test's file {check.split('::')[0]} is not in the build's last commit ({tip})")
        if check and not commit:
            lacks.append("no commit is named")
        elif commit and not found(f"{commit}^{{commit}}"):
            lacks.append(f"commit {commit} is not in the repository")
        if lacks:
            missing[ident] = " and ".join(lacks)
    return missing


def state_of(fate: dict | None, lacks: str = "") -> str:
    """Which group a finding belongs to, given its fate line (or None) and what of its proof was not found."""
    kind = str((fate or {}).get("fate") or "")
    if kind == "fixed":
        return "fixed-no-check" if not str(fate.get("check") or "").strip() else "fixed-not-found" if lacks else "fixed"
    return kind if kind in ("left", "not-a-defect") else f"fate: {kind}" if kind else "no-fate"


def join(findings: list[dict], fates: dict[str, dict], missing: dict[str, str] | None = None) -> list[dict]:
    """Each finding with its fate line (None when there is none), its state and what of its proof was not found."""
    joined = []
    for finding in findings:
        ident = str(finding.get("id", ""))
        lacks = (missing or {}).get(ident, "")
        joined.append({**finding, "fate": fates.get(ident), "state": state_of(fates.get(ident), lacks), "lacks": lacks})
    return joined


def group_by_state(joined: list[dict]) -> list[tuple[str, list[dict]]]:
    """The joined findings in groups: no fate first, then any fate the format does not name, then STATES' order.
    Within a group the most serious recorded severity comes first; findings of one severity keep the order they were read in."""
    named, ranks = list(STATES), list(SEVERITIES)
    rank = lambda f: ranks.index(f.get("severity")) if f.get("severity") in ranks else len(ranks)  # noqa: E731 (a one-line helper local to this function)
    order = named[:1] + sorted({f["state"] for f in joined} - set(STATES)) + named[1:]
    groups = [(state, sorted((f for f in joined if f["state"] == state), key=rank)) for state in order]
    return [(state, rows) for state, rows in groups if rows]


def issues(count: int) -> str:
    return f"{count:,} issue{'' if count == 1 else 's'}"


def reason(fate: dict | None) -> str:
    """The reason a fate line gives; one that is only spaces is none."""
    return str((fate or {}).get("why") or "").strip()


def shared_reason(rows: list[dict]) -> str:
    """The one reason every issue of a group gives, when the group has several issues and all give the same one; else ""."""
    whys = {reason(row.get("fate")) for row in rows}
    return whys.pop() if len(rows) > 1 and len(whys) == 1 else ""


def first_sentence(text: str, most: int = 240) -> str:
    """The first sentence of a reason, for quoting; "" when it has no clear end or runs past `most` characters."""
    found = re.match(r"(.+?[.!?])(?=\s|$)", text.strip(), re.S)
    return found.group(1) if found and len(found.group(1)) <= most else ""


def of_the(part: int, total: int) -> str:
    """'all 8' or '3 of the 8'."""
    return f"all {total:,}" if part == total else f"{part:,} of the {total:,}"


def state_said(state: str, rows: list[dict], verified: bool = False, top: bool = False) -> tuple[str, str]:
    """(what the record shows for this group, why that matters and what the owner can do), the last two as one text."""
    what, so, do = state_parts(state, rows, verified, top)
    return what, f"{so} {do}".strip()


def state_parts(state: str, rows: list[dict], verified: bool = False, top: bool = False) -> tuple[str, str, str]:
    """(what the record shows for this group, why that matters to the owner, what they can do about it): whole
    sentences, worded for one issue or for many. What the record claims is said as the record's claim; only FOUND is
    the page's own finding. `top` is for the list at the top of the page, far from the issues: it says where a reason
    is printed in those terms, and quotes how a reason the whole group shares begins."""
    total, one, count = len(rows), len(rows) == 1, issues(len(rows))
    it, each, below = ("it", "it", "the issue below") if one else ("them", "each one", "the issues below")
    once, beside = f"printed once above {below}", f"printed with {below}"
    if top:
        once = beside = f"printed with the issue{'' if one else 's'}, further down this page"
    unreasoned = sum(1 for row in rows if not reason(row.get("fate")))
    blocking = sum(1 for row in rows if row.get("severity") == "blocks")
    same = bool(shared_reason(rows))
    begins = first_sentence(shared_reason(rows)) if top else ""
    begins = f' The reason, which this page did not check, begins: "{begins}"' if begins else ""
    read = "Read the reason" if one or same else "Read each reason"
    do = ""
    if state == "no-fate":
        what = f"The build's record gives no outcome for {count}"
        so = (f"Nothing on record says whether {'this issue' if one else 'any of these issues'} was fixed, left unfixed or judged "
              f"not a defect, so treat {each} as open.")
        do = f"Ask what became of {it} {DECISION}."
    elif state == "left":
        what = f"The record marks {count} as left unfixed"
        if not unreasoned:
            so = (f"The build's record gives the same reason for leaving all {total}, {once}.{begins}" if same else
                  f"The build's record gives a reason for leaving {each}, {beside}.")
            do = f"{read} and decide whether you accept it."
        elif unreasoned == total:
            so, do = f"The build's record gives no reason for leaving {it} unfixed.", "Ask for the reason, then decide whether you accept it."
        else:
            lone = total - unreasoned == 1
            so = (f"The build's record gives no reason for leaving {unreasoned} of the {total} unfixed. "
                  f"{'The reason it does give is' if lone else 'The reasons it does give are'} {beside}.")
            do = f"Read {'it' if lone else 'them'}, ask for the rest, and decide whether you accept each reason."
    elif state == "fixed-not-found":
        what = f"The record marks {count} as fixed, but the proof it gives is incomplete"
        so = (f"The test's file or the commit for the fix was not found, or no commit is named, so this page could not trace "
              f"{'the fix' if one else 'each fix'}. {'The issue' if one else 'Each issue'} says which.")
        do = f"Ask for the missing proof before you count {it} as fixed."
    elif state == "fixed-no-check":
        what = f"The record names no test for {count} it marks as fixed"
        so = (f"So this page can point to no test that shows {'this fix works' if one else 'these fixes work'}, or that the fault "
              "would be caught if it came back. A test may exist that the record does not name.")
        lost = sum(1 for row in rows if row.get("lacks"))
        if lost:
            so += (" This page could not find the commit the record names for the fix." if one else
                   f" This page could not find the commit the record names for {of_the(lost, total)}; each of those issues says which.")
        do = f"{'Try the fix yourself' if one else 'Try the fixes that matter to you'}, or ask for a test{'' if one else ' for each'}."
    elif state == "fixed":
        what = f"The record marks {count} as fixed and names a test for {'it' if one else 'each'}"
        so = f"{'The fix' if one else 'Each fix'} names the test that is meant to show it works."
        whole = sum(1 for row in rows if "::" not in str((row.get("fate") or {}).get("check") or ""))
        if whole:  # a file of tests is weaker proof than one test: the record does not say which test in it shows the fix
            so += (" The record names a whole test file, not one test in it." if one else
                   f" For {of_the(whole, total)}, the record names a whole test file, not one test in it.")
        so += (FOUND_ONE if one else FOUND) if verified else ""
    elif state == "not-a-defect":
        what = f"The record judges {count} not to be a defect"
        so = "This is the build's own judgement, and this page did not check it."
        if unreasoned == total:
            so, do = so + " The record gives no reason.", "Ask for the reason, then decide whether you agree."
        elif unreasoned:
            so += f" The record gives no reason for {unreasoned} of the {total}."
            do = "Read the reasons it does give, ask for the rest, and decide whether you agree."
        else:
            so += (f" The record gives the same reason for all {total}, {once}.{begins}" if same else
                   f" The record gives a reason{'' if one else ' for each'}, {beside}.")
            do = f"{read} and decide whether you agree." if blocking else ""
    else:
        what = f'The record gives {count} an outcome this page does not recognise: "{state.partition(": ")[2]}"'
        so = (f"This page knows three outcomes: fixed, left unfixed and not a defect. This one tells it nothing, so treat "
              f"{'the issue' if one else 'each issue'} as open.")
        do = "Ask for the record to be corrected."
    if blocking and state != "fixed":  # the one severity that changes what the owner does next
        whom = ("it" if one else f"all {total}") if blocking == total else f"{blocking} of the {total}"
        so += f" The reviewer{'' if one else 's'} recorded {whom} as blocking use, which means a user cannot finish a task, or loses data."
    return what, so, do


def state_look(state: str, rows=()) -> tuple[str, str, bool]:
    """(heading, look, drawn open) of a group. Two groups are folded and quiet unless something in them needs the
    owner: issues judged not a defect that a reviewer recorded as blocking use or that give no reason, and fixes with
    no test named whose commit was not found."""
    heading, look, opened = STATES.get(state) or (f'Outcome not recognised ("{state.partition(": ")[2]}")', "bad", True)
    if state == "not-a-defect" and any(row.get("severity") == "blocks" or not reason(row.get("fate")) for row in rows):
        look, opened = "warn", True
    if state == "fixed-no-check" and any(row.get("lacks") for row in rows):
        look, opened = "warn", True
    return heading, look, opened


def orphan_fates(findings: list[dict], fates: dict[str, dict]) -> list[dict]:
    """Fate lines whose id matches no finding."""
    known = {str(f.get("id", "")) for f in findings}
    return [fate for fate_id, fate in fates.items() if fate_id not in known]


def count_by_finder(findings: list[dict]) -> dict[str, dict[str, int]]:
    """{finder: {"first": n, "recheck": n, "other": n}}: the format's finders first, then any other.
    "other" is every pass the format does not name, so a row always adds up to the finder's findings."""
    counts = {finder: {**dict.fromkeys(PASSES, 0), "other": 0} for finder in FINDERS}
    for finding in findings:
        row = counts.setdefault(str(finding.get("finder", "")), {**dict.fromkeys(PASSES, 0), "other": 0})
        which = str(finding.get("pass", ""))
        row[which if which in PASSES else "other"] += 1
    return counts


def wrote(name: str, finder: str) -> bool:
    """Whether a findings file's name says this finder wrote it: 1-walker.jsonl, walker-recheck.jsonl."""
    return bool(re.search(rf"(^|-){re.escape(finder)}(-|\.)", name))


def report_read(files: dict[str, list[dict]], finder: str, which: str) -> bool:
    """Whether a report this review wrote for this round was read: by its rows, or, for an empty file, by its name
    (walker-a-recheck.jsonl is a re-check; any other name is the first round)."""
    for name, rows in files.items():
        if any(str(row.get("finder", "")) == finder and str(row.get("pass", "")) == which for row in rows):
            return True
        if not rows and wrote(name, finder) and ("recheck" in name) == (which == "recheck"):
            return True
    return False


def absent_finders(files: dict[str, list[dict]]) -> list[str]:
    """The format's finders with no findings file at all: none whose rows name it, and none whose name does."""
    named = {str(row.get("finder", "")) for rows in files.values() for row in rows}
    return [finder for finder in FINDERS if finder not in named and not any(wrote(name, finder) for name in files)]


def page_data(feature: str, *, base_ref: str = "", tip_ref: str = "", git: dict | None = None, runs: dict | None = None,
              files: dict[str, list[dict]] | None = None, fates: dict | None = None, missing: dict[str, str] | None = None,
              summary: dict | None = None, recording: dict | None = None, shots=(), built: dict | None = None,
              walk_gap: tuple[int, int] | None = None, copies: list[dict] | None = None, flaky: list[dict] | None = None) -> dict:
    """Everything the page shows, in one dictionary. `files` is read_findings' answer; `missing` is
    missing_proof's, or None when nobody looked for the checks and commits the fates name; `copies` is listeners'
    answer, or None when nobody looked for programs still running; `flaky` is read_flaky's, or None when nobody read the
    walk runner's record."""
    files, fates = files or {}, fates or {}
    findings = [row for rows in files.values() for row in rows]
    joined = join(findings, fates, missing)
    runs = runs or run_facts(None, "")
    return {
        "feature": feature, "base_ref": base_ref, "tip_ref": tip_ref, "git": git,
        "runs": runs, "flaky": flaky_facts(runs, flaky), "summary": summary, "recording": recording, "shots": list(shots),
        "files": files, "findings": joined, "groups": group_by_state(joined), "verified": missing is not None,
        "by_finder": count_by_finder(findings), "absent": absent_finders(files),
        "orphans": orphan_fates(findings, fates), "built": built or {}, "walk_gap": walk_gap, "copies": copies,
    }


def rechecked(data: dict) -> bool:
    """Whether a re-check report was read: an issue names that round, or a report file's name does."""
    return any(str(row.get("pass", "")) == "recheck" for row in data["findings"]) or any("recheck" in name for name in data["files"])


def late_fixes(data: dict) -> tuple[int, int]:
    """(the fixes no review read, every fix). The re-check is the last review a build gets (the build's steps make no
    third round), so a fix for an issue the re-check found was read by no review; with no re-check report, no fix was."""
    fixed = [row for row in data["findings"] if str((row["fate"] or {}).get("fate") or "") == "fixed"]
    late = [row for row in fixed if str(row.get("pass", "")) == "recheck"] if rechecked(data) else fixed
    return len(late), len(fixed)


def late_said(data: dict, after_intro: bool = False) -> str:
    """How many fixes no review read, as a sentence or two: empty when there is none. `after_intro` is for the section
    that has just said no re-check report was read."""
    late, fixed = late_fixes(data)
    if not late:
        return ""
    one, fixes = late == 1, "the fix" if fixed == 1 else f"the {fixed:,} fixes"
    if not rechecked(data):
        lead = "Without one" if after_intro else "This page read no re-check report, so"
        return f"{lead}{',' if after_intro else ''} nothing on record shows that a review read {fixes}."
    which = (f"{fixes.capitalize()} {'is' if one else 'are'}" if late == fixed else f"{late:,} of {fixes} {'is' if one else 'are'}")
    return (f"{which} for {'an issue' if one else 'issues'} the re-check found. The re-check is the last review a build gets, "
            f"so no review read {'this fix' if one else f'these {late:,} fixes'}.")


def left_running(data: dict) -> list[dict]:
    """This project's programs still listening that started after the build's first commit. A build's first commit is
    made before any of its tests runs, so a copy of the app a test started and never stopped is one of these; so is
    the app, if the owner started it during the build. A program started after the build was merged is not the
    build's. Nothing when git gave no first commit to compare with."""
    first, end = (data["git"] or {}).get("first"), (data["git"] or {}).get("merged_at")
    return [copy for copy in data["copies"] or []
            if first and moment(first) <= moment(copy["started"]) and not (end and moment(copy["started"]) > moment(end))]


def ports_said(ports: list[int]) -> str:
    return f"port{'' if len(ports) == 1 else 's'} {listed([str(port) for port in ports])}"


def running_parts(data: dict) -> tuple[str, str, str] | None:
    """(what, why it matters, what the owner can do) for the programs left_running names, or None when there is none."""
    left = left_running(data)
    if not left:
        return None
    pids = " ".join(str(copy["pid"]) for copy in left)
    tests = "The build's tests start copies of the app and should stop each one. This page cannot tell whether the build started"
    if len(left) == 1:
        copy = left[0]
        return ("A program the build may have started is still running",
                f"It is running this project's code, was started at {when(copy['started'])}, after the build's first commit, and is still "
                f"listening on {ports_said(copy['ports'])} (process {copy['pid']}). {tests} this one or you did.",
                f"If you did not start it, stop it: type kill {pids} in a terminal.")
    each = "; ".join(f"process {copy['pid']}, started {when(copy['started'])}, {ports_said(copy['ports'])}" for copy in left)
    return (f"{len(left)} programs the build may have started are still running",
            f"They are running this project's code, were started after the build's first commit and are still listening: {each}. "
            f"{tests} them or you did.", f"If you did not start them, stop them: type kill {pids} in a terminal.")


def running_said(data: dict) -> str | None:
    """This project's programs still listening, counted for the list of numbers: None when nobody looked."""
    copies = data["copies"]
    if copies is None:
        return None
    if not copies:
        return "none"
    if not (data["git"] or {}).get("first"):
        return f"{len(copies)} running; this page cannot tell whether before or during the build"
    left, first = left_running(data), moment(data["git"]["first"])
    named = "; ".join(f"process {copy['pid']}, {ports_said(copy['ports'])}" for copy in left)
    before = sum(1 for copy in copies if moment(copy["started"]) < first)
    counts = ((len(left), f"started during the build ({named})"), (before, "started before the build"),
              (len(copies) - len(left) - before, "started after the build was merged"))
    return "; ".join(f"{count} {words}" for count, words in counts if count)


def same_commit(one, other) -> bool:
    """Whether two abbreviations name one commit: git shortens a commit to different lengths in different places."""
    one, other = str(one or ""), str(other or "")
    return one == other or (min(len(one), len(other)) >= 4 and (one.startswith(other) or other.startswith(one)))


def stale(commit, dirty, tip) -> str:
    """Why a walk or a checks run does not speak for the build's last commit; "" when it does."""
    why = [f"on commit {commit}, not the build's last commit ({tip})"] if tip and not same_commit(commit, tip) else []
    return " and ".join(why + (["with uncommitted changes in the folder"] if dirty else []))


def clean_again(off: str) -> str:
    """Where to ask for a run again: on the last commit, and with nothing uncommitted when that was what was wrong."""
    return AGAIN + (", with nothing uncommitted in the folder" if "uncommitted" in off else "")


def passed_but(off: str) -> str:
    """A tile's few words for a pass that does not speak for the last commit as committed."""
    return "Not shown to pass as committed" if off.startswith("with") else "Not shown to pass on the build's last commit"


FLAKY_MISSING = ("The record of which browser tests failed with the others and passed alone is missing for the last run of "
                 "the browser tests, so this page cannot say whether any did.")
QUICK_RUN = ", a quick run, with the browser tests at one window size"  # checks.py --quick: never a full run
QUICK_SQUARE = " or was a quick run, with the browser tests at one window size"
PICKED_RUN = "a run of only the tests the change could reach"  # checks.py --pick: never a full run, whatever it ran
NOT_LAST = "so it does not show that the build's last commit passes"
NO_FULL_RUN = "No run of every check is logged for this build's branch."
NO_REPORT = ("This page looks for review reports in one place (findings/*.jsonl). Where it finds none from a review, either "
             "the review was not made or its report is somewhere else: this page cannot tell which.")
CHECK_GLOSS = {"lint": "the check of the code for common mistakes",
               "patterns": "the scan for forbidden code patterns", "escapes": "the check of the defect log",
               "unit": "the unit tests", "walks": "the browser tests"}  # checks.py's docstring
DECISION = "before you accept this build"  # the owner's decision (CLAUDE.md, "When the owner accepts a build")
# For a build whose last commit is already part of main: the page's own finding, from git, said under its first sentence.
MERGED = "Nothing is left to accept: what this page lists is for you to know about and, if you choose, ask for."
MERGED_HOW = "This build is already merged: this page found its last commit in main, the project's main line of work."
AGAIN = "on the build's last commit"
ASK = "tell the agent you are working with (a new session opened in this project will do)"
# What accepting sets off: this project's rule (CLAUDE.md, "When the owner accepts a build"), not a fact about one build.
ACCEPTING = ("In this project, when you accept a build the agent pushes the build's branch and opens a pull request, "
             "and you merge it yourself.")


def merged(data: dict) -> bool:
    """Whether git shows the build's last commit in main already. False when git was not read or has no main."""
    return bool((data["git"] or {}).get("merged"))


def undecided(text: str, data: dict) -> str:
    """The text as it stands, or, for a build that is already merged, without "before you accept this build": that
    decision is behind the owner, and the page does not ask for it again."""
    return text.replace(f" {DECISION}", "") if merged(data) else text


def own_walks(recording: dict | None) -> list[dict]:
    """The walks this build added or changed, as recorded; [] when the recording is the standing walk through the whole app."""
    walks = (recording or {}).get("walks")
    return [walk for walk in walks if isinstance(walk, dict) and walk.get("walk")] if isinstance(walks, list) else []


def part_words(walk: dict) -> tuple[str, str]:
    """(title, legend) of one part of the walk-through, as the builder wrote them in hand-over.json."""
    title, legend = str(walk.get("title") or "").strip().rstrip("."), str(walk.get("legend") or "").strip()
    return title or "A part the builder gave no title", legend or "The builder wrote no note saying what this part tests."


def parts_said(count: int) -> str:
    return f"{number(count)} part{'' if count == 1 else 's'}"


def walk_prefix(nodeid: str) -> str:
    """What walks/helper.py names a walk's video and screenshots after (keep_video, shot_name)."""
    return re.sub(r"[^A-Za-z0-9]+", "-", nodeid.split("::", 1)[-1]).strip("-")


def tests_said(count: int) -> str:
    return f"{number(count)} browser test{'' if count == 1 else 's'}"


def gap_said(data: dict) -> str:
    """How far the walk-through's commit is from the build's last commit, as a sentence; "" when the two are one
    commit or git does not know the walk-through's."""
    recording, gap = data["recording"] or {}, data.get("walk_gap")
    if not gap or not any(gap):
        return ""
    ahead, behind = gap
    commits = lambda count: f"{count:,} commit{'' if count == 1 else 's'}"  # noqa: E731 (a one-line helper local to this function)
    commit = recording.get("commit")
    if not behind:
        return (f" Commit {commit} holds the whole build and {commits(ahead)} made after it, which {'is' if ahead == 1 else 'are'} "
                "not part of the build, so the app the walk-through used may differ from the finished build.")
    if not ahead:
        return (f" Commit {commit} is {commits(behind)} before the build's last commit, so the walk-through did not use "
                f"{'that last commit' if behind == 1 else f'the last {commits(behind)}'} of the build.")
    return (f" Commit {commit} is on another line of work: it has {commits(ahead)} the build does not have, and lacks "
            f"the build's last {commits(behind)}.")


def walk_verdict(data: dict) -> tuple[str, str, str]:
    """(look, the verdict as a sentence, the verdict as a tile's few words) for the recorded walk. Green only for a
    pass on the build's last commit, as committed."""
    recording = data["recording"]
    if not recording:
        return "amber", "The walk-through was not run for this page", "Not run for this page"
    result = recording.get("result")
    if result in WALK_ENDS:
        return "red", f"The walk-through {WALK_ENDS[result]}", WALK_ENDS[result].capitalize()
    if result != "passed":
        return "amber", "How the walk-through ended is unknown", "Result unknown"
    off = stale(recording.get("commit"), recording.get("dirty"), (data["git"] or {}).get("tip"))
    if off:
        return "amber", "The build's last commit is not shown to pass the walk-through", passed_but(off)
    return "green", "The walk-through passed", "Passed on the build's last commit"


def checks_verdict(data: dict) -> tuple[str, str, str]:
    """(look, the verdict as a sentence, the verdict as a tile's few words) for the last full run, the last that ran
    every check. Green only for a pass on the build's last commit, as committed."""
    full, after = data["runs"]["full"], since_result(data["runs"])  # after: the checks run again since, in runs of only some
    if full is None or full.get("result") not in ("green", "red"):
        return (("red", "The automated checks failed in their last run", "Failed in their last run") if after == "red" else
                ("amber", "Nothing on record shows whether the build passes the automated checks", "No result on record"))
    if full["result"] == "red":
        return "red", "The automated checks failed", "Failed"
    if after != "green":
        how = "failed" if after == "red" else "did not pass"
        return ("red" if after == "red" else "amber"), f"A later run of only some of the automated checks {how}", f"Passed, then a later partial run {how}"
    off = stale(full.get("tip"), full.get("dirty"), (data["git"] or {}).get("tip"))
    if off:
        return "amber", "The build's last commit is not shown to pass the automated checks", passed_but(off)
    return "green", "The automated checks passed", "Passed on the build's last commit"


def ended(result) -> str:
    """A run's logged result as a verb: passed, failed, or the log's own word for anything else."""
    return RUN_ENDS.get(str(result), f"ended as {result if result else 'unknown'}")


def check_said(name) -> str:
    """A check's name in a sentence: what it is, then the name the log and the chips use."""
    return f"{CHECK_GLOSS[name]} ({name})" if name in CHECK_GLOSS else str(name)


def sentence(text: str) -> str:
    """The text with its first letter a capital, the rest as written."""
    return text[:1].upper() + text[1:]


def later_said(runs: dict) -> str:
    """In words, what the runs of only some checks show since the last run of every check (or, with no such run, in
    the whole log): each check's most recent result and when, then the checks those runs did not run. "" when
    there are none."""
    since = runs["since"]
    if not since:
        return ""
    ran = [f"{check_said(name)} {ended(last['result'])} ({when(last['at'])})" for name, last in since.items()]
    rest = [check_said(name) for name in runs["names"] if name not in since]
    lead = "After the last run of every check, some checks were run again" if runs["full"] else "The log holds runs of only some checks"
    said = f"{lead}: most recently, {listed(ran)}."
    if rest:
        said += f" {sentence(listed(rest))} {'was' if len(rest) == 1 else 'were'} not run {'again' if runs['full'] else 'in them'}."
    return said


def left_said(data: dict, flagged: int = 0) -> tuple[str, str]:
    """(that the build's summary lists things as left for the owner, how many lines and what to do with them; where
    those lines come from and what the page did with them). The first is the link under the page's list and the
    second is said under the fold on how to read the page. The count is of lines, which the script can make without
    judging them. `flagged` is how many things the page itself lists."""
    summary = data["summary"]
    if summary is None:
        return "This build has no summary file (hand-over.json).", ""
    if not any(summary.get(key) for key in ("what", "so_what", "now_what")):
        return "The build's summary file (hand-over.json) is empty.", ""
    count = len(summary.get("now_what") or [])
    one = count == 1
    them = "it" if one else "them"
    if not count:
        return f'The build\'s summary file is shown further down this page, under "{SUMMARY_TITLE}". It lists nothing as left for you.', ""
    said = f"The build's summary file also lists what is left for you: {count} line{'' if one else 's'}, further down this page."
    same = " and the lines quoted at the top of this page come from the same file" if summary.get("what") else ""
    more = (f'The {"line" if one else "lines"} the build\'s summary file (hand-over.json) lists as left for you {"is" if one else "are"} '
            f'under "{SUMMARY_TITLE}"{same}. This page copied {them} as written')
    if not flagged:
        return f"{said} This page did not judge {them}: read {them} {DECISION}.", f"{more}."
    above = "the item above" if flagged == 1 else f"the {flagged} above"
    its = "it" if flagged == 1 else "one of these"
    return (f"{said} This page did not compare {them} with {above}, so read {them} as well.",
            f"{more}: a line there may repeat {its}, explain it or disagree with it.")


def listed(parts: list[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    return " and ".join([", ".join(parts[:-1])] * (len(parts) > 1) + parts[-1:])


# The page's two tests of the whole build, said once, under its first sentence, before either name is used again.
# The checks are listed from checks.py's own list, so a check added there is named here.
TERMS_OWN = ("The walk-through is a recording of the app being used in a real browser (Chromium, 1440 by 900 pixels), "
             "against a stand-in for the outside services the app calls. It shows what this build changed, not the whole app. Each part is one "
             "browser test that this build added or changed and that the builder chose to show; the title and the note on a "
             "part are the builder's words. A change the build wrote no browser test for is not in it. The automated checks "
             f"are the {len(CHECK_NAMES)} checks this project runs with one command: {listed([check_said(name) for name in CHECK_NAMES])}. "
             "Those tests are among the browser tests the checks run; this page judges the walk-through only from its own "
             "recorded run of them, not from a run of the checks.")
TERMS = ("The walk-through is an automated run of one whole journey through the app, by keyboard alone, in a real browser "
         "(Chromium, 1440 by 900 pixels), against a stand-in for the outside services the app calls. The automated checks are the "
         f"{len(CHECK_NAMES)} checks this project runs with one command: {listed([check_said(name) for name in CHECK_NAMES])}. "
         "The walk-through is one of those browser tests; this page judges it only from a recorded run of it on its own, not "
         "from a run of the checks.")
# The three other words the page's first sentences lean on, each said once, under TERMS.
WORDS = ("A commit is one saved step of the work, and the build's last commit is the finished build. The reviewers are "
         "agents that test the running app or read the code; this page reads the issues from their report files. The build's record "
         "is the file (fates.jsonl) that says what became of each issue: fixed, left unfixed, or not a defect.")
SUMMARY_TITLE = "The builder's own summary"
RUNNING = "Programs of this project still running"
NO_REVIEW = "This page found no review report for this build."


def headline_said(count: int, merged: bool = False) -> str:
    """The page's headline: how many things it lists for the owner to look at. main() prints the same words."""
    which = "in this build, which is already merged" if merged else DECISION
    return (f"{count} thing{'' if count == 1 else 's'} to look at {which}" if count else
            f"This page found nothing that needs a second look {which}")


def issues_said(data: dict) -> str:
    """How many issues the reports hold, what the record says happened to them and whether the reports say how serious
    they are, counted here from the record files."""
    found = data["findings"]
    if not found:
        return "The reviewers reported no issues in the reports this page read." if data["files"] else NO_REVIEW
    kinds = [str((f["fate"] or {}).get("fate") or "") for f in found]
    untested = sum(1 for f in found if f["state"] == "fixed-no-check")
    marks = [f"{kinds.count(kind):,} as {words}" for kind, words in OUTCOMES.items() if kinds.count(kind)]
    if untested:  # the part of "fixed" the owner most needs to know, said where the number first appears
        marks[0] += f" ({'' if untested == kinds.count('fixed') else f'{untested:,} of them '}with no test named)"
    other = sum(1 for kind in kinds if kind not in OUTCOMES)
    said = f"The reviewers reported {issues(len(found))} in the reports this page read."
    if marks:
        said += f" The build's record marks {listed(marks)}."
    if other:  # "usable" only when the record does name an outcome and the page cannot read it
        usable = " usable" if any(kind and kind not in OUTCOMES for kind in kinds) else ""
        said += f" {'It' if marks else 'The build' + chr(39) + 's record'} gives no{usable} outcome for {other:,}."
    return f"{said} {severity_said(found)}".strip()


def severity_said(found: list[dict]) -> str:
    """That the reports record no severity for some or all of the issues, so the page cannot say how serious they are:
    empty when every issue has one."""
    total, bare = len(found), sum(1 for row in found if not str(row.get("severity") or "").strip())
    if not bare:
        return ""
    whom = "this issue" if total == 1 else f"any of the {total:,}" if bare == total else f"{bare:,} of the {total:,}"
    return (f"The reviewers' reports record no severity for {whom}, so this page cannot say how serious "
            f"{'it is' if bare == 1 else 'they are'}.")


def proof_said(data: dict) -> str:
    """The page's own conclusion, the first thing read: whether anything on record shows that the build's last commit
    passes its two tests of the whole build. A failure is said first, then what is not shown, then what passed."""
    looks = (("the walk-through", *walk_verdict(data)[:2]), ("the automated checks", *checks_verdict(data)[:2]))
    if all(look == "green" for _, look, _ in looks):
        return "The build's last commit passed the walk-through and the automated checks."
    said = [f"{words}." for _, look, words in looks if look == "red"]
    unshown = [name for name, look, _ in looks if look == "amber"]
    if unshown:
        said.append(f"Nothing on record shows that the build's last commit passes {' or '.join(unshown)}.")
    said += [f"The build's last commit passed {name}." for name, look, _ in looks if look == "green"]
    return " ".join(said)


def e(value) -> str:
    """Any value as text that is safe inside HTML, attributes included."""
    return html.escape(str(value), quote=True)


def minutes(value) -> str:
    """A duration, always in minutes; None is unknown; a fraction too small to show is said, not shown as 0."""
    if value is None:
        return "unknown"
    if isinstance(value, float) and value < 0.05:
        return "under 0.1 minutes"
    number = f"{value:,.1f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"
    return f"{number} minute" + ("" if number == "1" else "s")


def number(value) -> str:
    return "unknown" if value is None else f"{value:,}"


def when(stamp) -> str:
    """An ISO-8601 time as '8 Nov 2026, 16:20 UTC'; None is unknown; anything unreadable is shown as it is."""
    if not stamp:
        return "unknown"
    try:
        utc = moment(stamp).astimezone(datetime.timezone.utc)
    except ValueError:
        return str(stamp)
    return f"{utc.day} {utc:%b %Y, %H:%M} UTC"


# Colours. Green, amber and red are kept for what passed, what needs a look and what failed. The findings bar, the
# lines bar and the squares of the run history use other hues, so a count or an old run is never mistaken for a verdict.
LIGHT = """--bg: #f4f5f7; --card: #ffffff; --ink: #1b2330; --soft: #5a6472; --line: #d9dde3; --accent: #1f5fbf;
  --ok: #0b7a3b; --ok-bg: #e3f4ea; --warn: #8a5a00; --warn-bg: #fdf1d0; --warn-line: #e6c15c; --warn-fill: #f0b323;
  --bad: #a3261a; --bad-bg: #fde7e3; --bad-line: #e2a093; --bad-fill: #d03b3b;
  --fixed: #3f6f9f; --quiet: #aeb6c1; --s1: #2a78d6; --s2: #7a5cc7; --s3: #6b7a8c;"""
DARK = """--bg: #14171c; --card: #1d2128; --ink: #e7eaee; --soft: #9aa5b3; --line: #343b46; --accent: #7fb0f5;
  --ok: #7fdca4; --ok-bg: #16331f; --warn: #f2d27a; --warn-bg: #3a2f10; --warn-line: #6e5a1e; --warn-fill: #e0a51c;
  --bad: #ffb4a6; --bad-bg: #40201b; --bad-line: #7a3a30; --bad-fill: #e05a50;
  --fixed: #6d9fd0; --quiet: #5b6470; --s1: #3987e5; --s2: #9a82e0; --s3: #8a97a8; color-scheme: dark;"""

CSS = (":root { " + LIGHT + " }\n"
       "@media (prefers-color-scheme: dark) { :root:not([data-theme=\"light\"]) { " + DARK + " } }\n"
       ":root[data-theme=\"dark\"] { " + DARK + " }\n") + """
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 66rem; margin: 0 auto; padding-block: 1.5rem 4rem;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1 { font-size: 2.2rem; line-height: 1.15; margin: 0 0 .3rem; overflow-wrap: anywhere; letter-spacing: -.01em; }
h2 { font-size: 1.35rem; margin: 0 0 .5rem; }
h3 { font-size: 1.05rem; margin: 0; }
p { margin: .5rem 0; }
section { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 1.2rem 1.3rem; margin-top: 1.2rem; }
code { font: .88em ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }
a { color: var(--accent); }
button { font: inherit; color: var(--ink); background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: .35rem .9rem; cursor: pointer; }
button:hover { border-color: var(--soft); }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.kicker { text-transform: uppercase; letter-spacing: .08em; font-size: .78rem; font-weight: 600; color: var(--soft); margin: 0; }
.soft, .source, figcaption, dd small, th small { color: var(--soft); font-size: .9rem; }
.lead { font-size: 1.08rem; margin: .5rem 0 0; max-width: 46rem; }
.terms { margin: .4rem 0 0; max-width: 46rem; color: var(--soft); }
.built { border-left: 3px solid var(--line); padding: .1rem 0 .1rem .9rem; margin: .7rem 0 1rem; max-width: 46rem; }
.built summary { cursor: pointer; }
.built .first { display: block; }
.built .more { color: var(--accent); font-size: .9rem; white-space: nowrap; }
.built ul { margin: .3rem 0; padding-left: 1.1rem; }
.built .soft { margin: .2rem 0 0; font-size: .9rem; }
p.built { color: var(--soft); }
.reading { margin-top: .9rem; max-width: 46rem; }
.merged { margin: .2rem 0 0; max-width: 46rem; } .merged .pill { margin-right: .35rem; }
.reading summary, ol.look summary { cursor: pointer; color: var(--soft); font-size: .9rem; width: fit-content; }
.found { margin-top: .9rem; }
th small { display: block; font-weight: 400; max-width: 24rem; }
.source { margin: 0 0 .8rem; }
.source.agent::before { content: "Agents' words"; }
.source.script::before { content: "Counted by this page"; }
.source::before { display: inline-block; margin-right: .5rem; padding: 0 .5rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
  border: 1px solid var(--line); color: var(--ink); }
.source.agent::before { border-color: var(--warn-line); background: var(--warn-bg); color: var(--warn); }
.mark { display: inline-grid; place-items: center; width: 1.7rem; height: 1.7rem; border-radius: 50%; font-weight: 700; line-height: 1;
  background: var(--quiet); color: var(--card); flex: none; }
.green > .mark { background: var(--ok); } .amber > .mark { background: var(--warn-fill); color: #1b1300; } .red > .mark { background: var(--bad-fill); color: #fff; }
.headline { display: flex; align-items: center; gap: .6rem; font-size: 1.35rem; font-weight: 650; margin: 1rem 0 .2rem; }
.headline.green { color: var(--ok); } .headline.amber { color: var(--warn); } .headline.red { color: var(--bad); }
ol.look { list-style: none; margin: .5rem 0 .6rem; padding: 0; counter-reset: look; display: grid; gap: .4rem; }
ol.look li { counter-increment: look; display: flex; align-items: flex-start; gap: .7rem; padding: .55rem .8rem; border-radius: 10px;
  background: var(--warn-bg); border: 1px solid var(--warn-line); }
ol.look li.red { background: var(--bad-bg); border: 2px solid var(--bad-line); }
ol.look .mark { width: 1.4rem; height: 1.4rem; font-size: .85rem; margin-top: .1rem; }
ol.look li > div { min-width: 0; }
ol.look a { color: var(--ink); text-decoration: none; }
ol.look details p { margin: .15rem 0 .1rem; font-size: .9rem; max-width: 46rem; overflow-wrap: anywhere; }
.tile.wide .issues { margin-top: .55rem; max-width: 46rem; }
ol.look a:hover strong { text-decoration: underline; }
ol.look strong::before { content: counter(look) ". "; }
ol.look li.amber strong { color: var(--warn); } ol.look li.red strong { color: var(--bad); }
ol.look .sub { display: block; font-size: .9rem; color: var(--ink); overflow-wrap: anywhere; }
.board { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-top: .9rem; }
.board + .headline { margin-top: 1.3rem; }
.tile { display: grid; grid-template-columns: auto 1fr; gap: .15rem .7rem; align-content: start; padding: 1rem 1.1rem; border-radius: 14px;
  border: 1px solid var(--line); background: var(--card); color: var(--ink); text-decoration: none; min-width: 0; }
.tile > .mark { grid-row: span 3; margin-top: .15rem; }
.tile > * { grid-column: 2; min-width: 0; } .tile > .mark { grid-column: 1; }
.tile .label { text-transform: uppercase; letter-spacing: .08em; font-size: .75rem; font-weight: 600; color: var(--soft); }
.tile strong { font-size: 1.12rem; line-height: 1.3; }
.tile .sub { display: block; font-size: .88rem; color: var(--soft); }
.tile.green { background: var(--ok-bg); border-color: transparent; } .tile.green strong { color: var(--ok); }
.tile.amber { background: var(--warn-bg); border-color: var(--warn-line); } .tile.amber strong { color: var(--warn); }
.tile.red { background: var(--bad-bg); border-color: var(--bad-line); border-width: 2px; } .tile.red strong { color: var(--bad); }
.tile.wide { grid-column: 1 / -1; display: block; }
.tile.wide strong { display: block; font-size: 1.5rem; }
.chk { display: inline-block; margin: .25rem .3rem 0 0; padding: 0 .5rem; border-radius: 999px; font-size: .8rem; font-weight: 600;
  border: 1px solid var(--line); background: var(--card); color: var(--ink); }
.chk.green { background: var(--card); color: var(--ok); border-color: var(--ok); } .chk.red { background: var(--bad-fill); color: #fff; border-color: transparent; }
.bar { display: flex; gap: 2px; height: 1.1rem; margin: .6rem 0 .5rem; }
.bar > * { min-width: 6px; border-radius: 4px; background: var(--quiet); }
.s-bad { background: var(--bad-fill) !important; } .s-left { background: var(--warn-fill) !important; }
.s-lost { background: repeating-linear-gradient(135deg, var(--warn-fill) 0 4px, var(--card) 4px 7px) !important; outline: 1px solid var(--warn-fill); outline-offset: -1px; }
.s-nocheck { background: repeating-linear-gradient(135deg, var(--fixed) 0 4px, var(--card) 4px 7px) !important; outline: 1px solid var(--fixed); outline-offset: -1px; }
.s-fixed { background: var(--fixed) !important; } .s-not { background: var(--quiet) !important; }
.c1 { background: var(--s1) !important; } .c2 { background: var(--s2) !important; } .c3 { background: var(--s3) !important; }
.sw { display: inline-block; width: .7rem; height: .7rem; border-radius: 3px; margin-right: .4rem; vertical-align: -.02rem; background: var(--quiet); }
.unknown, .warned { color: var(--warn); background: var(--warn-bg); border-radius: 4px; padding: 0 .35rem; }
.badly { color: var(--bad); background: var(--bad-bg); border-radius: 4px; padding: 0 .35rem; font-weight: 600; }
.pill { display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 0 .7rem; font-size: .88rem; font-weight: 600;
  color: var(--ink); background: var(--card); text-decoration: none; }
.pill.green { background: var(--ok-bg); color: var(--ok); border-color: transparent; }
.pill.red, .pill.bad { background: var(--bad-bg); color: var(--bad); border-color: var(--bad-line); }
.pill.amber, .pill.warn { background: var(--warn-bg); color: var(--warn); border-color: var(--warn-line); }
.pill.note { border: 1px dashed var(--warn); color: var(--warn); background: var(--card); }
ul.standing { list-style: none; display: flex; flex-wrap: wrap; gap: .45rem; margin: 0; padding: 0; }
video, img { max-width: 100%; height: auto; display: block; border: 1px solid var(--line); border-radius: 8px; background: #000; }
video { width: 100%; }
figure { margin: 0; }
.story .stage { display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: 1rem; }
.story figcaption { margin-top: .4rem; } .story figcaption b { color: var(--ink); margin-right: .4rem; }
.story .film { margin-top: 1rem; } .story .cantplay { display: none; }
.story.nofilm video { display: none; } .story.nofilm .cantplay { display: block; }
.story .clip { margin: 0 0 1.6rem; } .story .clip figcaption { margin: .6rem 0 0; font-size: 1.05rem; color: var(--ink); }
.clip.nofilm video { display: none; } .clip.nofilm .cantplay { display: block; }
.story.live .clip { display: none; margin: 0; } .story.live .clip.on { display: block; }
ol.parts { list-style: none; counter-reset: part; display: flex; flex-wrap: wrap; gap: .5rem; margin: .2rem 0 1rem; padding: 0; }
ol.parts li { counter-increment: part; }
ol.parts a { display: block; padding: .35rem .7rem; border: 1px solid var(--line); border-radius: .5rem; color: var(--ink); text-decoration: none; }
ol.parts a::before { content: counter(part) ". "; color: var(--soft); }
ol.parts a.on { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.story.live .stage { display: block; cursor: pointer; }
.story.live .frame { display: none; } .story.live .frame.on { display: block; }
.story.live .frame figcaption { font-size: 1.05rem; color: var(--ink); }
.story.live[data-view="film"] .stage, .story.live[data-view="film"] .controls, .story.live[data-view="film"] .reel,
.story.live[data-view="pictures"] .film { display: none; }
.story.live .film { margin-top: 0; }
.switch { display: inline-flex; margin-bottom: .8rem; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.switch button { border: 0; border-radius: 0; background: transparent; }
.switch button:focus-visible { outline-offset: -3px; }
.switch button.on { background: var(--ink); color: var(--card); }
.controls { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin-top: .7rem; }
.controls .play { background: var(--ink); color: var(--card); border-color: var(--ink); min-width: 5.5rem; }
.controls .count { color: var(--soft); font-variant-numeric: tabular-nums; margin-left: .3rem; }
.reel { display: flex; gap: .4rem; margin-top: .7rem; overflow-x: auto; padding: 3px; }
.reel .thumb { flex: 1 1 0; min-width: 3.5rem; max-width: 6.4rem; padding: 0; border: 2px solid transparent; border-radius: 8px; overflow: hidden; opacity: .6; background: none; }
.reel .thumb.on { border-color: var(--accent); opacity: 1; }
.reel .thumb img { border: 0; border-radius: 0; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: .9rem; }
.card { border: 1px solid var(--line); border-radius: 12px; padding: .9rem 1rem; min-width: 0; }
.card.next { border: 2px solid var(--accent); }
.card ul { margin: .4rem 0 0; padding-left: 1.1rem; } .card li { margin-top: .35rem; overflow-wrap: anywhere; }
.card details { margin-top: .6rem; } .card details > summary { color: var(--accent); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: .9rem; }
.stat { border: 1px solid var(--line); border-radius: 12px; padding: .8rem .9rem; min-width: 0; }
.stat .value { display: block; font-size: 1.7rem; font-weight: 650; line-height: 1.2; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.stat .value .unknown { font-size: 1.1rem; }
.stat .note { display: block; font-size: .85rem; color: var(--soft); }
.stat.span { grid-column: span 2; }
.legend { display: flex; flex-wrap: wrap; gap: .2rem .9rem; font-size: .85rem; color: var(--soft); }
.runs { display: flex; flex-wrap: wrap; gap: 3px; margin: .5rem 0 .3rem; }
.runs > * { width: .8rem; height: .8rem; border-radius: 3px; background: var(--quiet); }
.runs .r-green { background: var(--fixed); } .runs .r-red { background: var(--bad-fill); }
.runs .part { background: none; border: 2px solid var(--quiet); } .runs .part.r-green { border-color: var(--fixed); } .runs .part.r-red { border-color: var(--bad-fill); }
details.record { margin-top: 1rem; border-top: 1px solid var(--line); padding-top: .8rem; }
dl.facts { margin: .6rem 0 0; }
dl.facts > div { display: grid; grid-template-columns: 14rem 1fr; gap: .2rem 1rem; padding: .55rem 0; border-top: 1px solid var(--line); }
dl.facts > div:first-child { border-top: 0; }
dt { font-weight: 600; }
dd { margin: 0; overflow-wrap: anywhere; }
dd small { display: block; }
dd ul, ul.files { margin: .2rem 0; padding-left: 1.1rem; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; max-width: 38rem; }
th, td { text-align: left; padding: .4rem .8rem .4rem 0; border-top: 1px solid var(--line); }
thead th { border-top: 0; color: var(--soft); font-weight: 600; font-size: .9rem; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; } td.n small { display: block; font-size: .8rem; }
details.group, .orphans { border: 1px solid var(--line); border-radius: 10px; margin-top: .8rem; padding: .6rem .9rem; }
details.group.bad { border: 2px solid var(--bad); background: var(--bad-bg); }
details.group.bad > summary { color: var(--bad); }
details.group.warn, .orphans { border-color: var(--warn-line); background: var(--warn-bg); }
details.group.warn > summary, .orphans > p:first-child { color: var(--warn); }
details.group.note { border: 1px dashed var(--warn); }
details.group.note > summary { color: var(--warn); }
summary { cursor: pointer; font-weight: 600; }
summary h3 { display: inline; }
.why { margin: .5rem 0; max-width: 52rem; }
.sev { display: inline-block; margin-right: .2rem; padding: 0 .45rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
  border: 1px solid var(--line); color: var(--soft); vertical-align: .08rem; }
.sev.blocks { border-color: var(--bad-line); background: var(--bad-bg); color: var(--bad); }
details.trace { margin-top: .35rem; font-size: .88rem; color: var(--soft); }
details.trace > summary { font-weight: 400; }
details.trace dl { margin: .3rem 0 0; }
details.trace dl > div { display: grid; grid-template-columns: 9.5rem 1fr; gap: 0 .8rem; padding: .15rem 0; }
details.trace dt { font-weight: 400; }
details.trace dd { color: var(--ink); }
ol.findings { list-style: none; margin: .6rem 0 0; padding: 0; }
ol.findings > li { background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 8px; padding: .6rem .8rem; margin-top: .5rem; overflow-wrap: anywhere; }
ol.findings p { margin: .15rem 0; }
ol.findings .why { font-size: .93rem; }
footer { color: var(--soft); font-size: .85rem; margin-top: 1.5rem; }
@media (max-width: 600px) {
  body { font-size: 16px; }
  section { padding: .9rem .8rem; }
  dl.facts > div, details.trace dl > div { grid-template-columns: 1fr; }
  .stat.span { grid-column: auto; }
  .board { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
"""

# The picture story's controls. The page is whole without it: with no script every picture is drawn in a grid and
# the recording under them. It loads nothing and sends nothing.
SCRIPT = """
(function () {
  [].forEach.call(document.querySelectorAll('a[href^="#group-"]'), function (a) {
    a.addEventListener("click", function () { var g = document.getElementById(a.getAttribute("href").slice(1)); if (g) { g.open = true; } });
  });
  var story = document.getElementById("story");
  if (!story) { return; }
  var frames = [].slice.call(story.querySelectorAll(".frame"));
  var film = story.querySelector(".film");
  var videos = [].slice.call(story.querySelectorAll("video"));
  var clips = [].slice.call(story.querySelectorAll(".clip"));
  var chips = [].slice.call(document.querySelectorAll("#recording .parts a"));
  var view = function () {}, played = false;
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) { n.className = cls; } if (text) { n.textContent = text; } if (tag === "button") { n.type = "button"; } return n; }
  function part(k) {
    clips.forEach(function (c, i) { c.classList.toggle("on", i === k); });
    chips.forEach(function (c, i) { c.classList.toggle("on", i === k); });
  }
  videos.forEach(function (video, k) {
    var box = video.closest(".clip") || story, from = video.getAttribute("data-frame");
    video.addEventListener("play", function () { played = true; });
    video.addEventListener("ended", function () {  /* the parts play one after another, each held on its last moment first */
      var following = videos[k + 1];
      if (!following || story.getAttribute("data-view") !== "film") { return; }
      setTimeout(function () {
        if (story.getAttribute("data-view") !== "film" || !video.ended) { return; }
        part(clips.indexOf(following.closest(".clip")));
        following.play().catch(function () {});
      }, 1200);
    });
    video.addEventListener("error", function () { box.classList.add("nofilm"); if (!played) { view("pictures"); } });
    if (video.error) { box.classList.add("nofilm"); }
    var still = from !== null ? frames[+from] : (frames.length > 1 ? frames[1] : null);
    if (still) { video.poster = still.querySelector("img").src; }
  });
  if (!frames.length) { return; }
  var at = 0, timer = null;
  var stage = story.querySelector(".stage");
  var bar = el("div", "controls"), back = el("button", "", "Back"), play = el("button", "play", "Play"), next = el("button", "", "Next");
  var count = el("span", "count"), reel = el("div", "reel");
  function show(i) {
    at = (i + frames.length) % frames.length;
    frames.forEach(function (f, k) { f.classList.toggle("on", k === at); });
    if (frames[at].hasAttribute("data-part")) { part(+frames[at].getAttribute("data-part")); }
    [].forEach.call(reel.children, function (t, k) { t.classList.toggle("on", k === at); });
    count.textContent = (at + 1) + " of " + frames.length;
    var t = reel.children[at];
    if (t) { reel.scrollLeft = t.offsetLeft - reel.offsetLeft - (reel.clientWidth - t.offsetWidth) / 2; }
  }
  function stop() { clearInterval(timer); timer = null; play.textContent = "Play"; }
  function start() {
    if (at === frames.length - 1) { show(0); }
    timer = setInterval(function () { if (at === frames.length - 1) { stop(); } else { show(at + 1); } }, 2200);
    play.textContent = "Pause";
  }
  back.onclick = function () { stop(); show(at - 1); };
  next.onclick = function () { stop(); show(at + 1); };
  play.onclick = function () { if (timer) { stop(); } else { start(); } };
  stage.onclick = function () { stop(); show(at + 1); };
  story.addEventListener("keydown", function (ev) {
    if (story.getAttribute("data-view") === "film" || (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft")) { return; }
    ev.preventDefault();
    stop();
    show(at + (ev.key === "ArrowRight" ? 1 : -1));
  });
  frames.forEach(function (f, k) {
    var t = el("button", "thumb"), small = f.querySelector("img").cloneNode(false);
    small.alt = "";
    t.title = f.querySelector("figcaption").textContent;
    t.setAttribute("aria-label", t.title);
    t.appendChild(small);
    t.onclick = function () { stop(); show(k); };
    reel.appendChild(t);
  });
  [back, play, next, count].forEach(function (n) { bar.appendChild(n); });
  stage.parentNode.insertBefore(bar, stage.nextSibling);
  bar.parentNode.insertBefore(reel, bar.nextSibling);
  if (film) {
    var pick = el("div", "switch"), pictures = el("button", "", "Pictures"), recording = el("button", "", "Recording");
    view = function (which) {
      story.setAttribute("data-view", which);
      pictures.classList.toggle("on", which === "pictures");
      recording.classList.toggle("on", which === "film");
      if (which === "film") { stop(); } else { videos.forEach(function (video) { video.pause(); }); }
    };
    pictures.onclick = function () { view("pictures"); };
    recording.onclick = function () { view("film"); };
    pick.appendChild(pictures);
    pick.appendChild(recording);
    story.insertBefore(pick, story.firstChild);
    if (clips.length > 1) { film.insertBefore(el("p", "soft", "Press play once and the parts follow one another. Choose a part above to jump to it."), film.firstChild); }
    chips.forEach(function (chip, k) {
      chip.addEventListener("click", function (ev) {
        var from = chip.getAttribute("data-frame"), mine = clips[k] ? clips[k].querySelector("video") : null;
        ev.preventDefault();
        stop();
        videos.forEach(function (video) { video.pause(); });
        if (from !== null) { show(+from); } else { part(k); }
        if (story.getAttribute("data-view") === "film" && mine) { mine.currentTime = 0; mine.play().catch(function () {}); }
      });
    });
    view(story.hasAttribute("data-film") && !videos.some(function (video) { return video.error; }) ? "film" : "pictures");
  }
  if (frames.length < 2) { bar.style.display = "none"; reel.style.display = "none"; stage.onclick = null; stage.style.cursor = "auto"; }
  story.classList.add("live");
  show(0);
  if (clips.length && story.getAttribute("data-view") === "film") { part(0); }
}());
"""

TONES = {"green": "green", "amber": "amber", "warn": "amber", "note": "amber", "red": "red", "bad": "red"}
MARKS = {"green": "&#10003;", "amber": "!", "red": "&#215;", "": "&#183;"}
SEGMENTS = {"no-fate": "s-bad", "left": "s-left", "fixed-not-found": "s-lost", "fixed-no-check": "s-nocheck",
            "fixed": "s-fixed", "not-a-defect": "s-not"}


def unknown(text: str = "unknown") -> str:
    return f'<span class="unknown">{e(text)}</span>'


def mark(tone: str) -> str:
    """The round sign beside a verdict: a tick, an exclamation mark or a cross, so the colour never speaks alone."""
    return f'<span class="mark" aria-hidden="true">{MARKS[tone]}</span>'


def pill(text, look: str = "", href: str = "", swatch: str = "") -> str:
    """A rounded label. `look` is one of this script's own words (green, red, amber, bad, warn, note), never read text."""
    square = f'<i class="sw {swatch}"></i>' if swatch else ""
    return (f'<a class="pill {look}" href="{e(href)}">{square}{e(text)}</a>' if href
            else f'<span class="pill {look}">{square}{e(text)}</span>')


def fact(label: str, value_html: str, source: str) -> str:
    """One row of the facts: the label, the value (already HTML) and where it came from."""
    return f"<div><dt>{e(label)}</dt><dd>{value_html}<small>{e(source)}</small></dd></div>"


def walk_why(data: dict) -> tuple[str, str]:
    """(why the walk-through is not drawn as passed, what the owner can do about it)."""
    recording = data["recording"]
    if not recording:
        return ("There is no recording and there are no pictures, so this page does not show the app being used.",
                "Ask for this page to be built again with the walk-through.")
    off = stale(recording.get("commit"), recording.get("dirty"), (data["git"] or {}).get("tip"))
    if recording.get("result") in WALK_ENDS:
        shows = ("So this page does not show that what the build changed works in a browser." if own_walks(recording)
                 else "So nothing on this page shows that the app can be used from start to finish.")
        said = ((f"{recording['reason']}. " if recording.get("reason") else "") + shows
                + " What the run printed is in walk-output.txt, beside this page.")
        if off:
            return (f"{said} It was started {off}, so it does not show whether the build's last commit fails either.",
                    f"Ask for it to be run again {clean_again(off)}.")
        return said, f"Ask for this to be looked into {DECISION}."
    if recording.get("result") != "passed":
        return "Its record (recording.json) does not say how it ended.", f"Ask for it to be run again {AGAIN}."
    return f"The walk-through passed, but {off}.{gap_said(data)}", f"Ask for it to be run again {clean_again(off)}."


def checks_why(data: dict) -> tuple[str, str]:
    """(why the automated checks are not drawn as passed, what the owner can do about it)."""
    runs = data["runs"]
    full, later = runs["full"], later_said(runs)
    rerun = f"Ask for every check to be run {AGAIN}."
    if full is None:
        return (later, rerun) if later else (
            f"{runs['why_unknown'] or NO_FULL_RUN} Either the checks were never run for this build or the run was not logged: this page "
            "cannot tell which.", rerun)
    if full.get("result") not in ("green", "red"):
        return "The log of check runs does not say how the last run of every check ended.", rerun
    off = stale(full.get("tip", "unknown"), full.get("dirty"), (data["git"] or {}).get("tip"))
    if full["result"] == "red":
        checks_ = full.get("checks") or []
        red = [check_said(check.get("name", "?")) for check in checks_ if check.get("result") == "red"]
        skipped = [check_said(check.get("name", "?")) for check in checks_ if check.get("result") == "not run"]
        rest = f" {sentence(listed(skipped))} {'was' if len(skipped) == 1 else 'were'} not run after that." if skipped else ""
        failed = f"The last run of every check failed{f' at {listed(red)}' if red else ''}.{rest}{' ' + later if later else ''}"
        if off:
            return (f"{failed} That run was {off}, so it does not show whether the build's last commit fails.",
                    f"Ask for every check to be run {clean_again(off)}.")
        return failed, f"Ask for the failure to be fixed {DECISION}."
    if later and since_result(runs) != "green":
        return later, rerun
    return f"The last run of every check passed, but {off}.", f"Ask for every check to be run {clean_again(off)}."


def to_look_at(data: dict) -> list[tuple[str, str, str, str, str]]:
    """(amber or red, what, why it matters, what the owner can do, where on the page) for each thing the owner should look
    at before accepting the build: the walk-through, the automated checks, a range that holds no commit, each group of
    issues the record does not show as fixed with a test or as not a defect, each review whose report was not found,
    outcomes matching no issue, and review rounds not recognised. Red comes first. The headline counts this list and
    the page prints it, so the two cannot disagree."""
    things = [(TONES.get(walk_verdict(data)[0], ""), walk_verdict(data)[1], *walk_why(data), "#recording"),
              (TONES.get(checks_verdict(data)[0], ""), checks_verdict(data)[1], *checks_why(data), "#facts")]
    if flaky_parts(data):
        things.append(("amber", *flaky_parts(data), "#facts"))
    facts = data["git"]
    if facts and not facts["commits"]:
        things.append(("amber", "This page covers no commits",
                       f"The range it was asked for ({facts['base']}..{facts['tip']}) holds no commit, so its numbers describe no "
                       "build.", "Ask for this page to be built again from the build's first commit to its last.", "#facts"))
    if running_parts(data):
        things.append(("amber", *running_parts(data), "#facts"))
    for index, (state, rows) in enumerate(data["groups"]):
        things.append((TONES.get(state_look(state, rows)[1], ""), *state_parts(state, rows, top=True), f"#group-{index}"))
    if not data["files"]:
        kinds = listed([name.lower() for name in FINDERS.values()])
        things.append(("amber", NO_REVIEW.rstrip("."),
                       f"It looks for the reports of the build's reviews ({kinds}) in one place (findings/*.jsonl) and found none. "
                       "Either no review was made or the reports are somewhere else: this page cannot tell which, so nothing on "
                       "this page shows that anyone tested or read the build.",
                       f"Ask whether the reviews were made; if they were not, decide whether you want them made {DECISION}.", "#finders"))
    for finder in data["absent"] if data["files"] else ():
        note = FINDER_NOTES[finder]
        want = ("it can now only be made late, on the finished build: decide whether you want that" if finder == "early-read"
                else "decide whether you want it made")
        things.append(("amber", f"This page found no report from the {FINDERS[finder].lower()}",
                       f"{NO_REPORT} In this review, {note[0].lower()}{note[1:]}",
                       f"Ask whether it was made. If it was not, {want} {DECISION}.", "#finders"))
    if data["orphans"]:
        count = len(data["orphans"])
        one = count == 1
        things.append(("amber", f"The record gives {'an outcome' if one else 'outcomes'} for {issues(count)} that "
                                f"{'is' if one else 'are'} in no review report this page read",
                       f"So {'an issue' if one else 'issues'} may have been reported somewhere this page does not look.",
                       f"Ask where {'it was' if one else 'they were'} reported.", "#findings"))
    if odd_passes(data):
        count = odd_passes(data)
        one = count == 1
        things.append(("amber", f"{issues(count).capitalize()} {'does' if one else 'do'} not name a review round this page recognises",
                       f"An issue belongs to the first review or to the re-check after the fixes. {'This one names' if one else 'These name'} "
                       f"neither, so {'it is' if one else 'they are'} counted apart, in a column of {'its' if one else 'their'} own "
                       "in the review table.", "Ask for the record to be corrected.", "#finders"))
    flagged = [thing for thing in things if thing[0] in ("amber", "red")]
    return sorted(flagged, key=lambda thing: thing[0] != "red")  # a sort that keeps the order within each look


def walk_said(nodeid: str) -> str:
    """A browser test's name in words, from its test function's name and its window size: "A saved form keeps its
    values, at 1440 by 900 pixels" for walks/test_x.py::test_a_saved_form_keeps_its_values[1440x900]."""
    name, _, params = nodeid.split("::")[-1].partition("[")
    words = sentence(name.removeprefix("test_").replace("_", " ").strip()) or nodeid
    sizes = [re.sub(r"^(\d+)x(\d+)$", r"at \1 by \2 pixels", piece) if re.fullmatch(r"\d+x\d+", piece) else f"in {piece}"
             for piece in params.rstrip("]").split("-") if piece]
    return ", ".join([words, *sizes])


def flaky_parts(data: dict) -> tuple[str, str, str] | None:
    """(what, why it matters, what the owner can do) for the browser tests that were red with the others and green
    alone in the build's runs: None when the record names none. Each test is named in words under the fold, with its
    name in the code after it."""
    walks = (data.get("flaky") or {}).get("walks")
    if not walks:
        return None
    one = len(walks) == 1
    named = "; ".join(f"{walk_said(nodeid)} ({nodeid}), in the run{'' if len(ats) == 1 else 's'} of {listed([when(at) for at in ats])}"
                      for nodeid, ats in walks.items())
    return (f"{tests_said(len(walks))} failed when run with the others and passed when run alone",
            f"{'The test' if one else 'The tests'}: {named}. Run alone, {'it' if one else 'each'} passed, so the automated checks "
            f"counted {'it' if one else 'them'} as passed. A test that fails only when others run at the same time may point to a "
            "fault in the app that shows when it is busy, or to a fault in the test itself: this page cannot tell which. These "
            f"come from the browser tests' own record of each run ({data['feature']}/walks/{FLAKY_RECORD} under .scratch/).",
            f"Ask for {'it' if one else 'each'} to be looked into {DECISION}.")


def odd_passes(data: dict) -> int:
    """How many findings name a pass the format does not."""
    return sum(row["other"] for row in data["by_finder"].values())


def tile(look: str, label: str, words: str, sub_html: str, href: str) -> str:
    """One of the two verdict tiles: a sign, what it is, the verdict in a few words, and the facts of the run under it."""
    tone = TONES.get(look, "")
    return (f'<a class="tile {tone}" href="{e(href)}">{mark(tone)}<span class="label">{e(label)}</span>'
            f"<strong>{e(words)}</strong>{sub_html}</a>")


def render_walk_tile(data: dict) -> str:
    recording = data["recording"] or {}
    stopped = recording.get("result") in WALK_ENDS  # an attempt that failed, did not start or was stopped did not "run for" a time
    took = (f'{"Ended after" if stopped else "Ran for"} {e(minutes(recording["minutes"]))}, on' if recording.get("minutes") is not None
            else f'How long it ran was not recorded. It {"was started" if stopped else "ran"} on')
    own = own_walks(recording)
    shown = f"A recording of what this build changed, in {parts_said(len(own))}. " if own else ""
    sub = (f'<span class="sub">{shown}{took} commit <code>{e(recording.get("commit", "unknown"))}</code></span>'
           if recording else '<span class="sub">There is no recording and there are no pictures</span>')
    look, _, short = walk_verdict(data)
    off = stale(recording.get("commit"), recording.get("dirty"), (data["git"] or {}).get("tip")) if recording.get("result") == "passed" else ""
    if off and recording.get("commit"):
        ran = f' It ran for {e(minutes(recording["minutes"]))}.' if recording.get("minutes") is not None else ""
        sub = (f'<span class="sub">{shown}It passed on commit <code>{e(recording["commit"])}</code>'
               f'{", with uncommitted changes in the folder" if recording.get("dirty") else ""}.{ran}</span>')
    return tile(look, "Walk-through", short, sub, "#recording")


def chip(name) -> str:
    """A check's name on a chip or in a list: what it is, then the name the log uses."""
    return check_said(name).removeprefix("the ")


def render_checks_tile(data: dict) -> str:
    runs, tip = data["runs"], (data["git"] or {}).get("tip")
    full, later = runs["full"], later_said(runs)
    look, _, short = checks_verdict(data)
    sub = ""
    if full is None:
        sub += f'<span class="sub">{e(runs["why_unknown"] or NO_FULL_RUN)}</span>'
    else:
        off = stale(full.get("tip", "unknown"), full.get("dirty"), tip)
        looks = {"green": "green" if look == "green" else "", "red": "red"}  # a check is drawn green only when the verdict is
        each = "".join(f'<span class="chk {looks.get(str(check.get("result")), "")}">{e(chip(check.get("name", "?")))}: '
                       f'{e(RUN_ENDS.get(str(check.get("result")), check.get("result", "unknown")))}</span>' for check in full.get("checks") or [])
        sub += f'<span class="sub">{each}</span><span class="sub">The last full run took {e(minutes(full.get("minutes")))}</span>'
        sub += f'<span class="sub">This run was {e(off)}.</span>' if off else ""
    if later and (full is None or since_result(runs) != "green"):  # said on the tile, not only in the folded list
        sub += f'<span class="sub">{e(later)}</span>'
    if (data.get("flaky") or {}).get("missing"):  # said, not counted: a build may predate the record
        sub += f'<span class="sub">{e(FLAKY_MISSING)}</span>'
    return tile(look, "Automated checks", short, sub, "#facts")


def render_findings_tile(data: dict) -> str:
    """The issues as one bar, a part for each outcome the record gives, and a label for each part that links to its list."""
    items, bar = [], ""
    if data["findings"]:
        parts = []
        for index, (state, rows) in enumerate(data["groups"]):
            title, look = state_look(state, rows)[:2]
            swatch = SEGMENTS.get(state, "s-bad")
            parts.append(f'<span class="{swatch}" style="flex-grow: {len(rows)}" title="{e(title)}: {len(rows)}"></span>')
            items.append(pill(f"{title}: {len(rows)}", look, f"#group-{index}", swatch))
        count = len(data["findings"])
        said = f"{number(count)} reported"
        bar = f'<div class="bar" role="img" aria-label="{e(said)}, by the outcome the build recorded for each">{"".join(parts)}</div>'
    else:
        count = len(data["files"])
        said = "None reported" if count else "No review report found"
        items.append(pill(f"No issues in the {count} report{'' if count == 1 else 's'} read" if count
                          else "No review report found", "" if count else "amber", "#finders"))
    if late_fixes(data)[0]:  # said beside the outcomes, and not a colour: it is a count, not a verdict
        items.append(pill(f"Fixed after the last review: {late_fixes(data)[0]}", "", "#finders"))
    items += [pill(f"{FINDERS[finder]}: no report found", "amber", "#finders") for finder in data["absent"]]
    if data["orphans"]:
        items.append(pill(f"Outcomes matching no issue: {len(data['orphans'])}", "amber", "#findings"))
    if odd_passes(data):
        items.append(pill(f"Review round not recognised: {odd_passes(data)}", "amber", "#finders"))
    return (f'<div class="tile wide"><span class="label">Issues the reviewers reported, by recorded outcome</span>'
            f'<strong>{e(said)}</strong>{bar}<ul class="standing">{"".join(f"<li>{item}</li>" for item in items)}</ul>'
            + (f'<span class="sub issues">{e(severity_said(data["findings"]))}</span>' if severity_said(data["findings"]) else "") + "</div>")


WHY = "Why this matters"


def render_look(tone: str, what: str, so: str, do: str, href: str) -> str:
    """One thing to look at: what it is and what the owner can do, with why it matters one click under them. A thing
    with nothing to do shows its why in that place."""
    shown, folded = (do, so) if do else (so, "")
    why = f"<details><summary>{WHY}</summary><p>{e(folded)}</p></details>" if folded else ""
    return (f'<li class="{tone}">{mark(tone)}<div><a href="{e(href)}"><strong>{e(what)}</strong></a>'
            f'<span class="sub">{e(shown)}</span>{why}</div></li>')


def list_said(count: int) -> str:
    """Where the page's own list comes from and that each item links on: said under the fold on how to read the page."""
    if count == 1:
        return ("This page worked this out itself, from git and from the build's record files: it is not taken "
                "from the builder's summary. It links to the part of this page that shows it.")
    return (f"This page worked out these {count} itself, from git and from the build's record files: they are "
            "not taken from the builder's summary. Each one links to the part of this page that shows it.")


def render_standing(data: dict) -> str:
    """The board under the page's first sentence, drawn before anything is explained: the walk-through, the last full
    run of the checks and the issues as tiles; then how many things need a look before the owner accepts the build,
    each with what it is and what the owner can do, and whom to tell; then where the builder's own list is."""
    flagged = [(tone, what, undecided(so, data), undecided(do, data), href) for tone, what, so, do, href in to_look_at(data)]
    count, done = len(flagged), merged(data)
    accept = "" if done else f" {e(ACCEPTING)}"
    if flagged:
        worst = "red" if any(tone == "red" for tone, *_ in flagged) else "amber"
        rows = "".join(render_look(*thing) for thing in flagged)
        headline = (f'<p class="headline {worst}">{mark(worst)}{e(headline_said(count, done))}</p>'
                    f'<ol class="look">{rows}</ol><p>To ask for any of this{"" if done else ", or to accept the build"}, {ASK}.{accept}</p>')
    else:
        settled = "the reviewers reported no issues in the reports this page read"
        if data["findings"]:
            settled = ("every reported issue is recorded either as not a defect or as fixed, each fix naming the test meant to "
                       "show it works. The outcomes are the build's own record: this page did not test the fixes")
            judged = sum(len(rows) for state, rows in data["groups"] if state == "not-a-defect")
            if judged:  # each gives a reason and none is rated as blocking use, or the group would be listed above
                settled += (f". {issues(judged).capitalize()} {'is' if judged == 1 else 'are'} judged not a defect: that is the "
                            "build's own judgement, which this page did not check")
        headline = (f'<p class="headline green">{mark("green")}{e(headline_said(0, done))}</p>'
                    "<p class=\"soft\">This page checked: the walk-through and the automated checks passed on the build's last commit, "
                    f"and {settled}.{' ' + e(late_said(data)) if late_said(data) else ''}</p>" + ("" if done else f"<p>To accept the build, {ASK}.{accept}</p>"))
    headline += f'<p class="soft"><a href="#summary">{e(undecided(left_said(data, count)[0], data))}</a></p>'
    return f'<div class="board">{render_walk_tile(data)}{render_checks_tile(data)}{render_findings_tile(data)}</div>{headline}'


def render_built(data: dict) -> str:
    """What was built, under the title, in the builder's own words: the one place the header prints an agent's words,
    because nothing the page computes can say what a build is for. Its label says whose words they are and that the
    page did not check them; the first line shows, and the rest and where they come from open under it. No colour,
    count or item of the page's own list reads them."""
    summary = data["summary"]
    lines = (summary or {}).get("what") or []
    if not lines:
        why = ("the build has no summary file (hand-over.json is missing)" if summary is None
               else 'the build\'s summary file (hand-over.json) has nothing under "what"')
        return f'<p class="built">This page cannot say what was built: {e(why)}.</p>'
    one, rest = len(lines) == 1, len(lines) - 1
    more = f' <span class="more">and {rest} more line{"" if rest == 1 else "s"}</span>' if rest else ""
    return ('<details class="built"><summary><span class="kicker">What was built, in the builder\'s words, not checked by this page</span>'
            f'<span class="first">{e(lines[0])}{more}</span></summary>'
            + (f'<ul>{"".join(f"<li>{e(line)}</li>" for line in lines[1:])}</ul>' if rest else "")
            + f'<p class="soft">{"This line comes" if one else "These lines come"} from the build\'s summary file (hand-over.json), '
            f'which the agent that runs a build is meant to write. This page copied {"it" if one else "them"} as written and did '
            f'not check {"it" if one else "them"}.</p></details>')


READING = "How to read this page, and what its words mean"


def render_header(data: dict) -> str:
    """The first thing read, and seen before it is read: what was built, in one line of the builder's words; the page's
    own conclusion in one sentence; the tiles; and the list of what needs a look. What the page's words mean and where
    its list comes from open under one fold, so nothing has to be read to reach the tiles. How large the build is and
    which commits the page covers come last, as reference."""
    facts = data["git"]
    if facts:
        count, first, last = facts["commits"], when(facts["first"]), when(facts["last"])
        made = ("This build has no commits yet." if not count else
                f"The build is {e(number(count))} commit{'' if count == 1 else 's'}, made "
                + (f"on {e(first)}." if first == last else f"between {e(first)} and {e(last)}."))
        asked = f" (asked for as {e(data['base_ref'])} to {e(data['tip_ref'])})" if data["base_ref"] else ""
        covers = f"{made} For reference, this page covers commits <code>{e(facts['base'])}..{e(facts['tip'])}</code>{asked}."
    else:
        covers = f"The range of commits this page covers is {unknown()}."
    merged_said = f'<p class="merged"><span class="pill">Already merged</span> {e(MERGED)}</p>' if merged(data) else ""
    how = f'<p class="terms">{e(MERGED_HOW)}</p>' if merged(data) else ""
    left = left_said(data, len(to_look_at(data)))[1]
    more = f'<p class="terms">{e(left)}</p>' if left else ""
    listed_ = len(to_look_at(data))
    own = f'<p class="terms">{e(list_said(listed_))}</p>' if listed_ else ""
    reading = (f'<details class="reading"><summary>{READING}</summary><p class="terms">{e(TERMS_OWN if own_walks(data["recording"]) else TERMS)}</p>'
               f'<p class="terms">{e(WORDS)}</p>{how}{own}{more}</details>')
    return (f'<header><p class="kicker">Build hand-over</p><h1>{e(data["feature"])}</h1>{render_built(data)}'
            '<p class="kicker found">What this page found, from git and the build\'s records</p>'
            f'<p class="lead"><strong>{e(proof_said(data))}</strong></p>{merged_said}'
            f'{render_standing(data)}{reading}<p class="soft">{covers}</p></header>')


def shot_parts(shot) -> tuple[str, str]:
    """(caption, address) of one screenshot. A shot is its file name, or {"name", "src"} when the picture is inside the page."""
    name = shot["name"] if isinstance(shot, dict) else str(shot)
    step = re.search(r"-(\d\d)-(.+)\.png$", name)
    caption = f"Step {int(step.group(1))}: {step.group(2).replace('-', ' ')}" if step else name
    return caption, shot["src"] if isinstance(shot, dict) else "shots/" + urllib.parse.quote(name)


def render_parts(data: dict, own: list[dict], said: list[str]) -> str:
    """The walk-through of what the build changed: one recording in parts, each part under the builder's title and
    legend, and the same parts as pictures. Without script every part is drawn, one under another."""
    recording, total = data["recording"], len(own)
    look, _, short = walk_verdict(data)
    passed, filmed = recording.get("result") == "passed", recording.get("megabytes") is not None
    prefixes = [walk_prefix(walk["walk"]) for walk in own]

    def part_of(shot) -> int:
        """Which part a screenshot is from, by its file name; after them all when from none."""
        name = shot["name"] if isinstance(shot, dict) else str(shot)
        mine = [index for index, prefix in enumerate(prefixes) if name.startswith(prefix)]
        return max(mine, key=lambda index: len(prefixes[index])) if mine else total

    def ended(walk: dict) -> str:
        """How one part ended, said only when the run as a whole did not pass: a pass needs no word on each part."""
        if passed:
            return ""
        result = walk.get("result")
        words = {"passed": "This part passed.", "failed": "This part failed.", "did not run": "This part did not run."}
        return f' <span class="soft">{words[result]}</span>' if result in words else f" {unknown('How this part ended was not recorded.')}"

    shots = sorted(data["shots"], key=part_of)  # in the parts' order; sorted() keeps each part's pictures in theirs
    per = [sum(1 for shot in shots if part_of(shot) == index) for index in range(total)]
    frames, first, seen = [], {}, [0] * total
    for index, shot in enumerate(shots):
        plain, src = shot_parts(shot)
        part = part_of(shot)
        lazy = ' loading="lazy"' if index and not src.startswith("data:") else ""  # only a picture that is a file can wait
        if part == total:
            frames.append(f'<figure class="frame"><img src="{e(src)}" alt="{e(plain)}"{lazy}><figcaption>{e(plain)}</figcaption></figure>')
            continue
        first.setdefault(part, index)
        seen[part] += 1
        title, legend = part_words(own[part])
        lead, which = f"Part {part + 1} of {total}. {title}.", f"Picture {seen[part]} of {per[part]} from this part."
        frames.append(f'<figure class="frame" data-part="{part}"><img src="{e(src)}" alt="{e(lead)} {e(which)}"{lazy}>'
                      f'<figcaption><b>{e(lead)}</b> {e(legend)} <span class="soft">{which}</span></figcaption></figure>')
    stage = f'<div class="stage">{"".join(frames)}</div>' if frames else "<p>No pictures: the walk-through left none.</p>"
    chips, clips = [], []
    for index, walk in enumerate(own):
        title, legend = part_words(walk)
        still = f' data-frame="{first[index]}"' if index in first else ""
        chips.append(f'<li><a href="#part-{index + 1}" data-part="{index}"{still}>{e(title)}</a></li>')
        videos = "".join(
            f'<video controls preload="metadata" src="{e(src)}"{still}></video><p class="soft cantplay">This window cannot play this '
            f'part. Open <a href="{e(src)}">its video file</a>, which is beside this page, in Safari or Chrome.</p>'
            for src in ("clips/" + urllib.parse.quote(str(clip)) for clip in walk.get("clips") or []))
        clips.append(f'<figure class="clip" id="part-{index + 1}" data-part="{index}">{videos or "<p>This part left no video.</p>"}'
                     f"<figcaption><b>Part {index + 1} of {total}. {e(title)}.</b> {e(legend)}{ended(walk)}</figcaption></figure>")
    film = f'<div class="film">{"".join(clips)}</div>' if filmed else ""
    one = total == 1
    about = ((f"One recording{'' if one else f' in {parts_said(total)}'}." if filmed else
              f"{parts_said(total).capitalize()}, in pictures only: the walk-through left no video.")
             + (f" {'It' if one else 'Each part'} shows {'what' if one else 'one thing'} this build changed, in a real browser, and the "
                f"note under {'it' if one else 'each part'} says what is being tested.")
             + ("" if passed else f" The run did not pass: {'the part says how it' if one else 'each part says how it'} ended."))
    left = [str(name) for name in recording.get("left_out") or []]
    if left:
        said.append(f"The build changed {number(len(left))} other browser test{'' if len(left) == 1 else 's'} and left "
                    f"{'it' if len(left) == 1 else 'them'} out of this recording.")
    behind = "".join(f"<li>Part {index + 1}: <code>{e(walk['walk'])}</code></li>" for index, walk in enumerate(own))
    behind += "".join(f"<li>Changed by the build and left out of the recording: <code>{e(name)}</code></li>" for name in left)
    return (f'<section id="recording"><h2>The walk-through: what this build changed</h2><p>{pill(short, look)} {about}</p>'
            f'<ol class="parts">{"".join(chips)}</ol>'
            f'<div class="story" id="story" tabindex="-1"{" data-film" if filmed else ""}>{stage}{film}</div>'
            '<p class="source agent">The title and the note on each part are the builder\'s words. This page copied them as written and '
            "did not check them against what the part shows.</p>"
            f'<p class="soft">{" ".join(said)}</p>'
            f'<details class="record"><summary>The browser test behind each part</summary><ul class="files">{behind}</ul></details></section>')


def render_recording(data: dict) -> str:
    """The walk: its verdict, its screenshots as a picture story, and the recording."""
    recording, head = data["recording"], '<section id="recording"><h2>The walk-through, in pictures</h2>'
    if not recording:
        return head + ("<p>No recording: the walk-through was not run for this page.</p>"
                       "<p>No screenshots: the walk-through was not run for this page.</p></section>")
    look, _, short = walk_verdict(data)
    megabytes, tip, commit = recording.get("megabytes"), (data["git"] or {}).get("tip"), recording.get("commit", "unknown")
    said = [f'Run {e(when(recording.get("at")))} on commit <code>{e(commit)}</code>'
            f'{", with uncommitted changes in the folder" if recording.get("dirty") else ""}.']
    if tip and not same_commit(commit, tip):
        said.append(f"That is not the last commit of the build ({e(tip)}): the walk-through ran on the code that was in the folder at the time.")
    if recording.get("reason"):
        said.append(f'{e(recording["reason"])}.')
    if recording.get("result") != "passed":
        said.append('What it printed is in <a href="walk-output.txt"><code>walk-output.txt</code></a>, beside this page.')
    took, size = recording.get("minutes"), f"; the recording is {e(megabytes)} MB" if megabytes is not None else ""
    stopped = recording.get("result") in WALK_ENDS
    said.append(f'How long it ran was not recorded{size}.' if took is None else
                f'{"The attempt ended after" if stopped else "It ran for"} {e(minutes(took))}{size}.')
    own = own_walks(recording)
    if own:
        return render_parts(data, own, said)
    frames = []
    for index, shot in enumerate(data["shots"]):
        caption, src = shot_parts(shot)
        lazy = ' loading="lazy"' if index and not src.startswith("data:") else ""  # only a picture that is a file can wait
        frames.append(f'<figure class="frame"><img src="{e(src)}" alt="{e(caption)}"{lazy}>'
                      f"<figcaption>{e(caption)}</figcaption></figure>")
    stage = f'<div class="stage">{"".join(frames)}</div>' if frames else "<p>No screenshots: the walk-through left none.</p>"
    film = ('<div class="film"><video controls preload="metadata" src="recording.webm"></video>'
            '<p class="soft cantplay">This window cannot play the recording. Open <a href="recording.webm"><code>recording.webm</code></a>, '
            "which is beside this page, in Safari or Chrome.</p></div>" if megabytes is not None else "<p>It left no video file.</p>")
    count, passed, filmed = len(data["shots"]), recording.get("result") == "passed", megabytes is not None
    whole = "one whole journey through the app, from start to finish, by keyboard alone" if passed else "the app used up to where the run stopped"
    watch = f", or watch the recording{' of all of it' if passed else ''}" if filmed else ""
    about = (f"{count} moments from the walk-through: {whole}. Step through them{watch}." if count > 1
             else f"1 moment from the walk-through: {whole}.{' The recording shows the rest.' if filmed else ''}" if count
             else f"The walk-through: {whole}." if passed else "")
    if recording.get("shows") == "whole":
        said.append("This build added or changed no browser test of its own, so this is the standing walk through the whole app.")
    return (f'{head}<p>{pill(short, look)} {about}</p><div class="story" id="story" tabindex="-1">{stage}{film}</div>'
            f'<p class="soft">{" ".join(said)}</p><details class="record"><summary>The browser test behind it</summary>'
            f'<ul class="files"><li><code>{e(recording.get("walk", ""))}</code></li></ul></details></section>')


def render_summary(data: dict) -> str:
    summary = data["summary"]
    head = f'<section id="summary"><h2>{e(SUMMARY_TITLE)}</h2>'
    if summary is None:
        return head + f'<p>This build has no summary file: {unknown("hand-over.json is missing")}</p></section>'
    cards = []
    for key, kicker, title in (("so_what", "So what", "What it gives you"), ("now_what", "Now what", "What is left for you")):
        lines = summary.get(key) or []
        listed = lambda some: "".join(f"<li>{e(line)}</li>" for line in some)  # noqa: E731 (a one-line helper local to this function)
        first, rest = lines[:SUMMARY_LINES], lines[SUMMARY_LINES:]  # the agent writes the weightiest first; the tail is folded, and counted
        more = f"<details><summary>{len(rest)} more</summary><ul>{listed(rest)}</ul></details>" if rest else ""
        body = listed(first) if lines else f"<li>{unknown('nothing written')}</li>"
        cards.append(f'<div class="card{" next" if key == "now_what" else ""}"><p class="kicker">{kicker}</p><h3>{title}</h3><ul>{body}</ul>{more}</div>')
    return (head + '<p class="source agent">These two lists, and the list of what was built at the top of this page, come from '
            'the build\'s summary file (hand-over.json), which the agent that runs a build is meant to write. This page copies '
            'them as written and did not check them.</p>' + f'<div class="cards">{"".join(cards)}</div></section>')


def render_last_run(data: dict) -> str:
    """The last run of every check, with its checks; then, in words, any later run that ran only some."""
    runs, tip = data["runs"], (data["git"] or {}).get("tip")
    full, later, said = runs["full"], later_said(runs), []
    if full is None:
        said.append(unknown())
    else:
        off = stale(full.get("tip", "unknown"), full.get("dirty"), tip)
        looks = {"green": "amber" if off else "green", "red": "red"}  # green is drawn green only for the last commit as committed
        listed = "".join(
            f'<li>{e(chip(check.get("name", "?")))}: {pill(RUN_ENDS.get(str(check.get("result")), check.get("result", "unknown")), looks.get(str(check.get("result")), ""))}'
            f'{"" if check.get("result") == "not run" else " " + e(minutes(check.get("minutes"))) + ","} '
            f'output <code>{e(check.get("output", ""))}</code></li>' for check in full.get("checks") or [])
        look = looks.get(str(full.get("result")), "amber")
        said.append(f'{pill(RUN_ENDS.get(str(full.get("result")), full.get("result", "unknown")), look)} {e(when(full.get("at")))}, {e(minutes(full.get("minutes")))}, '
                    f'on commit <code>{e(full.get("tip", "unknown"))}</code>')
        if off:
            said.append(f'<p><span class="warned">This run was {e(off)}, {NOT_LAST}.</span></p>')
        said.append(f"<ul>{listed}</ul>")
    if later:
        said.append(f"<p>{e(later)}</p>")
    return "".join(said)


def stat(label: str, value_html: str, note_html: str = "", wide: bool = False) -> str:
    """One number of the build, drawn large, with one line under it."""
    return (f'<div class="stat{" span" if wide else ""}"><span class="kicker">{e(label)}</span>'
            f'<span class="value">{value_html}</span><span class="note">{note_html}</span></div>')


def render_stats(data: dict) -> str:
    """The build's numbers as tiles: time, commits, files, lines by kind, tests, and every checks run as a square."""
    facts, runs = data["git"] or {}, data["runs"]
    value = lambda key: e(number(facts.get(key))) if facts else unknown()  # noqa: E731 (a one-line helper local to this function)
    tiles = [stat("Build time", e(minutes(facts["minutes"])) if facts.get("minutes") is not None else unknown(), "first commit to last, on the clock"),
             stat("Commits", value("commits")), stat("Files changed", value("files"))]
    kinds = [(kind, count) for kind, count in (facts.get("added_by") or {}).items() if count]
    if kinds:
        names = {"product": "product", "tests and browser tests": "tests and browser tests"}
        bar = "".join(f'<span class="c{index}" style="flex-grow: {count}" title="{e(kind)}: {e(number(count))}"></span>'
                      for index, (kind, count) in enumerate(kinds, 1))
        legend = "".join(f'<span><i class="sw c{index}"></i>{e(names.get(kind, "records and agent instructions"))} {e(number(count))}</span>'
                         for index, (kind, count) in enumerate(kinds, 1))
        tiles.append(stat("Lines added", value("added"), f'<span class="bar">{bar}</span><span class="legend">{legend}</span>'
                          f' {e(number(facts.get("removed")))} removed', wide=True))
    else:
        tiles.append(stat("Lines added", value("added"), f'{value("removed")} removed' if facts else ""))
    tiles.append(stat("Tests added", value("tests_added"), f'{value("tests_removed")} removed' if facts else ""))
    if runs["runs"] is None:
        tiles.append(stat("Runs of the checks", unknown(), e(runs["why_unknown"]), wide=True))
    else:
        history, shown = runs.get("history") or [], (runs.get("history") or [])[-80:]
        squares = "".join(
            f'<span class="{"r-" + run["result"] if run["result"] in ("green", "red") else ""}{"" if run["full"] else " part"}" '
            f'title="{e(when(run["at"]))}: {e(ended(run["result"]))}{e(kind_of(run))}"></span>' for run in shown)
        picked = sum(1 for run in history if run.get("picked"))
        apart = (f'{e(number(picked))} of them ran only the tests the change could reach, so '
                 f'{"it is not" if picked == 1 else "none of those is"} a full run. ' if picked else "")
        more = f"The last {len(shown)} are drawn. " if len(history) > len(shown) else ""
        tiles.append(stat("Runs of the checks", f'{e(number(runs["runs"]))}', f'<span class="runs">{squares}</span>'
                          f'{e(number(runs["red"]))} failed. {apart}{more}Oldest first. A blue square is a run that passed, a red one a run that failed; '
                          f'a hollow square ran only some checks{QUICK_SQUARE if any(run.get("quick") for run in history) else ""}'
                          f'{" or ran only the tests the change could reach" if picked else ""}.', wide=True))
    return f'<div class="stats">{"".join(tiles)}</div>'


def kind_of(run: dict) -> str:
    """The words after a run's result in its square's title: a quick run, a picked run, both, or a run of some checks."""
    kinds = [QUICK_RUN.removeprefix(", ")] * bool(run.get("quick")) + [PICKED_RUN] * bool(run.get("picked"))
    return ", " + ", and ".join(kinds) if kinds else "" if run["full"] else ", some checks only"


def render_facts(data: dict) -> str:
    facts, runs, files = data["git"] or {}, data["runs"], data["files"]
    span = f"git, {data['git']['base']}..{data['git']['tip']}" if data["git"] else "git: no range was given"
    value = lambda key: e(number(facts.get(key))) if facts else unknown()  # noqa: E731 (a one-line helper local to this function)
    flagged = lambda count, look: f'<span class="{look}">{e(number(count))}</span>' if count else e(number(count))  # noqa: E731 (a one-line helper local to this function)
    every = ", ".join(runs["names"])
    log = runs["why_unknown"] or f".checks/runs.jsonl, the lines for branch {runs['branch']}"
    last = log if runs["full"] or runs["why_unknown"] else f"{log}: none of them is a full run, one of every check ({every})"
    red = unknown() if runs["red"] is None else f"{e(number(runs['red']))} of {e(number(runs['runs']))} runs"
    no_fate = sum(1 for f in data["findings"] if f["state"] == "no-fate")
    none_read = unknown("no review report was found")
    split = ("; of them " + ", ".join(f"{number(count)} {kind}" for kind, count in facts["added_by"].items())) if facts.get("added_by") else ""
    tests = f"{value('tests_added')} added, {value('tests_removed')} removed" if facts else unknown()
    rows = [
        fact("Last full run of the checks", render_last_run(data), last),
        fact("Failed runs of the checks", red, log if runs["why_unknown"] else f"{log}; every run is counted, a run of one named check too"),
        fact("Issues reported", e(number(len(data["findings"]))) if files else none_read,
             f"findings/*.jsonl: {number(len(files))} file{'' if len(files) == 1 else 's'} read"),
        fact("Issues with no outcome recorded", flagged(no_fate, "badly") if files else none_read, "issues with no outcome named in fates.jsonl"),
        fact("Outcomes matching no issue", flagged(len(data["orphans"]), "warned"), "lines of fates.jsonl whose id is no reported issue's"),
        fact(RUNNING, unknown() if running_said(data) is None else e(running_said(data)),
             "this computer's list of running programs (lsof and ps), read when this page was built: each program that is listening on a "
             "network port and was started with a file of this project; the app is one, a copy of it started by a test is another"),
        fact("Commits", value("commits"), span),
        fact("First commit", e(when(facts.get("first"))) if facts.get("first") else unknown(), span),
        fact("Last commit", e(when(facts.get("last"))) if facts.get("last") else unknown(), span),
        fact("Build time", e(minutes(facts["minutes"])) if facts.get("minutes") is not None else unknown(),
             "last commit minus first commit: clock time between them, not time worked"),
        fact("Files changed", value("files"), "git: the files the build changed, from where it branched off to its last commit"),
        fact("Lines added", value("added"), f"git: lines added in those files{split}"),
        fact("Lines removed", value("removed"), "git: lines removed from those files"),
        fact("Tests", tests, "lines starting def test_ that the build added and removed under tests/ and walks/; "
                             "a test that was moved or renamed counts as both"),
    ]
    return ('<section id="facts"><h2>The build in numbers</h2><p class="source script">This page computed or copied every number here '
            'from git and the build\'s record files.</p>' + render_stats(data) +
            '<details class="record"><summary>Every number, and where it came from</summary>'
            f'<dl class="facts">{"".join(rows)}</dl></details></section>')


def finder_said(finder: str) -> str:
    """A finder in the page's words; one the format does not name is shown as written and said to be unrecognised."""
    return FINDERS.get(finder) or (f'A review this page does not recognise: "{finder}"' if finder else "No review named")


NO_REPORT_CELL = '<td class="n soft">no report found<small>not made, or its report is elsewhere</small></td>'


def render_finders(data: dict) -> str:
    """Who reviewed the build and how much each reported: one row per kind of review, then every report read with its count."""
    counts, files = data["by_finder"], data["files"]
    other = any(row["other"] for row in counts.values())

    def cell(finder: str, which: str, n: int) -> str:
        """A count; "none found" where a report for this round was read and lists nothing; otherwise that none was found."""
        if n:
            return f'<td class="n">{e(n)}</td>'
        if report_read(files, finder, which):
            return '<td class="n">none found</td>'
        if (finder, which) == ("early-read", "recheck"):
            return '<td class="n soft">none is made</td>'
        return NO_REPORT_CELL

    rows = []
    for finder, row in counts.items():
        cells = cell(finder, "first", row["first"]) + cell(finder, "recheck", row["recheck"])
        if other:
            cells += f'<td class="n">{unknown(row["other"])}</td>' if row["other"] else '<td class="n soft">none</td>'
        if finder in data["absent"]:
            cells = f'<td colspan="{2 + other}">{unknown("no report found")}</td>'
        does = f'<small>{e(FINDER_NOTES[finder])}</small>' if finder in FINDER_NOTES else ""
        rows.append(f"<tr><th>{e(finder_said(finder))}{does}</th>{cells}</tr>")
    extra = '<th class="n">Round not recognised</th>' if other else ""
    empty = lambda name: ("reviewed, found nothing" if any(wrote(name, finder) for finder in FINDERS)  # noqa: E731 (a one-line helper local to this function)
                          else "empty report: its name does not say which review wrote it")
    read = "".join(f"<li><code>{e(name)}</code>: {e(issues(len(found))) if found else empty(name)}</li>"
                   for name, found in files.items())
    read = (f'<details class="record"><summary>The {number(len(files))} report{"" if len(files) == 1 else "s"} read</summary>'
            f'<ul class="files">{read}</ul></details>' if files
            else f"<p>{unknown('This page found no review report, so nothing on this page shows that anyone tested or read the build.')}</p>")
    intro = ("The numbers are issues reported. A re-check is a second review, made after the fixes, of what the fixes touched."
             + (" This page read no re-check report, so nothing on record shows that one was made." if files and not rechecked(data) else "")
             + (f" {late_said(data, after_intro=True)}" if late_said(data) else ""))
    return ('<section id="finders"><h2>Who reviewed the build</h2>'
            f'<p>{intro}</p>'
            f'<div class="scroll"><table><thead><tr><th>Review</th><th class="n">{PASSES["first"]}</th><th class="n">{PASSES["recheck"]}</th>{extra}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="source script">This page counted these from the reviewers\' report files. {NO_REPORT}</p>{read}</section>')


def trace(label: str, value_html: str) -> str:
    return f"<div><dt>{e(label)}</dt><dd>{value_html}</dd></div>"


def render_finding(finding: dict, shared: str = "", same_as: str = "") -> str:
    """One issue. In view: what the reviewer reported, how serious they recorded it to be, the reason the record gives
    where the issue is not recorded as fixed, and anything of its proof that was not found. Folded under it: its whole
    record, so every id, commit and test stays on the page. `shared` is a reason its whole group gives, already printed
    once above the list; `same_as` is the id of an earlier issue in the list that gives this issue's reason word for
    word. Nothing is said twice."""
    fate, state = finding["fate"] or {}, finding["state"]
    severity, why = str(finding.get("severity") or "").strip(), reason(fate)
    finder, which = str(finding.get("finder", "")), str(finding.get("pass", ""))
    fixed = state in ("fixed", "fixed-no-check", "fixed-not-found")
    tag = f'<span class="sev{" blocks" if severity == "blocks" else ""}">{e(SEVERITIES[severity])}</span> ' if severity in SEVERITIES else ""
    lines = [f'<p class="what">{tag}{e(finding.get("what", ""))}</p>']
    if why and why != shared and not fixed:
        lines.append(f'<p class="why"><b>Reason recorded:</b> the same as for <code>{e(same_as)}</code>, above.</p>' if same_as
                     else f'<p class="why"><b>Reason recorded:</b> {e(why)}</p>')
    if finding["lacks"]:
        lines.append(f'<p><span class="warned">Missing: {e(finding["lacks"])}.</span></p>')
    code = lambda text: f"<code>{e(text)}</code>"  # noqa: E731 (a one-line helper local to this function)
    by = ", ".join(part for part in (finder_said(finder) if finder else "", PASSES.get(which, which).lower()) if part)
    rows = [trace("Reported by", e(by or "not recorded")), trace("Area", e(finding.get("area") or "not recorded")),
            trace("Severity", e(SEVERITIES.get(severity, severity or "not recorded in the review report")))]
    if finding.get("where"):
        rows.append(trace("Where", e(finding["where"])))
    if finding.get("check") and finding["check"] != fate.get("check"):  # said once when the outcome names the same test
        rows.append(trace("Reviewer's test", code(finding["check"])))
    rows.append(trace("Outcome recorded", e(fate.get("fate") or "none")))
    if fate.get("commit"):
        rows.append(trace("Commit", code(fate["commit"])))
    named = str(fate.get("check") or "").strip()
    if fixed or named:  # a name with no :: is a whole file of tests, and the record does not say which test shows the fix
        whole = " (a whole test file: the record does not say which test in it)" if named and "::" not in named else ""
        rows.append(trace("Test named", code(named) + whole if named else "none"))
    if why and why != shared and fixed:
        rows.append(trace("Note recorded", e(why)))
    lines.append(f'<details class="trace"><summary>Record {code(finding.get("id", ""))}</summary><dl>{"".join(rows)}</dl></details>')
    return f'<li class="finding">{"".join(lines)}</li>'


def render_findings(data: dict) -> str:
    """Every issue, in two layers. First what happened, in sentences: how many were reported and what the record says
    became of them, one heading per outcome with what it means for the owner, and a reason a whole group shares said
    once. Under that the evidence: each issue in its reviewer's words with its record folded beneath it."""
    found = data["findings"]
    head = f'<section id="findings"><h2>The issues found, and what happened to each</h2><p class="lead">{e(issues_said(data))}</p>'
    orphans = ""
    if data["orphans"]:
        count = len(data["orphans"])
        def orphan(fate: dict) -> str:  # the outcome in the page's words; a reason only when the record gives one
            kind, why = str(fate.get("fate") or ""), reason(fate)
            outcome = OUTCOMES.get(kind) or (f'"{kind}", as written' if kind else "no outcome named")
            return f'<li><code>{e(fate.get("id", ""))}</code>: {e(outcome)}.{" Reason recorded: " + e(why) if why else ""}</li>'
        rows = "".join(orphan(fate) for fate in data["orphans"])
        one = count == 1
        orphans = (f'<div class="orphans"><p><strong>The record gives {"an outcome" if one else "outcomes"} for {issues(count)} that '
                   f'{"is" if one else "are"} in no review report this page read.</strong> '
                   f'{"The outcome" if one else "Each outcome"} below names an issue this page did not read. An issue may have been '
                   f'reported somewhere it does not look: it reads findings/*.jsonl only.</p><ul>{rows}</ul></div>')
    if not found:
        return head + orphans + ("" if data["files"] or orphans else "<p>So there is nothing to list.</p>") + "</section>"
    odd = sum(1 for row in found if str(row.get("severity") or "").strip() not in ("", *SEVERITIES))
    ranked = (f" {issues(odd).capitalize()} record{'s' if odd == 1 else ''} a severity this page does not recognise; it is shown "
              f"as written in {'that issue' if odd == 1 else 'each issue'}'s record." if odd else "")
    source = ('<p class="source agent">Each description is copied from the review report files as written, and each outcome and reason is '
              f'what the build\'s record says. This page reproduces them and did not check them.{ranked} A group is shown open when its '
              'issues were left unfixed, have no usable outcome recorded, are marked fixed with a test file or commit this page '
              'could not find, or are judged not a defect with no reason given or against a reviewer\'s rating of "blocks use". '
              'Every other group is folded: select its heading to open it. '
              'Each issue\'s full record is folded under it. Sources: findings/*.jsonl and fates.jsonl.</p>')
    groups = []
    for index, (state, rows) in enumerate(data["groups"]):
        look, opened = state_look(state, rows)[1:]
        what, so_what = state_said(state, rows, data["verified"])
        so_what = undecided(so_what, data)
        shared = shared_reason(rows)  # one reason for all: said once, not on every issue
        same = (f'<p class="why"><b>The reason recorded, the same for all {len(rows)}:</b> {e(shared)}</p>' if shared else "")
        first, cards = {}, []  # the first issue in the list to give each reason
        for row in rows:
            why = reason(row["fate"])
            cards.append(render_finding(row, shared, first.get(why, "") if why else ""))
            first.setdefault(why, str(row.get("id", "")))
        groups.append(
            f'<details id="group-{index}" class="group {look}"{" open" if opened else ""}>'
            f'<summary><i class="sw {SEGMENTS.get(state, "s-bad")}"></i><h3>{e(what)}</h3></summary>'
            f'<p>{e(so_what)}</p>{same}'
            f'<ol class="findings">{"".join(cards)}</ol></details>')
    return head + source + orphans + "".join(groups) + "</section>"


def render(data: dict) -> str:
    """The whole page, as one HTML document with its CSS and its one small script inside."""
    built = data["built"]
    footer = (f'Built by handover.py {e(when(built.get("at")))} from the folder at commit <code>{e(built.get("commit", "unknown"))}</code>'
              f'{", with uncommitted changes in the folder" if built.get("dirty") else ""}.'
              if built else "Built by handover.py.")
    body = "".join([
        render_header(data), render_recording(data), render_summary(data), render_findings(data),
        render_finders(data), render_facts(data),
    ])
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Hand-over: {e(data["feature"])}</title><style>{CSS}</style></head>\n'
            f'<body><main>{body}<footer>{footer}</footer></main><script>{SCRIPT}</script></body></html>\n')


# Recording the walk.

def tree_state(root: pathlib.Path) -> dict:
    """The commit the folder is at now, and whether anything in it is uncommitted."""
    return {"commit": git(root, "rev-parse", "--short", "HEAD"), "dirty": bool(git(root, "status", "--porcelain")),
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}


def changed_walks(root: pathlib.Path, base: str, tip: str) -> list[tuple[str, str]]:
    """(file, test name) of every walk the build added or changed, in file order: a test function in walks/test_*.py
    with an added or changed line of its own between <base> and <tip>. A walk that changed only through a helper it
    calls is not counted. [] when git cannot say."""
    done = subprocess.run(["git", "diff", "--unified=0", "--no-color", f"{base}...{tip}", "--", "walks"],
                          cwd=root, capture_output=True, text=True)
    if done.returncode != 0:
        return []
    touched: dict[str, list[tuple[int, int]]] = {}
    path = None
    for line in done.stdout.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        hunk = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", line) if path else None
        if hunk:
            start, count = int(hunk.group(1)), int(hunk.group(2) or 1)
            # Lines only removed leave no line of their own: they count for the function they were removed from inside.
            touched.setdefault(path, []).append((start, start + count - 1) if count else (start + 1, start))
    found = []
    for path in sorted(touched):
        shown = subprocess.run(["git", "show", f"{tip}:{path}"], cwd=root, capture_output=True, text=True)
        if not re.fullmatch(r"walks/test_\w+\.py", path) or shown.returncode != 0:
            continue
        try:
            tree = ast.parse(shown.stdout)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                first = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list])
                if any(start <= node.end_lineno and end >= first for start, end in touched[path]):
                    found.append((path, node.name))
    return found


def walk_ids(root: pathlib.Path, tests: list[tuple[str, str]]) -> list[str]:
    """The pytest ids to record: each changed walk once, at VIEW (in Chromium) where it runs at several window sizes."""
    bare = [f"{path}::{name}" for path, name in tests]
    if not bare:
        return []
    try:
        asked = subprocess.run([str(root / ".venv" / "bin" / "python"), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *bare],
                               cwd=root, capture_output=True, text=True, timeout=120)
        collected = [line.strip() for line in asked.stdout.splitlines() if "::" in line]
    except (subprocess.TimeoutExpired, OSError):
        collected = []
    ids = []
    for one in bare:
        mine = [nodeid for nodeid in collected if nodeid.split("[", 1)[0] == one]
        sized = sorted((nodeid for nodeid in mine if VIEW in nodeid), key=lambda nodeid: "chromium" not in nodeid and "-" in nodeid.split("[", 1)[-1])
        ids.append((sized or mine or [one])[0])
    return ids


def walk_parts(summary: dict | None, changed: list[tuple[str, str]], path: pathlib.Path) -> tuple[list[dict], list[str]]:
    """(the parts of the walk-through, the changed walks left out of it). A part is an entry of hand-over.json's
    walk_through, in the builder's order: {"test": (file, name), "title", "legend"}. A build that changed walks and
    lists none stops the run, and so does an entry that names no walk the build added or changed, or one named twice."""
    entries = (summary or {}).get("walk_through") or []
    names = {f"{file}::{name}": (file, name) for file, name in changed}
    listed_tests = "".join(f"\n  {key}" for key in names) or "\n  (none)"
    if changed and not entries:
        raise SystemExit(
            f"handover: this build added or changed {tests_said(len(changed))} and {path} has no walk_through, so the owner's "
            'recording would have no words. Add "walk_through": one {"test", "title", "legend"} for each of these the owner '
            f"should see, in the order to show them (`.claude/skills/implement-spec/SKILL.md` has the format):{listed_tests}")
    parts, used = [], []
    for index, entry in enumerate(entries, 1):
        mine = [key for key, (_, name) in names.items() if entry["test"] in (name, key)]
        if len(mine) != 1 or mine[0] in used:
            why = ("is listed twice" if mine and mine[0] in used else "is the name of more than one of them: write it as file::name" if mine
                   else "is not a browser test this build added or changed")
            raise SystemExit(f"handover: {path}: walk_through entry {index}: {entry['test']} {why}. "
                             f"The browser tests this build added or changed:{listed_tests}")
        used.append(mine[0])
        parts.append({"test": names[mine[0]], "title": entry["title"].strip(), "legend": entry["legend"].strip()})
    return parts, [key for key in names if key not in used]


def junit_results(path: pathlib.Path) -> dict[str, str]:
    """{pytest id: passed, failed or did not run} from a run's JUnit file; {} when the run left none that can be read."""
    try:
        cases = list(xml.etree.ElementTree.parse(path).iter("testcase"))
    except (OSError, xml.etree.ElementTree.ParseError):
        return {}
    results = {}
    for case in cases:
        kinds = {child.tag for child in case}
        results[f"{case.get('classname', '').replace('.', '/')}.py::{case.get('name')}"] = (
            "failed" if kinds & {"failure", "error"} else "did not run" if "skipped" in kinds else "passed")
    return results


def record_walk(root: pathlib.Path, feature: str, out: pathlib.Path, picked=(), left_out=()) -> dict:
    """Run the walk-through with recording on; leave the videos, shots/, recording.json and walk-output.txt in `out`.
    `picked` is the parts of the walk-through, each {"walk": its pytest id, "title", "legend"}: each is recorded as
    clips/<walk>.webm. With none, the standing walk through the whole app is recorded, as recording.webm.
    The result is passed, failed (pytest ran it and it failed), did not run (pytest ended any other way) or did not finish."""
    scratch, shots, clips = out / "recording-tmp", out / "shots", out / "clips"
    shutil.rmtree(clips, ignore_errors=True)
    for folder in (scratch, shots):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
    for old in ("recording.webm", "recording.json"):  # an earlier run's pass must not outlive this run
        (out / old).unlink(missing_ok=True)
    words = {part["walk"]: part for part in picked}
    ids = list(words) or [WALK]
    record = {**({} if picked else {"walk": WALK}), "shows": "build" if picked else "whole", **tree_state(root)}
    limit = max(900, 180 * len(ids))
    started = time.time()
    try:
        run = subprocess.run(
            [str(root / ".venv" / "bin" / "python"), "-m", "pytest", *ids, "-q", "-p", "no:cacheprovider",
             *([f"--junitxml={scratch / 'junit.xml'}"] if picked else [])],
            cwd=root, capture_output=True, text=True, timeout=limit,
            env={**os.environ, "WALK_RECORD": str(scratch), "WALK_FEATURE": feature,
                 **({"WALK_SLOW_MO": os.environ.get("WALK_SLOW_MO", OWN_SLOW_MO)} if picked else {})})
        printed = run.stdout + run.stderr
        record.update(result={0: "passed", 1: "failed"}.get(run.returncode, "did not run"), returncode=run.returncode)
        if record["result"] == "did not run":
            record["reason"] = (f"The test runner (pytest) ended with exit code {run.returncode}, which is neither a pass nor a "
                                "failure of the walk-through")
    except (subprocess.TimeoutExpired, OSError) as error:
        timed_out = isinstance(error, subprocess.TimeoutExpired)
        parts = [error.stdout, error.stderr] if timed_out else [str(error)]
        printed = "".join(part.decode(errors="replace") if isinstance(part, bytes) else part or "" for part in parts)
        record.update(result="did not finish" if timed_out else "did not run",
                      reason=f"It was stopped after {limit // 60} minutes" if timed_out else f"The command that runs it could not start: {error}")
    record["minutes"] = round((time.time() - started) / 60, 1)
    (out / "walk-output.txt").write_text(printed, encoding="utf-8")
    # A walk's videos and screenshots are named after it (walks/helper.py keep_video, shot_name); take this run's only.
    if picked:
        results = junit_results(scratch / "junit.xml")
        clips.mkdir()
        record["walks"] = []
        for one in ids:
            kept = []
            for video in sorted(scratch.glob(f"{walk_prefix(one)}*.webm")):  # a walk that opened a second page left a second video
                video.replace(clips / video.name)
                kept.append(video.name)
            record["walks"].append({"walk": one, "title": words[one]["title"], "legend": words[one]["legend"],
                                    "result": results.get(one), "clips": kept})
        record["left_out"] = list(left_out)
    elif (scratch / f"{walk_prefix(WALK)}.webm").exists():
        (scratch / f"{walk_prefix(WALK)}.webm").replace(out / "recording.webm")
    shutil.rmtree(scratch, ignore_errors=True)
    for one in ids:
        for shot in sorted((root / ".scratch" / feature / "walks").glob(f"{walk_prefix(one)}-*.png")):
            if shot.stat().st_mtime >= started - 1:
                shutil.copy2(shot, shots / shot.name)
    (out / "recording.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def read_recording(out: pathlib.Path) -> dict | None:
    """recording.json, with the size of its video or videos in megabytes (None when there is no video file)."""
    record = read_json(out / "recording.json")
    if record is None:
        return None
    videos = ([out / "clips" / str(clip) for walk in own_walks(record) for clip in walk.get("clips") or []]
              if own_walks(record) else [out / "recording.webm"])
    sizes = [video.stat().st_size for video in videos if video.is_file()]
    return {**record, "megabytes": round(sum(sizes) / 1e6, 1) if sizes else None}


def shots_of(out: pathlib.Path) -> list[dict]:
    """The walk's screenshots, each with the address the page shows it from: the picture itself, written into the
    page, so the page is one file that shows its pictures wherever it is opened; a very large one stays a file."""
    shots = []
    for path in sorted((out / "shots").glob("*.png")):
        inside = path.stat().st_size <= PICTURE_BYTES
        src = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii") if inside else "shots/" + urllib.parse.quote(path.name)
        shots.append({"name": path.name, "src": src})
    return shots


def main(argv=None, root: pathlib.Path = ROOT, show=None) -> int:
    """Build the page. `show`, when given, is called with the page's file: address once it is written (run as a
    script, that opens it in the browser)."""
    parser = argparse.ArgumentParser(description="Build the hand-over page of one feature.")
    parser.add_argument("feature", help="the folder name under .scratch/")
    parser.add_argument("--base", default="main", help="the commit the build started from (default main)")
    parser.add_argument("--tip", default="HEAD", help="the build's last commit (default HEAD); give --branch with it")
    parser.add_argument("--branch", default=None, help="the branch whose checks runs are counted (default the current branch)")
    parser.add_argument("--no-walk", action="store_true", help="do not run and record the walk; keep any earlier recording")
    parser.add_argument("--no-open", action="store_true", help="do not open the page in the browser when it is built")
    args = parser.parse_args(argv)
    if args.tip != "HEAD" and not args.branch:
        raise SystemExit("handover: --tip needs --branch: checks runs are logged by branch name, and the checked-out branch may not be the tip's")
    feature_dir = root / ".scratch" / args.feature
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.feature) or not feature_dir.is_dir():
        raise SystemExit(f"handover: no feature folder {feature_dir}")
    out = feature_dir / "hand-over"
    out.mkdir(exist_ok=True)
    # Everything that can refuse is read before the walk, so a refusal does not cost a recording.
    facts = git_facts(root, args.base, args.tip)
    files, fates, summary = read_findings(feature_dir), read_fates(feature_dir), read_summary(feature_dir)
    runs = run_facts(read_runs(root / ".checks" / "runs.jsonl"), args.branch or git(root, "rev-parse", "--abbrev-ref", "HEAD"))
    record, picked, left_out = None, [], []
    if not args.no_walk:  # which walks, and the words for each: a refusal here costs no recording
        parts, left_out = walk_parts(summary, changed_walks(root, args.base, args.tip), feature_dir / "hand-over.json")
        picked = [{"walk": nodeid, "title": part["title"], "legend": part["legend"]}
                  for part, nodeid in zip(parts, walk_ids(root, [part["test"] for part in parts]))]
    if not args.no_walk:
        if picked:
            print(f"Recording the walk-through, {parts_said(len(picked))}:", *(part["walk"] for part in picked), sep="\n  ", flush=True)
        else:
            print(f"This build added or changed no walk, so recording the acceptance walk (about two minutes): {WALK}", flush=True)
        record = record_walk(root, args.feature, out, picked, left_out)
    recording = read_recording(out)
    data = page_data(
        args.feature, base_ref=args.base, tip_ref=args.tip, git=facts, runs=runs, files=files, fates=fates,
        missing=missing_proof(root, facts["tip"], fates), summary=summary, recording=recording,
        shots=shots_of(out), built=tree_state(root), walk_gap=commit_gap(root, (recording or {}).get("commit"), args.tip),
        copies=listeners(root), flaky=read_flaky(feature_dir),
    )
    page = out / "index.html"
    page.write_text(render(data), encoding="utf-8")
    print(page)
    print(f"The page's headline: {headline_said(len(to_look_at(data)), merged(data))}")
    if record and record["result"] != "passed":
        print(f"handover: the {'walk-through' if record.get('walks') is not None else 'acceptance walk'} "
              f"{WALK_ENDS[record['result']]}; what it printed is in {out / 'walk-output.txt'}")
    print(f"open {shlex.quote(str(page))}", flush=True)
    if show and not args.no_open:
        show(page.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main(show=webbrowser.open))
