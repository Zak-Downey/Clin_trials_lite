"""Build the one page a build ends with: .scratch/<feature>/hand-over/index.html.

    python3 handover.py <feature> [--base <ref>] [--tip <ref> --branch <name>] [--no-walk] [--no-open]

Run from the repo root. The page is one file: its pictures, its styles and its one small script are inside it (a
screenshot over 1.5 MB stays a file beside it), and it loads nothing from outside its own folder. When it is built
it opens in the browser. The facts on the page are computed here, from git and from
machine-readable files; the only words an agent writes are the what / so what / now
what of hand-over.json and the words inside findings and fates, and the page says so.
Nothing here reads Markdown.

Reads (all optional; what is missing is shown as missing, never as zero):
  git                                   the commits of <base>..<tip>
  .checks/runs.jsonl                    one line per checks run
  .scratch/<feature>/findings/*.jsonl   one line per finding; an empty file is a look that found nothing
  .scratch/<feature>/fates.jsonl        one line per finding id: what became of it
  .scratch/<feature>/hand-over.json     {"what": [...], "so_what": [...], "now_what": [...]}

Writes, beside index.html: recording.webm (the acceptance walk, recorded; the page plays it from
beside itself), recording.json (when, on which commit and how it ended), shots/*.png and walk-output.txt. A walk that
fails is said on the page and in one printed line; the exit code is still 0.
"""

from __future__ import annotations

import argparse
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

import checks

ROOT = pathlib.Path(__file__).resolve().parent

# The walk that is recorded: the whole journey, keyboard only, Chromium at 1440 x 900.
WALK = "walks/test_acceptance_walk.py::test_walk_the_whole_journey_by_keyboard_alone[chromium-1440x900]"
CHECK_NAMES = [name for name, _, _ in checks.CHECKS]  # a checks run is "full" when it lists every one of these

FINDERS = {"walker": "Walker", "review": "Review", "early-read": "Early read"}
PASSES = {"first": "First pass", "recheck": "Re-check"}
SEVERITIES = {"blocks": "blocks use", "wrong": "wrong", "cosmetic": "cosmetic", "not recorded": "severity not recorded"}
# What became of a finding, in the order the page shows the groups: heading, look, drawn open, what it means.
STATES = {
    "no-fate": ("No fate recorded", "bad", True,
                "fates.jsonl names no fate for these findings, so the record does not say what became of them."),
    "left": ("Left as it is", "warn", True, "Recorded as known and left."),
    "fixed-not-found": ("Fixed, but what the record names was not found", "warn", True,
                        "Recorded as fixed, but handover.py could not find the check's file or the commit. Each says which."),
    "fixed-no-check": ("Fixed, no check named", "note", False,
                       "Recorded as fixed, but the record names no test or walk that shows the fix holds."),
    "fixed": ("Fixed", "", False, "Recorded as fixed, each naming the test or walk that shows it."),
    "not-a-defect": ("Not a defect", "", False, "Recorded as not a defect."),
}
FOUND = (" handover.py found each check's file in the build's last commit and each commit in the repository; "
         "it did not run the checks.")
WALK_ENDS = {"failed": "FAILED", "did not run": "did not run", "did not finish": "did not finish"}
SUMMARY_LINES, LINE_LENGTH = 5, 200  # what and so_what: at most this many lines; any line of hand-over.json: at most this long
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
    return summary


def read_runs(path: pathlib.Path) -> list[dict] | None:
    """The checks run log, oldest first. None when the file does not exist."""
    return read_jsonl(path) if path.exists() else None


def git(repo: pathlib.Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"handover: git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


# Computing.

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
    added = {"product": 0, "tests and walks": 0, "build records and kit (.scratch/, .claude/)": 0}
    for line in git(repo, "diff", "--numstat", f"{base}...{tip}").splitlines():
        plus, minus, path = line.split("\t", 2)
        path = re.sub(r"\{[^{}]* => ([^{}]*)\}", r"\1", path).split(" => ")[-1].replace("//", "/")  # a renamed file: its new path
        kind = list(added)[2 if path.startswith((".scratch/", ".claude/")) else 1 if path.startswith(("tests/", "walks/")) else 0]
        files += 1
        added[kind] += int(plus) if plus.isdigit() else 0  # a binary file has "-" for both
        removed += int(minus) if minus.isdigit() else 0
    tests = git(repo, "diff", f"{base}...{tip}", "--", "tests", "walks")
    return {
        "base": git(repo, "rev-parse", "--short", base), "tip": git(repo, "rev-parse", "--short", tip),
        "commits": len(times), "first": first, "last": last,
        "minutes": round(span.total_seconds() / 60) if span is not None else None,
        "files": files, "added": sum(added.values()), "added_by": added, "removed": removed,
        "tests_added": tests_changed(tests, "+"), "tests_removed": tests_changed(tests, "-"),
    }


def run_facts(runs: list[dict] | None, branch: str, names=None) -> dict:
    """The checks runs of one branch: how many, how many red, each run's result in order (`history`), the last
    run of every check (`full`) and, when the branch's last run is not that one, the last run (`later`). None,
    with why, where the log does not say."""
    facts = {"runs": None, "red": None, "full": None, "later": None, "history": [], "branch": branch,
             "names": list(CHECK_NAMES if names is None else names), "why_unknown": ""}
    if runs is None:
        return {**facts, "why_unknown": "No checks run was logged: .checks/runs.jsonl does not exist."}
    own = [run for run in runs if run.get("branch") == branch]
    if not own:
        return {**facts, "why_unknown": f"The checks run log (.checks/runs.jsonl) has no line for branch {branch}."}
    full = [run for run in own if not missed(run, facts["names"])]
    history = [{"at": run.get("at"), "result": str(run.get("result")), "full": not missed(run, facts["names"])} for run in own]
    return {**facts, "runs": len(own), "red": sum(run.get("result") == "red" for run in own), "history": history,
            "full": full[-1] if full else None, "later": None if full and full[-1] is own[-1] else own[-1]}


def missed(run: dict, names: list[str]) -> list[str]:
    """The configured checks a run's line does not list."""
    ran = {str(check.get("name")) for check in run.get("checks") or []}
    return [name for name in names if name not in ran]


def missing_proof(repo: pathlib.Path, tip: str, fates: dict[str, dict]) -> dict[str, str]:
    """{finding id: what could not be found} for each fate recorded as fixed with a check: the check's file
    (the part before ::) must be in the tip commit and the fate's commit must be in the repository."""
    found = lambda name: subprocess.run(["git", "cat-file", "-e", name], cwd=repo, capture_output=True).returncode == 0  # noqa: E731
    missing = {}
    for ident, fate in fates.items():
        check, commit = str(fate.get("check") or "").strip(), str(fate.get("commit") or "").strip()
        if fate.get("fate") != "fixed" or not check:
            continue
        path = check.split("::")[0]
        lacks = [] if found(f"{tip}:{path}") else [f"the check's file {path} is not in the build's last commit ({tip})"]
        if not commit:
            lacks.append("no commit is named")
        elif not found(f"{commit}^{{commit}}"):
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
    """The joined findings in groups: no fate first, then any fate the format does not name, then STATES' order."""
    named = list(STATES)
    order = named[:1] + sorted({f["state"] for f in joined} - set(STATES)) + named[1:]
    groups = [(state, [f for f in joined if f["state"] == state]) for state in order]
    return [(state, rows) for state, rows in groups if rows]


def state_look(state: str, verified: bool = False) -> tuple[str, str, bool, str]:
    """(heading, look, drawn open, what it means) of a group."""
    if state not in STATES:
        return state.capitalize(), "bad", True, "A fate the record format does not name."
    title, look, opened, note = STATES[state]
    return title, look, opened, note + (FOUND if state == "fixed" and verified else "")


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


def absent_finders(files: dict[str, list[dict]]) -> list[str]:
    """The format's finders with no findings file at all: none whose rows name it, none named <finder>-..."""
    named = {str(row.get("finder", "")) for rows in files.values() for row in rows}
    return [finder for finder in FINDERS if finder not in named and not any(name.startswith(finder + "-") for name in files)]


def page_data(feature: str, *, base_ref: str = "", tip_ref: str = "", git: dict | None = None, runs: dict | None = None,
              files: dict[str, list[dict]] | None = None, fates: dict | None = None, missing: dict[str, str] | None = None,
              summary: dict | None = None, recording: dict | None = None, shots=(), built: dict | None = None) -> dict:
    """Everything the page shows, in one dictionary. `files` is read_findings' answer; `missing` is
    missing_proof's, or None when nobody looked for the checks and commits the fates name."""
    files, fates = files or {}, fates or {}
    findings = [row for rows in files.values() for row in rows]
    joined = join(findings, fates, missing)
    return {
        "feature": feature, "base_ref": base_ref, "tip_ref": tip_ref, "git": git,
        "runs": runs or run_facts(None, ""), "summary": summary, "recording": recording, "shots": list(shots),
        "files": files, "findings": joined, "groups": group_by_state(joined), "verified": missing is not None,
        "by_finder": count_by_finder(findings), "absent": absent_finders(files),
        "orphans": orphan_fates(findings, fates), "built": built or {},
    }


def stale(commit, dirty, tip) -> str:
    """Why a walk or a checks run does not speak for the build's last commit; "" when it does."""
    why = [f"on commit {commit}, not the build's last commit ({tip})"] if tip and commit != tip else []
    return " and ".join(why + (["with uncommitted changes in the folder"] if dirty else []))


def walk_verdict(data: dict) -> tuple[str, str]:
    """(look, words) for the recorded walk. Green only for a pass on the build's last commit, as committed."""
    recording = data["recording"]
    if not recording:
        return "amber", "The walk was not run for this page"
    result = recording.get("result")
    if result in WALK_ENDS:
        return "red", f"The walk {WALK_ENDS[result]}"
    if result != "passed":
        return "amber", "The walk's result is unknown"
    if stale(recording.get("commit"), recording.get("dirty"), (data["git"] or {}).get("tip")):
        return "amber", "The walk passed, on code that is not the build's last commit"
    return "green", "The walk passed"


def checks_verdict(data: dict) -> tuple[str, str]:
    """(look, words) for the last run of every check. Green only for a green run on the build's last commit, as committed."""
    full, later = data["runs"]["full"], data["runs"]["later"]
    after = str(later.get("result")) if later else "green"  # the branch's last run, when it ran only some checks
    if full is None or full.get("result") not in ("green", "red"):
        return ("red", "Checks: the last run was RED") if after == "red" else ("amber", "Checks: unknown")
    if full["result"] == "red":
        return "red", "Checks RED"
    if after != "green":
        return ("red" if after == "red" else "amber"), f"Checks green, then a later run of some was {'RED' if after == 'red' else 'not green'}"
    if stale(full.get("tip"), full.get("dirty"), (data["git"] or {}).get("tip")):
        return "amber", "Checks green, on code that is not the build's last commit"
    return "green", "Checks green"


def later_said(runs: dict) -> str:
    """In words, the branch's last run when it ran only some checks; "" when its last run ran every check."""
    later = runs["later"]
    if not later:
        return ""
    ran = ", ".join(str(check.get("name", "?")) for check in later.get("checks") or [])
    return (f'{"A later run" if runs["full"] else "The last run"} of {ran or "no check"} only was {later.get("result", "unknown")} at '
            f'{when(later.get("at"))}; it did not run {", ".join(missed(later, runs["names"]))}.')


def left_said(data: dict) -> str:
    """How many things the builder lists as left for the owner: a count of lines, which the script can make without judging them."""
    if data["summary"] is None:
        return "There is no builder's summary: hand-over.json is missing."
    count = len(data["summary"].get("now_what") or [])
    return (f"The builder lists {count} thing{'' if count == 1 else 's'} as left for you, further down." if count
            else "The builder wrote nothing as left for you.")


# Rendering.

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
.soft, .source, figcaption, .meta, .fate, dd small { color: var(--soft); font-size: .9rem; }
.source { margin: 0 0 .8rem; }
.source.agent::before { content: "Agent's words"; }
.source.script::before { content: "Counted by the script"; }
.source::before { display: inline-block; margin-right: .5rem; padding: 0 .5rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
  border: 1px solid var(--line); color: var(--ink); }
.source.agent::before { border-color: var(--warn-line); background: var(--warn-bg); color: var(--warn); }
.mark { display: inline-grid; place-items: center; width: 1.7rem; height: 1.7rem; border-radius: 50%; font-weight: 700; line-height: 1;
  background: var(--quiet); color: var(--card); flex: none; }
.green > .mark { background: var(--ok); } .amber > .mark { background: var(--warn-fill); color: #1b1300; } .red > .mark { background: var(--bad-fill); color: #fff; }
.headline { display: flex; align-items: center; gap: .6rem; font-size: 1.35rem; font-weight: 650; margin: 1rem 0 .2rem; }
.headline.green { color: var(--ok); } .headline.amber { color: var(--warn); } .headline.red { color: var(--bad); }
.board { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; margin-top: .9rem; }
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
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
details.group, .orphans { border: 1px solid var(--line); border-radius: 10px; margin-top: .8rem; padding: .6rem .9rem; }
details.group.bad { border: 2px solid var(--bad); background: var(--bad-bg); }
details.group.bad > summary { color: var(--bad); }
details.group.warn, .orphans { border-color: var(--warn-line); background: var(--warn-bg); }
details.group.warn > summary, .orphans > p:first-child { color: var(--warn); }
details.group.note { border: 1px dashed var(--warn); }
details.group.note > summary { color: var(--warn); }
summary { cursor: pointer; font-weight: 600; }
summary h3 { display: inline; }
.count { font-weight: 600; margin-left: .4rem; }
ol.findings { list-style: none; margin: .6rem 0 0; padding: 0; }
ol.findings > li { background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 8px; padding: .6rem .8rem; margin-top: .5rem; overflow-wrap: anywhere; }
ol.findings p { margin: .15rem 0; }
footer { color: var(--soft); font-size: .85rem; margin-top: 1.5rem; }
@media (max-width: 600px) {
  body { font-size: 16px; }
  section { padding: .9rem .8rem; }
  dl.facts > div { grid-template-columns: 1fr; }
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
  var video = story.querySelector("video");
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) { n.className = cls; } if (text) { n.textContent = text; } if (tag === "button") { n.type = "button"; } return n; }
  if (video) {
    video.addEventListener("error", function () { story.classList.add("nofilm"); });
    if (video.error) { story.classList.add("nofilm"); }
    var still = frames.length > 1 ? frames[1].querySelector("img") : null;
    if (still) { video.poster = still.src; }
  }
  if (!frames.length) { return; }
  var at = 0, timer = null;
  var stage = story.querySelector(".stage");
  var bar = el("div", "controls"), back = el("button", "", "Back"), play = el("button", "play", "Play"), next = el("button", "", "Next");
  var count = el("span", "count"), reel = el("div", "reel");
  function show(i) {
    at = (i + frames.length) % frames.length;
    frames.forEach(function (f, k) { f.classList.toggle("on", k === at); });
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
    var view = function (which) {
      story.setAttribute("data-view", which);
      pictures.classList.toggle("on", which === "pictures");
      recording.classList.toggle("on", which === "film");
      if (which === "film") { stop(); } else if (video) { video.pause(); }
    };
    pictures.onclick = function () { view("pictures"); };
    recording.onclick = function () { view("film"); };
    pick.appendChild(pictures);
    pick.appendChild(recording);
    story.insertBefore(pick, story.firstChild);
    view("pictures");
  }
  if (frames.length < 2) { bar.style.display = "none"; reel.style.display = "none"; stage.onclick = null; stage.style.cursor = "auto"; }
  story.classList.add("live");
  show(0);
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


def to_look_at(data: dict) -> list[str]:
    """One "amber" or "red" for each thing the board marks: the walk, the checks, each group of findings the record
    does not show as fixed with a check or as not a defect, each finder that did not run, fate lines matching no
    finding, findings whose pass is not recognised, and no findings file read."""
    tones = [TONES.get(walk_verdict(data)[0], ""), TONES.get(checks_verdict(data)[0], "")]
    tones += [TONES.get(state_look(state)[1], "") for state, _ in data["groups"]]
    tones += ["amber"] * (len(data["absent"]) + bool(data["orphans"]) + (not data["files"]) + bool(odd_passes(data)))
    return [tone for tone in tones if tone in ("amber", "red")]


def odd_passes(data: dict) -> int:
    """How many findings name a pass the format does not."""
    return sum(row["other"] for row in data["by_finder"].values())


def tile(look: str, label: str, words: str, sub_html: str, href: str) -> str:
    """One of the two verdict tiles: a sign, what it is, the verdict in words, and one line under it."""
    tone = TONES.get(look, "")
    return (f'<a class="tile {tone}" href="{e(href)}">{mark(tone)}<span class="label">{e(label)}</span>'
            f"<strong>{e(words)}</strong>{sub_html}</a>")


def render_walk_tile(data: dict) -> str:
    recording = data["recording"] or {}
    ran = "Ended after" if recording.get("result") in WALK_ENDS else "Ran for"
    sub = (f'<span class="sub">{ran} {e(minutes(recording.get("minutes")))}, on commit <code>{e(recording.get("commit", "unknown"))}</code></span>'
           if recording else '<span class="sub">So there is no recording and there are no pictures</span>')
    look, words = walk_verdict(data)
    return tile(look, "Acceptance walk", words, sub, "#recording")


def render_checks_tile(data: dict) -> str:
    runs, tip = data["runs"], (data["git"] or {}).get("tip")
    full, later = runs["full"], runs["later"]
    look, words = checks_verdict(data)
    if full is None:
        sub = f'<span class="sub">{e(runs["why_unknown"] or "No run of every check is logged for this branch.")}</span>'
    else:
        off = stale(full.get("tip", "unknown"), full.get("dirty"), tip)
        looks = {"green": "green" if look == "green" else "", "red": "red"}  # a check is drawn green only when the verdict is
        each = "".join(f'<span class="chk {looks.get(str(check.get("result")), "")}">{e(check.get("name", "?"))}: {e(check.get("result", "unknown"))}</span>'
                       for check in full.get("checks") or [])
        sub = f'<span class="sub">{each}</span><span class="sub">The last run of every check took {e(minutes(full.get("minutes")))}</span>'
        sub += f'<span class="sub">This run was {e(off)}.</span>' if off else ""
    if later and (full is None or later.get("result") != "green"):  # said on the tile, not only in the folded list
        sub += f'<span class="sub">{e(later_said(runs))}</span>'
    return tile(look, "Checks", words, sub, "#facts")


def render_findings_tile(data: dict) -> str:
    """The findings as one bar, a part for each thing that became of them, and a label for each part that links to its list."""
    items, bar = [], ""
    if data["findings"]:
        parts = []
        for index, (state, rows) in enumerate(data["groups"]):
            title, look = state_look(state)[:2]
            swatch = SEGMENTS.get(state, "s-bad")
            parts.append(f'<span class="{swatch}" style="flex-grow: {len(rows)}" title="{e(title)}: {len(rows)}"></span>')
            items.append(pill(f"{title}: {len(rows)}", look, f"#group-{index}", swatch))
        count = len(data["findings"])
        said = f"{number(count)} found"
        bar = f'<div class="bar" role="img" aria-label="{e(said)}, by what became of them">{"".join(parts)}</div>'
    else:
        count = len(data["files"])
        said = "None found" if count else "Nobody looked"
        items.append(pill(f"No findings in the {count} findings file{'' if count == 1 else 's'} read" if count
                          else "No findings file was read", "" if count else "amber", "#finders"))
    items += [pill(f"{FINDERS[finder]}: no findings file", "amber", "#finders") for finder in data["absent"]]
    if data["orphans"]:
        items.append(pill(f"Fate lines matching no finding: {len(data['orphans'])}", "amber", "#findings"))
    if odd_passes(data):
        items.append(pill(f"Pass not recognised: {odd_passes(data)}", "amber", "#finders"))
    return (f'<div class="tile wide"><span class="label">Findings: what the walkers and reviewers reported</span>'
            f'<strong>{e(said)}</strong>{bar}<ul class="standing">{"".join(f"<li>{item}</li>" for item in items)}</ul></div>')


def render_standing(data: dict) -> str:
    """The board under the title: how many things need a look, then the walk, the last run of every check, and the findings."""
    flagged = to_look_at(data)
    if flagged:
        worst, count = ("red" if "red" in flagged else "amber"), len(flagged)
        headline = (f'<p class="headline {worst}">{mark(worst)}{count} thing{"" if count == 1 else "s"} to look at before you decide</p>'
                    '<p class="soft">Each is marked amber or red below. Counted by the script from git and the record files, not by an agent.</p>')
    else:
        settled = ("every finding is recorded as fixed, with its check named, or as not a defect. What became of a finding is "
                   "the agents' record: the script did not test it" if data["findings"] else "the findings files hold no findings")
        headline = (f'<p class="headline green">{mark("green")}Nothing on record needs a second look</p>'
                    "<p class=\"soft\">Counted by the script: the walk passed and every check was green on the build's last commit, "
                    f"and {settled}.</p>")
    headline += f'<p class="soft"><a href="#summary">{e(left_said(data))}</a></p>'
    return f'{headline}<div class="board">{render_walk_tile(data)}{render_checks_tile(data)}{render_findings_tile(data)}</div>'


def render_header(data: dict) -> str:
    facts = data["git"]
    if facts:
        asked = f" (asked for as {e(data['base_ref'])} to {e(data['tip_ref'])})" if data["base_ref"] else ""
        covers = (f"Covers {e(number(facts['commits']))} commits, <code>{e(facts['base'])}..{e(facts['tip'])}</code>{asked}: "
                  f"{e(when(facts['first']))} to {e(when(facts['last']))}.")
    else:
        covers = f"The range of commits it covers is {unknown()}."
    return (f'<header><p class="kicker">Build hand-over</p><h1>{e(data["feature"])}</h1>'
            f'<p class="soft">{covers}</p>{render_standing(data)}</header>')


def shot_parts(shot) -> tuple[str, str]:
    """(caption, address) of one screenshot. A shot is its file name, or {"name", "src"} when the picture is inside the page."""
    name = shot["name"] if isinstance(shot, dict) else str(shot)
    step = re.search(r"-(\d\d)-(.+)\.png$", name)
    caption = f"Step {int(step.group(1))}: {step.group(2).replace('-', ' ')}" if step else name
    return caption, shot["src"] if isinstance(shot, dict) else "shots/" + urllib.parse.quote(name)


def render_recording(data: dict) -> str:
    """The walk: its verdict, its screenshots as a picture story, and the recording."""
    recording, head = data["recording"], '<section id="recording"><h2>The walk, in pictures</h2>'
    if not recording:
        return head + ("<p>No recording: the walk was not run for this page.</p>"
                       "<p>No screenshots: the walk was not run for this page.</p></section>")
    look, words = walk_verdict(data)
    megabytes, tip, commit = recording.get("megabytes"), (data["git"] or {}).get("tip"), recording.get("commit", "unknown")
    said = [f'Run {e(when(recording.get("at")))} on commit <code>{e(commit)}</code>'
            f'{", with uncommitted changes in the folder" if recording.get("dirty") else ""}.']
    if tip and commit != tip:
        said.append(f"That is not the last commit of the build ({e(tip)}): the walk ran on the code that was in the folder at the time.")
    if recording.get("reason"):
        said.append(f'{e(recording["reason"])}.')
    if recording.get("result") != "passed":
        said.append('What it printed is in <a href="walk-output.txt"><code>walk-output.txt</code></a>, beside this page.')
    said.append(f'It ran for {e(minutes(recording.get("minutes")))}{f"; the recording is {e(megabytes)} MB" if megabytes is not None else ""}.')
    frames = []
    for index, shot in enumerate(data["shots"]):
        caption, src = shot_parts(shot)
        lazy = ' loading="lazy"' if index and not src.startswith("data:") else ""  # only a picture that is a file can wait
        frames.append(f'<figure class="frame"><img src="{e(src)}" alt="{e(caption)}"{lazy}>'
                      f"<figcaption>{e(caption)}</figcaption></figure>")
    stage = f'<div class="stage">{"".join(frames)}</div>' if frames else "<p>No screenshots: the walk left none.</p>"
    film = ('<div class="film"><video controls preload="metadata" src="recording.webm"></video>'
            '<p class="soft cantplay">This window cannot play the recording. Open <a href="recording.webm"><code>recording.webm</code></a>, '
            "which is beside this page, in Safari or Chrome.</p></div>" if megabytes is not None else "<p>It left no video file.</p>")
    count, passed, filmed = len(data["shots"]), recording.get("result") == "passed", megabytes is not None
    whole = "the whole journey by keyboard alone" if passed else "up to where it stopped"
    watch = f", or watch the recording{' of all of it' if passed else ''}" if filmed else ""
    about = (f"{count} moments from the acceptance walk, {whole}. Step through them{watch}." if count > 1
             else f"1 moment from the acceptance walk, {whole}.{' The recording shows the rest.' if filmed else ''}" if count
             else f"The acceptance walk, {whole}.")
    return (f'{head}<p>{pill(words, look)} {about}</p><div class="story" id="story" tabindex="-1">{stage}{film}</div>'
            f'<p class="soft">{" ".join(said)} Walk: <code>{e(recording.get("walk", ""))}</code></p></section>')


def render_summary(data: dict) -> str:
    summary = data["summary"]
    head = '<section id="summary"><h2>In the builder\'s words</h2>'
    if summary is None:
        return head + f'<p>The build agent wrote no summary: {unknown("hand-over.json is missing")}</p></section>'
    cards = []
    for key, kicker, title in (("what", "What", "What was built"), ("so_what", "So what", "What it gives you"),
                               ("now_what", "Now what", "What is left for you")):
        lines = summary.get(key) or []
        listed = lambda some: "".join(f"<li>{e(line)}</li>" for line in some)  # noqa: E731
        first, rest = lines[:SUMMARY_LINES], lines[SUMMARY_LINES:]  # the agent writes the weightiest first; the tail is folded, and counted
        more = f"<details><summary>{len(rest)} more</summary><ul>{listed(rest)}</ul></details>" if rest else ""
        body = listed(first) if lines else f"<li>{unknown('nothing written')}</li>"
        cards.append(f'<div class="card{" next" if key == "now_what" else ""}"><p class="kicker">{kicker}</p><h3>{title}</h3><ul>{body}</ul>{more}</div>')
    return (head + '<p class="source agent">Written by the build agent. These are its words, copied from hand-over.json; '
            'the script did not check them.</p>' + f'<div class="cards">{"".join(cards)}</div></section>')


def render_last_run(data: dict) -> str:
    """The last run of every check, with its checks; then, in words, any later run that ran only some."""
    runs, tip = data["runs"], (data["git"] or {}).get("tip")
    full, later, said = runs["full"], runs["later"], []
    if full is None:
        said.append(unknown())
    else:
        off = stale(full.get("tip", "unknown"), full.get("dirty"), tip)
        looks = {"green": "amber" if off else "green", "red": "red"}  # green is drawn green only for the last commit as committed
        listed = "".join(
            f'<li>{e(check.get("name", "?"))}: {pill(check.get("result", "unknown"), looks.get(str(check.get("result")), ""))}'
            f'{"" if check.get("result") == "not run" else " " + e(minutes(check.get("minutes"))) + ","} '
            f'output <code>{e(check.get("output", ""))}</code></li>' for check in full.get("checks") or [])
        look = looks.get(str(full.get("result")), "amber")
        said.append(f'{pill(full.get("result", "unknown"), look)} {e(when(full.get("at")))}, {e(minutes(full.get("minutes")))}, '
                    f'on commit <code>{e(full.get("tip", "unknown"))}</code>')
        if off:
            said.append(f'<p><span class="warned">This run was {e(off)}: it does not show the last commit as committed passes.</span></p>')
        said.append(f"<ul>{listed}</ul>")
    if later:
        said.append(f"<p>{e(later_said(runs))}</p>")
    return "".join(said)


def stat(label: str, value_html: str, note_html: str = "", wide: bool = False) -> str:
    """One number of the build, drawn large, with one line under it."""
    return (f'<div class="stat{" span" if wide else ""}"><span class="kicker">{e(label)}</span>'
            f'<span class="value">{value_html}</span><span class="note">{note_html}</span></div>')


def render_stats(data: dict) -> str:
    """The build's numbers as tiles: time, commits, files, lines by kind, tests, and every checks run as a square."""
    facts, runs = data["git"] or {}, data["runs"]
    value = lambda key: e(number(facts.get(key))) if facts else unknown()  # noqa: E731
    tiles = [stat("Build time", e(minutes(facts["minutes"])) if facts.get("minutes") is not None else unknown(), "first commit to last, on the clock"),
             stat("Commits", value("commits")), stat("Files changed", value("files"))]
    kinds = [(kind, count) for kind, count in (facts.get("added_by") or {}).items() if count]
    if kinds:
        names = {"product": "product", "tests and walks": "tests and walks"}
        bar = "".join(f'<span class="c{index}" style="flex-grow: {count}" title="{e(kind)}: {e(number(count))}"></span>'
                      for index, (kind, count) in enumerate(kinds, 1))
        legend = "".join(f'<span><i class="sw c{index}"></i>{e(names.get(kind, "build records"))} {e(number(count))}</span>'
                         for index, (kind, count) in enumerate(kinds, 1))
        tiles.append(stat("Lines added", value("added"), f'<span class="bar">{bar}</span><span class="legend">{legend}</span>'
                          f'{e(number(facts.get("removed")))} removed', wide=True))
    else:
        tiles.append(stat("Lines added", value("added"), f'{value("removed")} removed' if facts else ""))
    tiles.append(stat("Tests added", value("tests_added"), f'{value("tests_removed")} removed' if facts else ""))
    if runs["runs"] is None:
        tiles.append(stat("Checks runs", unknown(), e(runs["why_unknown"]), wide=True))
    else:
        history, shown = runs.get("history") or [], (runs.get("history") or [])[-80:]
        squares = "".join(
            f'<span class="{"r-" + run["result"] if run["result"] in ("green", "red") else ""}{"" if run["full"] else " part"}" '
            f'title="{e(when(run["at"]))}: {e(run["result"])}{"" if run["full"] else ", some checks only"}"></span>' for run in shown)
        more = f"The last {len(shown)} are drawn. " if len(history) > len(shown) else ""
        tiles.append(stat("Checks runs", f'{e(number(runs["runs"]))}', f'<span class="runs">{squares}</span>'
                          f'{e(number(runs["red"]))} red. {more}Oldest first. Blue was green when it ran, red was red; a hollow square ran only some checks.', wide=True))
    return f'<div class="stats">{"".join(tiles)}</div>'


def render_facts(data: dict) -> str:
    facts, runs, files = data["git"] or {}, data["runs"], data["files"]
    span = f"git, {data['git']['base']}..{data['git']['tip']}" if data["git"] else "git: no range was given"
    value = lambda key: e(number(facts.get(key))) if facts else unknown()  # noqa: E731
    flagged = lambda count, look: f'<span class="{look}">{e(number(count))}</span>' if count else e(number(count))  # noqa: E731
    every = ", ".join(runs["names"])
    log = runs["why_unknown"] or f".checks/runs.jsonl, the lines for branch {runs['branch']}"
    last = log if runs["full"] or runs["why_unknown"] else f"{log}: none of them is a run of every check ({every})"
    red = unknown() if runs["red"] is None else f"{e(number(runs['red']))} of {e(number(runs['runs']))} runs"
    no_fate = sum(1 for f in data["findings"] if f["state"] == "no-fate")
    none_read = unknown("no findings file was read")
    split = ("; of them " + ", ".join(f"{number(count)} {kind}" for kind, count in facts["added_by"].items())) if facts.get("added_by") else ""
    tests = f"{value('tests_added')} added, {value('tests_removed')} removed" if facts else unknown()
    rows = [
        fact("Last checks run", render_last_run(data), last),
        fact("Red check runs", red, log if runs["why_unknown"] else f"{log}; every run is counted, a run of one named check too"),
        fact("Findings recorded", e(number(len(data["findings"]))) if files else none_read,
             f"findings/*.jsonl: {number(len(files))} file{'' if len(files) == 1 else 's'} read"),
        fact("Findings with no fate", flagged(no_fate, "badly") if files else none_read, "findings with no fate named in fates.jsonl"),
        fact("Fate lines matching no finding", flagged(len(data["orphans"]), "warned"), "lines of fates.jsonl whose id is no finding's"),
        fact("Commits", value("commits"), span),
        fact("First commit", e(when(facts.get("first"))) if facts.get("first") else unknown(), span),
        fact("Last commit", e(when(facts.get("last"))) if facts.get("last") else unknown(), span),
        fact("Build time", e(minutes(facts["minutes"])) if facts.get("minutes") is not None else unknown(),
             "last commit minus first commit: clock time between them, not time worked"),
        fact("Files changed", value("files"), "git: the files that differ between the two ends of the range"),
        fact("Lines added", value("added"), f"git: lines added in those files{split}"),
        fact("Lines removed", value("removed"), "git: lines removed from those files"),
        fact("Tests", tests, "lines starting def test_ that the build added and removed under tests/ and walks/; "
                             "a test that was moved or renamed counts as both"),
    ]
    return ('<section id="facts"><h2>The build in numbers</h2><p class="source script">Computed by handover.py from git and the build\'s '
            'record files. No agent typed a number here.</p>' + render_stats(data) +
            '<details class="record"><summary>Every number, and where it came from</summary>'
            f'<dl class="facts">{"".join(rows)}</dl></details></section>')


def render_finders(data: dict) -> str:
    """Who looked and what they found: one row per finder, then every findings file read with its count."""
    counts, files = data["by_finder"], data["files"]
    other = any(row["other"] for row in counts.values())
    cell = lambda n: f'<td class="n">{e(n)}</td>' if n else '<td class="n soft">none recorded</td>'  # noqa: E731
    rows = []
    for finder, row in counts.items():
        cells = cell(row["first"]) + cell(row["recheck"])
        if other:
            cells += f'<td class="n">{unknown(row["other"])}</td>' if row["other"] else '<td class="n soft">none</td>'
        if finder in data["absent"]:
            cells = f'<td colspan="{2 + other}">{unknown("no findings file: did not run")}</td>'
        rows.append(f"<tr><th>{e(FINDERS.get(finder, finder or 'no finder named'))}</th>{cells}</tr>")
    extra = '<th class="n">Pass not recognised</th>' if other else ""
    read = "".join(f"<li><code>{e(name)}</code>: {e(number(len(found))) if found else 'looked, found nothing'}</li>"
                   for name, found in files.items())
    read = (f'<details class="record"><summary>The {number(len(files))} findings file{"" if len(files) == 1 else "s"} read</summary>'
            f'<ul class="files">{read}</ul></details>' if files
            else f"<p>{unknown('No findings file was read, so the record does not show that anyone looked.')}</p>")
    return ('<section id="finders"><h2>Who looked</h2>'
            '<p class="source script">Counted by handover.py from findings/*.jsonl. The re-check is the second look, after the fixes. '
            'A finder writes its file even when it finds nothing, so a finder with no file did not run.</p>'
            f'<div class="scroll"><table><thead><tr><th>Found by</th><th class="n">{PASSES["first"]}</th><th class="n">{PASSES["recheck"]}</th>{extra}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>{read}</section>')


def render_finding(finding: dict, shared: str = "") -> str:
    """One finding as a card. `shared` is a reason its whole group gives, already printed once above the cards."""
    severity = str(finding.get("severity", "") or "not recorded")
    finder, which = str(finding.get("finder", "")), str(finding.get("pass", ""))
    meta = [finding.get("id", ""), FINDERS.get(finder, finder), PASSES.get(which, which), finding.get("area", ""),
            SEVERITIES.get(severity, severity)]
    lines = [f'<p class="what">{e(finding.get("what", ""))}</p>',
             f'<p class="meta">{" · ".join(e(part) for part in meta if part)}</p>']
    if finding.get("where"):
        lines.append(f'<p class="meta">Where: {e(finding["where"])}</p>')
    fate = finding["fate"]
    if finding.get("check") and finding["check"] != (fate or {}).get("check"):  # said once when the fate names the same check
        lines.append(f'<p class="meta">Shown by: <code>{e(finding["check"])}</code></p>')
    if fate:
        said = [f"{e(state_look(finding['state'])[0])}."]
        if fate.get("commit"):
            said.append(f"Commit <code>{e(fate['commit'])}</code>.")
        if str(fate.get("check") or "").strip():
            said.append(f"Check: <code>{e(fate['check'])}</code>.")
        if fate.get("why") and fate["why"] != shared:
            said.append(e(fate["why"]))
        lines.append(f'<p class="fate">{" ".join(said)}</p>')
    if finding["lacks"]:
        lines.append(f'<p><span class="warned">Not found: {e(finding["lacks"])}.</span></p>')
    return f'<li class="finding">{"".join(lines)}</li>'


def render_findings(data: dict) -> str:
    head = ('<section id="findings"><h2>Every finding, and what became of it</h2>'
            '<p class="source agent">Joined by handover.py from findings/*.jsonl and fates.jsonl. The words of each finding are copied '
            'from the findings files and the words of each fate from fates.jsonl; the script did not check them. '
            'The open groups are the findings left as they are and those whose record is missing or does not hold up; '
            'the groups recorded as fixed or as not a defect are folded.</p>')
    orphans = ""
    if data["orphans"]:
        count = len(data["orphans"])
        listed = "".join(f'<li><code>{e(fate.get("id", ""))}</code>: {e(fate.get("fate") or "no fate named")}. {e(fate.get("why") or "")}</li>'
                         for fate in data["orphans"])
        orphans = (f'<div class="orphans"><p><strong>{count} fate line{"" if count == 1 else "s"} name{"s" if count == 1 else ""} a finding '
                   'the page did not read.</strong> Findings may have been written somewhere handover.py does not look '
                   f'(it reads findings/*.jsonl only).</p><ul>{listed}</ul></div>')
    if not data["findings"]:
        none = "" if orphans else ("<p>The findings files read hold no findings.</p>" if data["files"]
                                   else "<p>No findings file was read, so there is nothing to list.</p>")
        return head + orphans + none + "</section>"
    groups = []
    for index, (state, rows) in enumerate(data["groups"]):
        title, look, opened, note = state_look(state, data["verified"])
        whys = {str((row["fate"] or {}).get("why") or "") for row in rows}
        shared = whys.pop() if len(rows) > 1 and len(whys) == 1 else ""  # one reason for all: said once, not on every card
        same = f'<p class="fate">The record gives the same reason for all {len(rows)}: {e(shared)}</p>' if shared else ""
        groups.append(
            f'<details id="group-{index}" class="group {look}"{" open" if opened else ""}>'
            f'<summary><i class="sw {SEGMENTS.get(state, "s-bad")}"></i><h3>{e(title)}</h3><span class="count">{len(rows)}</span></summary>'
            f'<p class="soft">{e(note)}</p>{same}'
            f'<ol class="findings">{"".join(render_finding(row, shared) for row in rows)}</ol></details>')
    return head + orphans + "".join(groups) + "</section>"


def render(data: dict) -> str:
    """The whole page, as one HTML document with its CSS and its one small script inside."""
    built = data["built"]
    footer = (f'Built by handover.py {e(when(built.get("at")))} from the folder at commit <code>{e(built.get("commit", "unknown"))}</code>.'
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


def record_walk(root: pathlib.Path, feature: str, out: pathlib.Path) -> dict:
    """Run the acceptance walk with recording on; leave recording.webm, shots/, recording.json and walk-output.txt in `out`.
    The result is passed, failed (pytest ran it and it failed), did not run (pytest ended any other way) or did not finish."""
    scratch, shots = out / "recording-tmp", out / "shots"
    for folder in (scratch, shots):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
    for old in ("recording.webm", "recording.json"):  # an earlier run's pass must not outlive this run
        (out / old).unlink(missing_ok=True)
    record = {"walk": WALK, **tree_state(root)}
    started = time.time()
    try:
        run = subprocess.run(
            [str(root / ".venv" / "bin" / "python"), "-m", "pytest", WALK, "-q", "-p", "no:cacheprovider"],
            cwd=root, capture_output=True, text=True, timeout=900,
            env={**os.environ, "WALK_RECORD": str(scratch), "WALK_FEATURE": feature})
        printed = run.stdout + run.stderr
        record.update(result={0: "passed", 1: "failed"}.get(run.returncode, "did not run"), returncode=run.returncode)
        if record["result"] == "did not run":
            record["reason"] = f"pytest ended with exit code {run.returncode}, which is neither a pass nor a failed walk"
    except (subprocess.TimeoutExpired, OSError) as error:
        timed_out = isinstance(error, subprocess.TimeoutExpired)
        parts = [error.stdout, error.stderr] if timed_out else [str(error)]
        printed = "".join(part.decode(errors="replace") if isinstance(part, bytes) else part or "" for part in parts)
        record.update(result="did not finish", reason="It was stopped after 15 minutes" if timed_out else f"It could not start: {error}")
    record["minutes"] = round((time.time() - started) / 60, 1)
    (out / "walk-output.txt").write_text(printed, encoding="utf-8")
    # The walk's video and screenshots are named after it (walks/helper.py keep_video, shot_name); take this run's only.
    prefix = re.sub(r"[^A-Za-z0-9]+", "-", WALK.split("::", 1)[-1]).strip("-")
    if (scratch / f"{prefix}.webm").exists():
        (scratch / f"{prefix}.webm").replace(out / "recording.webm")
    shutil.rmtree(scratch, ignore_errors=True)
    for shot in sorted((root / ".scratch" / feature / "walks").glob(f"{prefix}-*.png")):
        if shot.stat().st_mtime >= started - 1:
            shutil.copy2(shot, shots / shot.name)
    (out / "recording.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def read_recording(out: pathlib.Path) -> dict | None:
    """recording.json, with the video's size in megabytes (None when there is no video file)."""
    record = read_json(out / "recording.json")
    if record is None:
        return None
    video = out / "recording.webm"
    return {**record, "megabytes": round(video.stat().st_size / 1e6, 1) if video.exists() else None}


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
    record = None
    if not args.no_walk:
        print(f"Recording the acceptance walk (about two minutes): {WALK}", flush=True)
        record = record_walk(root, args.feature, out)
    data = page_data(
        args.feature, base_ref=args.base, tip_ref=args.tip, git=facts, runs=runs, files=files, fates=fates,
        missing=missing_proof(root, facts["tip"], fates), summary=summary, recording=read_recording(out),
        shots=shots_of(out), built=tree_state(root),
    )
    page = out / "index.html"
    page.write_text(render(data), encoding="utf-8")
    print(page)
    if record and record["result"] != "passed":
        print(f"handover: the acceptance walk {WALK_ENDS[record['result']]}; what it printed is in {out / 'walk-output.txt'}")
    print(f"open {shlex.quote(str(page))}", flush=True)
    if show and not args.no_open:
        show(page.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main(show=webbrowser.open))
