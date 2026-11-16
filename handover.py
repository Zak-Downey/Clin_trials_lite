"""Build the one page a build ends with: .scratch/<feature>/hand-over/index.html.

    python3 handover.py <feature> [--base <ref>] [--tip <ref> --branch <name>] [--no-walk]

Run from the repo root. The facts on the page are computed here, from git and from
machine-readable files; the only words an agent writes are the what / so what / now
what of hand-over.json and the words inside findings and fates, and the page says so.
Nothing here reads Markdown.

Reads (all optional; what is missing is shown as missing, never as zero):
  git                                   the commits of <base>..<tip>
  .checks/runs.jsonl                    one line per checks run
  .scratch/<feature>/findings/*.jsonl   one line per finding; an empty file is a look that found nothing
  .scratch/<feature>/fates.jsonl        one line per finding id: what became of it
  .scratch/<feature>/hand-over.json     {"what": [...], "so_what": [...], "now_what": [...]}

Writes, beside index.html: recording.webm (the acceptance walk, recorded), recording.json
(when, on which commit and how it ended), shots/*.png and walk-output.txt. A walk that
fails is said on the page and in one printed line; the exit code is still 0.
"""

from __future__ import annotations

import argparse
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
    A file of another shape stops the run."""
    path = feature_dir / "hand-over.json"
    summary = read_json(path)
    lists = [summary.get(key, []) for key in ("what", "so_what", "now_what")] if isinstance(summary, dict) else [None]
    if summary is not None and not all(isinstance(lines, list) and all(isinstance(line, str) for line in lines) for lines in lists):
        raise SystemExit(f"handover: {path} must be an object whose what, so_what and now_what are each a list of sentences")
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
    """The checks runs of one branch: how many, how many red, the last run of every check (`full`) and, when
    the branch's last run is not that one, the last run (`later`). None, with why, where the log does not say."""
    facts = {"runs": None, "red": None, "full": None, "later": None, "branch": branch,
             "names": list(CHECK_NAMES if names is None else names), "why_unknown": ""}
    if runs is None:
        return {**facts, "why_unknown": "No checks run was logged: .checks/runs.jsonl does not exist."}
    own = [run for run in runs if run.get("branch") == branch]
    if not own:
        return {**facts, "why_unknown": f"The checks run log (.checks/runs.jsonl) has no line for branch {branch}."}
    full = [run for run in own if not missed(run, facts["names"])]
    return {**facts, "runs": len(own), "red": sum(run.get("result") == "red" for run in own),
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
    full = data["runs"]["full"]
    if full is None or full.get("result") not in ("green", "red"):
        return "amber", "Checks: unknown"
    if full["result"] == "red":
        return "red", "Checks RED"
    if stale(full.get("tip"), full.get("dirty"), (data["git"] or {}).get("tip")):
        return "amber", "Checks green, on code that is not the build's last commit"
    return "green", "Checks green"


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


CSS = """
:root { --bg: #f7f6f3; --card: #ffffff; --ink: #1f2428; --soft: #5c6670; --line: #dcd9d2;
  --accent: #0f6e63; --warn-bg: #fdf3d7; --warn-ink: #6b4a00; --warn-line: #e3c877;
  --bad-bg: #fde8e4; --bad-ink: #8a1f11; --bad-line: #e2a093; --ok-bg: #e4f3ec; --ok-ink: #0d5a3c; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #16191c; --card: #1e2226; --ink: #e6e8ea; --soft: #9aa5af; --line: #343a40;
    --accent: #6fcfbf; --warn-bg: #3a2f10; --warn-ink: #f2d27a; --warn-line: #6e5a1e;
    --bad-bg: #40201b; --bad-ink: #ffb4a6; --bad-line: #7a3a30; --ok-bg: #173327; --ok-ink: #9be0bd; } }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 60rem; margin: 0 auto; padding: 1.5rem 1rem 4rem; }
h1 { font-size: 2rem; line-height: 1.2; margin: 0 0 .4rem; overflow-wrap: anywhere; }
h2 { font-size: 1.3rem; margin: 0 0 .3rem; }
h3 { font-size: 1.05rem; margin: 0; display: inline; }
p { margin: .5rem 0; }
section { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 1.1rem 1.2rem; margin-top: 1.2rem; }
code { font: .88em ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }
a { color: var(--accent); }
.kicker { text-transform: uppercase; letter-spacing: .08em; font-size: .8rem; color: var(--soft); margin: 0; }
.soft, .source, figcaption, .meta, .fate, dd small { color: var(--soft); font-size: .9rem; }
.source { border-left: 3px solid var(--line); padding-left: .6rem; margin: .2rem 0 .9rem; }
.source.agent { border-left-color: var(--warn-line); }
video, img { max-width: 100%; height: auto; display: block; border: 1px solid var(--line); border-radius: 6px; background: #000; }
video { width: 100%; }
figure { margin: 0; }
.text { max-width: 44rem; }
.text h3 { display: block; margin-top: .9rem; }
.text ul { margin: .3rem 0 0; padding-left: 1.2rem; }
dl.facts { margin: 0; }
dl.facts > div { display: grid; grid-template-columns: 14rem 1fr; gap: .2rem 1rem; padding: .55rem 0; border-top: 1px solid var(--line); }
dl.facts > div:first-child { border-top: 0; }
dt { font-weight: 600; }
dd { margin: 0; overflow-wrap: anywhere; }
dd small { display: block; }
dd ul, ul.files { margin: .2rem 0; padding-left: 1.1rem; }
table { border-collapse: collapse; width: 100%; max-width: 38rem; }
th, td { text-align: left; padding: .4rem .8rem .4rem 0; border-top: 1px solid var(--line); }
thead th { border-top: 0; color: var(--soft); font-weight: 600; font-size: .9rem; }
td.n, th.n { text-align: right; }
.unknown, .warned { color: var(--warn-ink); background: var(--warn-bg); border-radius: 4px; padding: 0 .35rem; }
.badly { color: var(--bad-ink); background: var(--bad-bg); border-radius: 4px; padding: 0 .35rem; font-weight: 600; }
.pill { display: inline-block; border: 1px solid var(--line); border-radius: 999px; padding: 0 .6rem; font-size: .85rem; font-weight: 600;
  color: var(--ink); background: var(--card); text-decoration: none; }
.pill.green { background: var(--ok-bg); color: var(--ok-ink); border-color: transparent; }
.pill.red, .pill.bad { background: var(--bad-bg); color: var(--bad-ink); border-color: var(--bad-line); }
.pill.amber, .pill.warn { background: var(--warn-bg); color: var(--warn-ink); border-color: var(--warn-line); }
.pill.note { border: 1px dashed var(--warn-ink); color: var(--warn-ink); background: var(--card); }
ul.standing { list-style: none; display: flex; flex-wrap: wrap; gap: .5rem; margin: .3rem 0 0; padding: 0; }
ul.standing .pill { font-size: .95rem; padding: .1rem .8rem; }
details.group, .orphans { border: 1px solid var(--line); border-radius: 8px; margin-top: .8rem; padding: .6rem .9rem; }
details.group.bad { border: 2px solid var(--bad-ink); background: var(--bad-bg); }
details.group.bad > summary { color: var(--bad-ink); }
details.group.warn, .orphans { border-color: var(--warn-line); background: var(--warn-bg); }
details.group.warn > summary, .orphans > p:first-child { color: var(--warn-ink); }
details.group.note { border: 1px dashed var(--warn-ink); }
details.group.note > summary { color: var(--warn-ink); }
summary { cursor: pointer; }
.count { font-weight: 600; margin-left: .4rem; }
ol.findings { list-style: none; margin: .6rem 0 0; padding: 0; }
ol.findings > li { background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 6px; padding: .6rem .8rem; margin-top: .5rem; overflow-wrap: anywhere; }
ol.findings p { margin: .15rem 0; }
.shots { display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: 1rem; }
footer { color: var(--soft); font-size: .85rem; margin-top: 1.5rem; }
@media (max-width: 600px) {
  body { font-size: 16px; }
  section { padding: .9rem .8rem; }
  dl.facts > div { grid-template-columns: 1fr; }
}
"""


def unknown(text: str = "unknown") -> str:
    return f'<span class="unknown">{e(text)}</span>'


def pill(text, look: str = "", href: str = "") -> str:
    """A rounded label. `look` is one of this script's own words (green, red, amber, bad, warn, note), never read text."""
    return f'<a class="pill {look}" href="{e(href)}">{e(text)}</a>' if href else f'<span class="pill {look}">{e(text)}</span>'


def fact(label: str, value_html: str, source: str) -> str:
    """One row of the facts: the label, the value (already HTML) and where it came from."""
    return f"<div><dt>{e(label)}</dt><dd>{value_html}<small>{e(source)}</small></dd></div>"


def render_standing(data: dict) -> str:
    """The strip under the title: the walk, the last run of every check, and the findings by what became of them."""
    items = [pill(walk_verdict(data)[1], walk_verdict(data)[0], "#recording"),
             pill(checks_verdict(data)[1], checks_verdict(data)[0], "#facts")]
    for index, (state, rows) in enumerate(data["groups"]):
        title, look = state_look(state)[:2]
        items.append(pill(f"{title}: {len(rows)}", look, f"#group-{index}"))
    if not data["findings"]:
        count = len(data["files"])
        items.append(pill(f"No findings in the {count} findings file{'' if count == 1 else 's'} read" if count
                          else "No findings file was read", "" if count else "amber", "#finders"))
    items += [pill(f"{FINDERS[finder]}: no findings file", "amber", "#finders") for finder in data["absent"]]
    if data["orphans"]:
        items.append(pill(f"Fate lines matching no finding: {len(data['orphans'])}", "amber", "#findings"))
    return ('<p class="soft">Where it stands, counted by the script from git and the record files. '
            f'Each links to its part of the page.</p><ul class="standing">{"".join(f"<li>{item}</li>" for item in items)}</ul>')


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


def render_recording(data: dict) -> str:
    recording, head = data["recording"], '<section id="recording"><h2>The recording</h2>'
    if not recording:
        return head + "<p>No recording: the walk was not run for this page.</p></section>"
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
    said.append(f'It ran for {e(minutes(recording.get("minutes")))}{f"; the file is {e(megabytes)} MB" if megabytes is not None else ""}.')
    video = ('<video controls preload="metadata" src="recording.webm"></video>' if megabytes is not None else "")
    about = ("The acceptance walk: the whole journey by keyboard alone, in Chromium at 1440 x 900, slowed down so it can be followed."
             if megabytes is not None else "It left no video file.")
    return (f'{head}<figure>{video}<figcaption><p>{pill(words, look)} {about}</p>'
            f'<p>{" ".join(said)} Walk: <code>{e(recording.get("walk", ""))}</code></p></figcaption></figure></section>')


def render_summary(data: dict) -> str:
    summary = data["summary"]
    head = '<section id="summary"><h2>What, so what, now what</h2>'
    if summary is None:
        return head + f'<p>The build agent wrote no summary: {unknown("hand-over.json is missing")}</p></section>'
    parts = []
    for key, title in (("what", "What"), ("so_what", "So what"), ("now_what", "Now what")):
        lines = summary.get(key) or []
        body = "".join(f"<li>{e(line)}</li>" for line in lines) if lines else f"<li>{unknown('nothing written')}</li>"
        parts.append(f"<h3>{title}</h3><ul>{body}</ul>")
    return (head + '<p class="source agent">Written by the build agent. These are its words, copied from hand-over.json; '
            'the script did not check them.</p>' + f'<div class="text">{"".join(parts)}</div></section>')


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
        ran = ", ".join(str(check.get("name", "?")) for check in later.get("checks") or [])
        said.append(f'<p>{"A later run" if full else "The last run"} of {e(ran or "no check")} only was {e(later.get("result", "unknown"))} at '
                    f'{e(when(later.get("at")))}; it did not run {e(", ".join(missed(later, runs["names"])))}.</p>')
    return "".join(said)


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
    return ('<section id="facts"><h2>The facts</h2><p class="source">Computed by handover.py from git and the build\'s record files. '
            'No agent typed a number here; each line names where it came from.</p>'
            f'<dl class="facts">{"".join(rows)}</dl></section>')


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
    read = f'<ul class="files">{read}</ul>' if files else f"<p>{unknown('No findings file was read, so the record does not show that anyone looked.')}</p>"
    return ('<section id="finders"><h2>Findings by who found them</h2>'
            '<p class="source">Counted by handover.py from findings/*.jsonl. The re-check is the second look, after the fixes. '
            'A finder writes its file even when it finds nothing, so a finder with no file did not run.</p>'
            f'<table><thead><tr><th>Found by</th><th class="n">{PASSES["first"]}</th><th class="n">{PASSES["recheck"]}</th>{extra}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table><h3>Findings files read</h3>{read}</section>')


def render_finding(finding: dict) -> str:
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
        if fate.get("why"):
            said.append(e(fate["why"]))
        lines.append(f'<p class="fate">{" ".join(said)}</p>')
    if finding["lacks"]:
        lines.append(f'<p><span class="warned">Not found: {e(finding["lacks"])}.</span></p>')
    return f'<li class="finding">{"".join(lines)}</li>'


def render_findings(data: dict) -> str:
    head = ('<section id="findings"><h2>Every finding read and what became of it</h2>'
            '<p class="source">Joined by handover.py from findings/*.jsonl and fates.jsonl. The words of each finding are copied '
            'from the findings files and the words of each fate from fates.jsonl; the script did not check them.</p>')
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
        groups.append(
            f'<details id="group-{index}" class="group {look}"{" open" if opened else ""}>'
            f'<summary><h3>{e(title)}</h3><span class="count">{len(rows)}</span></summary>'
            f'<p class="soft">{e(note)}</p>'
            f'<ol class="findings">{"".join(render_finding(row) for row in rows)}</ol></details>')
    return head + orphans + "".join(groups) + "</section>"


def render_shots(data: dict) -> str:
    head = '<section id="shots"><h2>Screenshots from the walk</h2>'
    if not data["shots"]:
        return head + f'<p>No screenshots: the walk {"left none" if data["recording"] else "was not run for this page"}.</p></section>'
    figures = []
    for name in data["shots"]:
        step = re.search(r"-(\d\d)-(.+)\.png$", name)
        caption = f"{int(step.group(1))}. {step.group(2).replace('-', ' ')}" if step else name
        src = e("shots/" + urllib.parse.quote(name))
        figures.append(f'<figure><a href="{src}"><img loading="lazy" src="{src}" alt="{e(caption)}"></a>'
                       f"<figcaption>{e(caption)}</figcaption></figure>")
    return head + f'<div class="shots">{"".join(figures)}</div></section>'


def render(data: dict) -> str:
    """The whole page, as one HTML document with its CSS inside."""
    built = data["built"]
    footer = (f'Built by handover.py {e(when(built.get("at")))} from the folder at commit <code>{e(built.get("commit", "unknown"))}</code>.'
              if built else "Built by handover.py.")
    body = "".join([
        render_header(data), render_recording(data), render_summary(data), render_facts(data),
        render_finders(data), render_findings(data), render_shots(data),
    ])
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Hand-over: {e(data["feature"])}</title><style>{CSS}</style></head>\n'
            f'<body><main>{body}<footer>{footer}</footer></main></body></html>\n')


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


def main(argv=None, root: pathlib.Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description="Build the hand-over page of one feature.")
    parser.add_argument("feature", help="the folder name under .scratch/")
    parser.add_argument("--base", default="main", help="the commit the build started from (default main)")
    parser.add_argument("--tip", default="HEAD", help="the build's last commit (default HEAD); give --branch with it")
    parser.add_argument("--branch", default=None, help="the branch whose checks runs are counted (default the current branch)")
    parser.add_argument("--no-walk", action="store_true", help="do not run and record the walk; keep any earlier recording")
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
        shots=sorted(path.name for path in (out / "shots").glob("*.png")), built=tree_state(root),
    )
    page = out / "index.html"
    page.write_text(render(data), encoding="utf-8")
    print(page)
    if record and record["result"] != "passed":
        print(f"handover: the acceptance walk {WALK_ENDS[record['result']]}; what it printed is in {out / 'walk-output.txt'}")
    print(f"open {shlex.quote(str(page))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
