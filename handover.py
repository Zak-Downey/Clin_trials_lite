"""Build the one page a build ends with: .scratch/<feature>/hand-over/index.html.

    python3 handover.py <feature> [--base <ref>] [--tip <ref>] [--branch <name>] [--no-walk]

Run from the repo root. The facts on the page are computed here, from git and from
machine-readable files; the only words an agent writes are the what / so what / now
what of hand-over.json, and the page says so. Nothing here reads Markdown.

Reads (all optional; what is missing is shown as missing, never as zero):
  git                                   the commits of <base>..<tip>
  .checks/runs.jsonl                    one line per checks run
  .scratch/<feature>/findings/*.jsonl   one line per finding
  .scratch/<feature>/fates.jsonl        one line per finding id: what became of it
  .scratch/<feature>/hand-over.json     {"what": [...], "so_what": [...], "now_what": [...]}

Writes, beside index.html: recording.webm (the acceptance walk, recorded), recording.json
(when and on which commit it was recorded), shots/*.png and walk-output.txt.
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

ROOT = pathlib.Path(__file__).resolve().parent

# The walk that is recorded: the whole journey, keyboard only, Chromium at 1440 x 900.
WALK = "walks/test_acceptance_walk.py::test_walk_the_whole_journey_by_keyboard_alone[chromium-1440x900]"

FINDERS = {"walker": "Walker", "review": "Review", "early-read": "Early read", "you": "You"}
PASSES = {"first": "First pass", "recheck": "Re-check"}
SEVERITIES = {"blocks": "blocks use", "wrong": "wrong", "cosmetic": "cosmetic", "not recorded": "severity not recorded"}
# What became of a finding, in the order the page shows the groups.
STATES = {
    "no-fate": "No fate recorded",
    "left": "Left as it is",
    "fixed-no-check": "Fixed, no check named",
    "fixed": "Fixed",
    "not-a-defect": "Not a defect",
}
STATE_NOTES = {
    "no-fate": "No line in fates.jsonl names these findings, so the record does not say what became of them.",
    "left": "Recorded as known and left.",
    "fixed-no-check": "Recorded as fixed, but the record names no test or walk that shows the fix holds.",
    "fixed": "Recorded as fixed, each with the test or walk that shows it.",
    "not-a-defect": "Recorded as not a defect.",
}
OPEN_STATES = ("no-fate", "left", "fixed-no-check")  # drawn open and marked; the rest are folded


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


def read_findings(feature_dir: pathlib.Path) -> list[dict]:
    """Every finding of every findings/*.jsonl file, in file-name order."""
    return [row for path in sorted((feature_dir / "findings").glob("*.jsonl")) for row in read_jsonl(path)]


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
    """hand-over.json: the what / so what / now what an agent wrote. None when there is no file."""
    return read_json(feature_dir / "hand-over.json")


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


def tests_added(diff: str) -> int:
    """How many `def test_` lines a diff adds."""
    return len(re.findall(r"^\+\s*(?:async\s+)?def test_\w*\(", diff, re.M))


def git_facts(repo: pathlib.Path, base: str, tip: str) -> dict:
    """What git knows of base..tip: commits, first and last commit time, minutes between, the size of the diff."""
    times = sorted(git(repo, "log", "--format=%cI", f"{base}..{tip}").split(), key=moment)
    first, last = (times[0], times[-1]) if times else (None, None)
    span = moment(last) - moment(first) if times else None
    files = added = removed = 0
    for line in git(repo, "diff", "--numstat", f"{base}...{tip}").splitlines():
        plus, minus, _ = line.split("\t", 2)
        files += 1
        added += int(plus) if plus.isdigit() else 0  # a binary file has "-" for both
        removed += int(minus) if minus.isdigit() else 0
    return {
        "base": git(repo, "rev-parse", "--short", base), "tip": git(repo, "rev-parse", "--short", tip),
        "commits": len(times), "first": first, "last": last,
        "minutes": round(span.total_seconds() / 60) if span is not None else None,
        "files": files, "added": added, "removed": removed,
        "tests_added": tests_added(git(repo, "diff", f"{base}...{tip}", "--", "tests", "walks")),
    }


def run_facts(runs: list[dict] | None, branch: str) -> dict:
    """The checks runs of one branch: how many, how many red, the last. All None, with why, when the log does not say."""
    if runs is None:
        return {"runs": None, "red": None, "last": None, "branch": branch,
                "why_unknown": "No checks run was logged: .checks/runs.jsonl does not exist."}
    own = [run for run in runs if run.get("branch") == branch]
    if not own:
        return {"runs": None, "red": None, "last": None, "branch": branch,
                "why_unknown": f"The checks run log (.checks/runs.jsonl) has no line for branch {branch}."}
    return {"runs": len(own), "red": sum(run.get("result") == "red" for run in own), "last": own[-1],
            "branch": branch, "why_unknown": ""}


def state_of(fate: dict | None) -> str:
    """Which group a finding belongs to, given its fate line (or None)."""
    kind = (fate or {}).get("fate") or "no-fate"
    if kind == "fixed" and not str(fate.get("check") or "").strip():
        return "fixed-no-check"
    return kind


def join(findings: list[dict], fates: dict[str, dict]) -> list[dict]:
    """Each finding with its fate line (None when there is none) and its state."""
    joined = []
    for finding in findings:
        fate = fates.get(str(finding.get("id", "")))
        joined.append({**finding, "fate": fate, "state": state_of(fate)})
    return joined


def group_by_state(joined: list[dict]) -> list[tuple[str, list[dict]]]:
    """The joined findings in groups: no fate first, then STATES' order, then any fate the contract does not name."""
    order = list(STATES) + sorted({f["state"] for f in joined} - set(STATES))
    groups = [(state, [f for f in joined if f["state"] == state]) for state in order]
    return [(state, rows) for state, rows in groups if rows]


def orphan_fates(findings: list[dict], fates: dict[str, dict]) -> list[str]:
    """Fate ids that match no finding."""
    known = {str(f.get("id", "")) for f in findings}
    return [fate_id for fate_id in fates if fate_id not in known]


def count_by_finder(findings: list[dict]) -> dict[str, dict[str, int]]:
    """{finder: {"first": n, "recheck": n}}: the contract's four finders first, then any other."""
    counts = {finder: dict.fromkeys(PASSES, 0) for finder in FINDERS}
    for finding in findings:
        row = counts.setdefault(str(finding.get("finder", "")), dict.fromkeys(PASSES, 0))
        which = str(finding.get("pass", ""))
        row[which] = row.get(which, 0) + 1
    return counts


def page_data(feature: str, *, base_ref: str = "", tip_ref: str = "", git: dict | None = None,
              runs: dict | None = None, findings=(), fates: dict | None = None, finding_files: int | None = None,
              summary: dict | None = None, recording: dict | None = None, shots=(), built: dict | None = None) -> dict:
    """Everything the page shows, in one dictionary."""
    findings, fates = list(findings), fates or {}
    joined = join(findings, fates)
    return {
        "feature": feature, "base_ref": base_ref, "tip_ref": tip_ref, "git": git,
        "runs": runs or run_facts(None, ""), "summary": summary, "recording": recording, "shots": list(shots),
        "findings": joined, "groups": group_by_state(joined), "finding_files": finding_files,
        "by_finder": count_by_finder(findings), "orphans": orphan_fates(findings, fates), "built": built or {},
    }


# Rendering.

def e(value) -> str:
    """Any value as text that is safe inside HTML, attributes included."""
    return html.escape(str(value), quote=True)


def minutes(value) -> str:
    """A duration, always in minutes; None is unknown."""
    if value is None:
        return "unknown"
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
  --bad-bg: #fde8e4; --bad-ink: #8a1f11; --ok-bg: #e4f3ec; --ok-ink: #0d5a3c; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #16191c; --card: #1e2226; --ink: #e6e8ea; --soft: #9aa5af; --line: #343a40;
    --accent: #6fcfbf; --warn-bg: #3a2f10; --warn-ink: #f2d27a; --warn-line: #6e5a1e;
    --bad-bg: #40201b; --bad-ink: #ffb4a6; --ok-bg: #173327; --ok-ink: #9be0bd; } }
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
dd ul { margin: .2rem 0; padding-left: 1.1rem; }
table { border-collapse: collapse; width: 100%; max-width: 30rem; }
th, td { text-align: left; padding: .4rem .8rem .4rem 0; border-top: 1px solid var(--line); }
thead th { border-top: 0; color: var(--soft); font-weight: 600; font-size: .9rem; }
td.n, th.n { text-align: right; }
.unknown { color: var(--warn-ink); background: var(--warn-bg); border-radius: 4px; padding: 0 .35rem; }
.pill { display: inline-block; border-radius: 999px; padding: 0 .6rem; font-size: .85rem; font-weight: 600; }
.pill.green { background: var(--ok-bg); color: var(--ok-ink); }
.pill.red { background: var(--bad-bg); color: var(--bad-ink); }
details.group { border: 1px solid var(--line); border-radius: 8px; margin-top: .8rem; padding: .6rem .9rem; }
details.group.attention { border-color: var(--warn-line); background: var(--warn-bg); }
details.group.attention > summary { color: var(--warn-ink); }
summary { cursor: pointer; }
.count { font-weight: 600; margin-left: .4rem; }
ol.findings { list-style: none; margin: .6rem 0 0; padding: 0; }
ol.findings > li { background: var(--card); border: 1px solid var(--line); border-radius: 6px; padding: .6rem .8rem; margin-top: .5rem; overflow-wrap: anywhere; }
ol.findings p { margin: .15rem 0; }
.shots { display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: 1rem; }
.blank { display: flex; align-items: flex-end; gap: .8rem; margin: 1.6rem 0 .4rem; max-width: 36rem; }
.blank .rule { flex: 1; min-width: 5rem; border-bottom: 1.5px solid var(--ink); height: 1.2rem; }
footer { color: var(--soft); font-size: .85rem; margin-top: 1.5rem; }
@media (max-width: 600px) {
  body { font-size: 16px; }
  section { padding: .9rem .8rem; }
  dl.facts > div { grid-template-columns: 1fr; }
  .blank { flex-direction: column; align-items: stretch; gap: 0; }
}
"""


def unknown(text: str = "unknown") -> str:
    return f'<span class="unknown">{e(text)}</span>'


def fact(label: str, value_html: str, source: str) -> str:
    """One row of the facts: the label, the value (already HTML) and where it came from."""
    return f"<div><dt>{e(label)}</dt><dd>{value_html}<small>{e(source)}</small></dd></div>"


def render_header(data: dict) -> str:
    facts = data["git"]
    if facts:
        asked = f" (asked for as {e(data['base_ref'])} to {e(data['tip_ref'])})" if data["base_ref"] else ""
        covers = (f"Covers {e(number(facts['commits']))} commits, <code>{e(facts['base'])}..{e(facts['tip'])}</code>{asked}: "
                  f"{e(when(facts['first']))} to {e(when(facts['last']))}.")
    else:
        covers = f"The range of commits it covers is {unknown()}."
    return (f'<header><p class="kicker">Build hand-over</p><h1>{e(data["feature"])}</h1>'
            f'<p class="soft">{covers}</p></header>')


def render_recording(data: dict) -> str:
    recording = data["recording"]
    if not recording or recording.get("megabytes") is None:
        why = "the walk was not run for this page." if not recording else "the walk ran but left no video file."
        return f'<section><h2>The recording</h2><p>No recording: {e(why)}</p></section>'
    tip = (data["git"] or {}).get("tip")
    dirty = ", with uncommitted changes in the folder" if recording.get("dirty") else ""
    aside = ""
    if tip and recording.get("commit") != tip:
        aside = f" That is not the last commit of the range above ({e(tip)}): the walk ran on the code that was in the folder at the time."
    passed = recording.get("result") == "passed"
    verdict = '<span class="pill green">The walk passed</span>' if passed else '<span class="pill red">The walk FAILED</span>'
    return (
        '<section><h2>The recording</h2>'
        '<figure><video controls preload="metadata" src="recording.webm"></video>'
        f'<figcaption><p>{verdict} The acceptance walk: the whole journey by keyboard alone, in Chromium at 1440 x 900, '
        'slowed down so it can be followed.</p>'
        f'<p>Recorded {e(when(recording.get("at")))} on commit <code>{e(recording.get("commit", "unknown"))}</code>{e(dirty)}.{aside} '
        f'It ran for {e(minutes(recording.get("minutes")))}; the file is {e(recording["megabytes"])} MB. '
        f'Walk: <code>{e(recording.get("walk", ""))}</code></p></figcaption></figure></section>'
    )


def render_summary(data: dict) -> str:
    summary = data["summary"]
    head = '<section><h2>What, so what, now what</h2>'
    if summary is None:
        return head + f'<p>The build agent wrote no summary: {unknown("hand-over.json is missing")}</p></section>'
    parts = []
    for key, title in (("what", "What"), ("so_what", "So what"), ("now_what", "Now what")):
        lines = summary.get(key) or []
        body = "".join(f"<li>{e(line)}</li>" for line in lines) if lines else f"<li>{unknown('nothing written')}</li>"
        parts.append(f"<h3>{title}</h3><ul>{body}</ul>")
    return (head + '<p class="source agent">Written by the build agent. These are its words, copied from hand-over.json; '
            'the script did not check them.</p>' + f'<div class="text">{"".join(parts)}</div></section>')


def render_last_run(runs: dict) -> str:
    last = runs["last"]
    if last is None:
        return unknown()
    checks = "".join(
        f'<li>{e(check.get("name", "?"))}: <span class="pill {e(check.get("result", ""))}">{e(check.get("result", "unknown"))}</span> '
        f'{e(minutes(check.get("minutes")))}, output <code>{e(check.get("output", ""))}</code></li>'
        for check in last.get("checks") or [])
    dirty = ", with uncommitted changes" if last.get("dirty") else ""
    return (f'<span class="pill {e(last.get("result", ""))}">{e(last.get("result", "unknown"))}</span> '
            f'{e(when(last.get("at")))}, {e(minutes(last.get("minutes")))}, on commit <code>{e(last.get("tip", "unknown"))}</code>{e(dirty)}'
            f'<ul>{checks}</ul>')


def render_facts(data: dict) -> str:
    facts, runs = data["git"] or {}, data["runs"]
    span = f"git, {data['git']['base']}..{data['git']['tip']}" if data["git"] else "git: no range was given"
    value = lambda key: e(number(facts.get(key))) if facts else unknown()  # noqa: E731
    log = runs["why_unknown"] or f".checks/runs.jsonl, the lines for branch {runs['branch']}"
    red = unknown() if runs["red"] is None else f"{e(number(runs['red']))} of {e(number(runs['runs']))} runs"
    files = data["finding_files"]
    no_fate = sum(1 for f in data["findings"] if f["state"] == "no-fate")
    rows = [
        fact("Commits", value("commits"), span),
        fact("First commit", e(when(facts.get("first"))) if facts.get("first") else unknown(), span),
        fact("Last commit", e(when(facts.get("last"))) if facts.get("last") else unknown(), span),
        fact("Build time", e(minutes(facts["minutes"])) if facts.get("minutes") is not None else unknown(),
             "last commit minus first commit: clock time between them, not time worked"),
        fact("Files changed", value("files"), "git diff --numstat"),
        fact("Lines added", value("added"), "git diff --numstat"),
        fact("Lines removed", value("removed"), "git diff --numstat"),
        fact("Tests added", value("tests_added"), "lines starting def test_ that the diff adds under tests/ and walks/"),
        fact("Last checks run", render_last_run(runs), log),
        fact("Red check runs", red, log),
        fact("Findings recorded", e(number(len(data["findings"]))) if files else unknown("none recorded"),
             f"findings/*.jsonl: {number(files)} file{'' if files == 1 else 's'}" if files is not None else "findings/*.jsonl"),
        fact("Findings with no fate", e(number(no_fate)) if data["findings"] else unknown("none recorded"),
             "findings whose id has no line in fates.jsonl"),
    ]
    return ('<section><h2>The facts</h2><p class="source">Computed by handover.py from git and the build\'s record files. '
            'No agent typed a number here; each line names where it came from.</p>'
            f'<dl class="facts">{"".join(rows)}</dl></section>')


def render_finders(data: dict) -> str:
    head = '<section><h2>Defects by who found them</h2>'
    if not data["findings"]:
        return head + "<p>No findings were recorded for this build.</p></section>"
    cell = lambda n: f'<td class="n">{e(n)}</td>' if n else '<td class="n soft">none recorded</td>'  # noqa: E731
    rows = "".join(
        f"<tr><th>{e(FINDERS.get(finder, finder or 'no finder named'))}</th>{cell(counts.get('first', 0))}{cell(counts.get('recheck', 0))}</tr>"
        for finder, counts in data["by_finder"].items())
    return (head + '<p class="source">Counted by handover.py from findings/*.jsonl. The re-check is the second look, after the fixes.</p>'
            f'<table><thead><tr><th>Found by</th><th class="n">{PASSES["first"]}</th><th class="n">{PASSES["recheck"]}</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></section>")


def render_finding(finding: dict) -> str:
    severity = str(finding.get("severity", "") or "not recorded")
    meta = [finding.get("id", ""), FINDERS.get(finding.get("finder"), finding.get("finder", "")),
            PASSES.get(finding.get("pass"), finding.get("pass", "")), finding.get("area", ""),
            SEVERITIES.get(severity, severity)]
    lines = [f'<p class="what">{e(finding.get("what", ""))}</p>',
             f'<p class="meta">{" · ".join(e(part) for part in meta if part)}</p>']
    if finding.get("where"):
        lines.append(f'<p class="meta">Where: {e(finding["where"])}</p>')
    fate = finding["fate"]
    if finding.get("check") and finding["check"] != (fate or {}).get("check"):  # said once when the fate names the same check
        lines.append(f'<p class="meta">Shown by: <code>{e(finding["check"])}</code></p>')
    if fate:
        said = [f"{STATES.get(finding['state'], finding['state'])}."]
        if fate.get("commit"):
            said.append(f"Commit <code>{e(fate['commit'])}</code>.")
        if str(fate.get("check") or "").strip():
            said.append(f"Check: <code>{e(fate['check'])}</code>.")
        if fate.get("why"):
            said.append(e(fate["why"]))
        lines.append(f'<p class="fate">{e(said[0])} {" ".join(said[1:])}</p>')
    return f"<li>{''.join(lines)}</li>"


def render_findings(data: dict) -> str:
    head = '<section><h2>Every finding and what became of it</h2>'
    if not data["findings"]:
        return head + "<p>No findings were recorded for this build.</p></section>"
    groups = []
    for state, rows in data["groups"]:
        attention = state in OPEN_STATES or state not in STATES
        groups.append(
            f'<details class="group{" attention" if attention else ""}"{" open" if attention else ""}>'
            f'<summary><h3>{e(STATES.get(state, f"Fate: {state}"))}</h3><span class="count">{len(rows)}</span></summary>'
            f'<p class="soft">{e(STATE_NOTES.get(state, "A fate the record format does not name."))}</p>'
            f'<ol class="findings">{"".join(render_finding(row) for row in rows)}</ol></details>')
    orphans = ""
    if data["orphans"]:
        orphans = f'<p class="soft">Fate lines that match no finding: {e(", ".join(data["orphans"]))}.</p>'
    return (head + '<p class="source">Joined by handover.py from findings/*.jsonl and fates.jsonl. The words of each finding '
            'are the finder\'s.</p>' + "".join(groups) + orphans + "</section>")


def render_shots(data: dict) -> str:
    head = '<section><h2>Screenshots from the walk</h2>'
    if not data["shots"]:
        return head + "<p>No screenshots: the walk was not run for this page, or it took none.</p></section>"
    figures = []
    for name in data["shots"]:
        step = re.search(r"-(\d\d)-(.+)\.png$", name)
        caption = f"{int(step.group(1))}. {step.group(2).replace('-', ' ')}" if step else name
        src = e("shots/" + urllib.parse.quote(name))
        figures.append(f'<figure><a href="{src}"><img loading="lazy" src="{src}" alt="{e(caption)}"></a>'
                       f"<figcaption>{e(caption)}</figcaption></figure>")
    return head + f'<div class="shots">{"".join(figures)}</div></section>'


def render_yours() -> str:
    blank = '<p class="blank"><span>{}</span><span class="rule"></span></p>'
    return ('<section><h2>Two numbers only you know</h2>'
            + blank.format("Messages I typed during the run")
            + blank.format("Minutes I spent on this page") + "</section>")


def render(data: dict) -> str:
    """The whole page, as one HTML document with its CSS inside."""
    built = data["built"]
    footer = (f'Built by handover.py {e(when(built.get("at")))} from the folder at commit <code>{e(built.get("commit", "unknown"))}</code>.'
              if built else "Built by handover.py.")
    body = "".join([
        render_header(data), render_recording(data), render_summary(data), render_facts(data),
        render_finders(data), render_findings(data), render_shots(data), render_yours(),
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
    """Run the acceptance walk with recording on; leave recording.webm, shots/, recording.json and walk-output.txt in `out`."""
    scratch, shots = out / "recording-tmp", out / "shots"
    for folder in (scratch, shots):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
    (out / "recording.webm").unlink(missing_ok=True)
    record = {"walk": WALK, **tree_state(root)}
    started = time.time()
    run = subprocess.run(
        [str(root / ".venv" / "bin" / "python"), "-m", "pytest", WALK, "-q", "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True, timeout=900,
        env={**os.environ, "WALK_RECORD": str(scratch), "WALK_FEATURE": feature})
    record.update(result="passed" if run.returncode == 0 else "failed", minutes=round((time.time() - started) / 60, 1))
    (out / "walk-output.txt").write_text(run.stdout + run.stderr, encoding="utf-8")
    videos = sorted(scratch.glob("*.webm"))
    if videos:
        videos[0].replace(out / "recording.webm")
    shutil.rmtree(scratch, ignore_errors=True)
    # The walk's screenshots are named after it (walks/helper.py shot_name); take this run's only.
    prefix = re.sub(r"[^A-Za-z0-9]+", "-", WALK.split("::", 1)[-1]).strip("-")
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
    parser.add_argument("--tip", default="HEAD", help="the build's last commit (default HEAD)")
    parser.add_argument("--branch", default=None, help="the branch whose checks runs are counted (default the current branch)")
    parser.add_argument("--no-walk", action="store_true", help="do not run and record the walk; keep any earlier recording")
    args = parser.parse_args(argv)
    feature_dir = root / ".scratch" / args.feature
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.feature) or not feature_dir.is_dir():
        raise SystemExit(f"handover: no feature folder {feature_dir}")
    out = feature_dir / "hand-over"
    out.mkdir(exist_ok=True)
    facts = git_facts(root, args.base, args.tip)  # before the walk: a bad range stops the run at once
    if not args.no_walk:
        print(f"Recording the acceptance walk (about two minutes): {WALK}", flush=True)
        record_walk(root, args.feature, out)
    branch = args.branch or git(root, "rev-parse", "--abbrev-ref", "HEAD")
    data = page_data(
        args.feature, base_ref=args.base, tip_ref=args.tip, git=facts,
        runs=run_facts(read_runs(root / ".checks" / "runs.jsonl"), branch),
        findings=read_findings(feature_dir), fates=read_fates(feature_dir),
        finding_files=len(list((feature_dir / "findings").glob("*.jsonl"))),
        summary=read_summary(feature_dir), recording=read_recording(out),
        shots=sorted(path.name for path in (out / "shots").glob("*.png")), built=tree_state(root),
    )
    page = out / "index.html"
    page.write_text(render(data), encoding="utf-8")
    print(page)
    print(f"open {shlex.quote(str(page))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
