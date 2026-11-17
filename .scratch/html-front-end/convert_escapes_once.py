"""One-off: turn the old escapes ledger into findings and fates for the html-front-end hand-over page.

    python3 .scratch/html-front-end/convert_escapes_once.py      (from the repo root; run 2026-11-16)

Reads docs/agents/local/escapes.jsonl (rows E-001 to E-037: features html-front-end and
pr-1-review, the latter being the same build's fix round) and the nine follow-ups in the Further
Notes of this folder's spec.md, and writes, in this folder, findings/1-walker.jsonl,
findings/2-review.jsonl, findings/3-walker-recheck.jsonl and fates.jsonl in the formats
handover.py reads. handover.py itself reads neither the ledger nor the spec.

The words are for the owner, who reads them on the page (.claude/rules/human-facing-writing.md): a finding leads
with what a user saw, a fate's `why` leads with the reason, and where each is recorded comes last.

Nothing is made up:
- `what` is the ledger's `defect` text up to its citations: the sentence about what a user saw. `where` holds the
  rest of that text (the explore or findings file it cites, the walk it names), so every word of it is on the page.
- `finder` is `found_by` (exploration is a walker, branch-review is the review); `pass` is
  "recheck" for the pr-1-review exploration rows (found after the fixes), else "first".
- `area` is the explore or findings file the defect text cites after "explore:" or "findings:".
- `severity` is empty for every row: the ledger has a class (escape, blocking), not what a user
  would lose, so the page says that no severity is recorded.
- `check` is the walk the defect text names after "walk:", found by name in walks/; else empty.
- A fate is "fixed" where the ledger's `fixed_in` names a ticket. For the seventeen review rows
  the ledger names no fix; RANKED below is copied by hand from the Blocking table of
  .scratch/pr-1-review/ranked.md, which gives each finding (by its source citation) a fix
  ticket. Each such ticket's file says Status: done. A row with neither would get no fate line.
- `commit` is the merge commit of that ticket, found in git by its subject.
- For six of the seventeen, .scratch/pr-1-review/findings/round-1.md names the test or walk
  that showed the fix: five in its table "Did each blocking fix land" (two of them by line) and
  one, E-024's, in its finding 2. CONFIRMED below is copied from it by hand and becomes the
  fate's `check`. The other eleven keep an empty
  check: the table names code lines for them, or mentions a test without naming it. Their `why`
  quotes the table's own word under "Landed" (LANDED, copied by hand).
- The nine follow-ups are read from spec.md's bullets as walker first-pass findings with ids
  walker-<area>-<number> from the bullet's own bracket; the bracket's citation goes to `where` and
  the rest of the sentence is `what`, whole. Their fate is "left" with the spec's reason, said in
  plain words and then quoted (LEFT_WHY), except the CSV formula item (summary 6): the fix round's Open list
  took it as item 6 and fix ticket 08's ticked box names the test, so its fate is "fixed".
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
BASE, REVIEW_TIP, TIP = "ec9c681^1", "e77cb9c", "ec9c681^2"  # the build; the tip the review read; the merged tip

# Ledger id -> (row of ranked.md's Blocking table, its sources as written there, pr-1-review ticket).
RANKED = {
    "E-012": (4, "walk B1", "01"),
    "E-013": (3, "srv 1", "08"),
    "E-014": (5, "cli 1; seams 1", "02"),
    "E-015": (13, "cli 2", "03"),
    "E-016": (14, "cli 5", "03"),
    "E-017": (11, "cli 3; cli 4", "04"),
    "E-018": (9, "seams 2", "04"),
    "E-019": (1, "disc S1", "05"),
    "E-020": (10, "disc S3", "05"),
    "E-021": (2, "seams 3", "06"),
    "E-022": (12, "seams 4; srv 4", "06"),
    "E-023": (7, "disc S2; srv 8", "07"),
    "E-024": (8, "srv 7", "07"),
    "E-025": (6, "disc S4", "08"),
    "E-026": (17, "cli 10; walk N3", "09"),
    "E-027": (15, "walk S1", "10"),
    "E-028": (16, "walk S2", "10"),
}

ROUND_1 = '.scratch/pr-1-review/findings/round-1.md (table "Did each blocking fix land"'
ACCEPTANCE = "walks/test_acceptance_walk.py::test_walk_the_acceptance_journey_"

# Ledger id -> (the fix spec's number for it, the test or walk round-1.md names for the fix, what else the records say).
CONFIRMED = {
    "E-014": ("F3", "walks/test_summary_walk.py::test_walk_a_finished_check_keeps_summary_period_and_typed_dates", ""),
    "E-019": ("F8", "walks/test_origin_walk.py", ""),
    "E-021": ("F10", "walks/test_saved_search_walk.py", ""),
    "E-024": ("F13", "tests/test_api_checks.py::test_a_trial_removed_while_a_check_runs_is_not_fetched_marked_checked_or_given_changes",
              " The second read names that test in its finding 2, and points to it by line in its finding 4, not in row F13 of its table. It also says the fix landed with a gap and a miscount (its findings 1 and 2), "
              "which that test does not cover. A later fix (fix ticket 18, merge a7a2d4e) closed the miscount, and closed the gap for a fetch that succeeds, with the tests "
              "test_a_finished_check_counts_only_the_trials_it_still_held_after_one_was_removed and "
              "test_a_trial_removed_during_its_own_fetch_is_not_marked_checked_or_given_changes. "
              "The re-check of that fix found the gap still open when the removed trial's own fetch fails (.scratch/pr-1-review/findings/round-1-check.md, sweep 1); "
              "the fix round recommended deferring that case, as item 22 of its list of open choices (.scratch/pr-1-review/spec.md)."),
    "E-027": ("F16", ACCEPTANCE + "measures_horizontal_scroll_on_every_keyboard_move_and_fails_on_a_wide_new_watchlist_dialog",
              " The second read names the test by its line, not its name (line 441 of walks/test_acceptance_walk.py at commit 73b36b5); the test named here is the one that starts on that line."),
    "E-028": ("F17", ACCEPTANCE + "checks_every_tab_stop_it_passes_and_fails_when_a_control_passed_on_the_way_loses_its_name",
              " The second read names the test by its line, not its name (line 456 of walks/test_acceptance_walk.py at commit 73b36b5); the test named here is the one that starts on that line."),
}

# Ledger id -> (row of round-1.md's table for a fix with no test named here, the table's own word under "Landed"). Copied by hand.
LANDED = {
    "E-012": ("F1", "yes"), "E-013": ("F2", "yes"), "E-015": ("F4", "yes, for the four named"), "E-016": ("F5", "yes"),
    "E-017": ("F6", "yes"), "E-018": ("F7", "yes"), "E-020": ("F9", "yes"), "E-022": ("F11", "yes"), "E-023": ("F12", "yes"),
    "E-025": ("F14", "yes"), "E-026": ("F15", "yes"),
}
assert not set(LANDED) & set(CONFIRMED) and set(LANDED) | set(CONFIRMED) == set(RANKED)

# Ledger id -> a later commit on the same fix, named in the fate's why.
LATER = {"E-012": " A follow-up to that ticket was merged afterwards (db1b506, Merge ticket 01 follow-up)."}

FOLLOW_UPS = "- **Follow-up from the exploration round (ticket 16), found and not fixed here** ("
LEFT_WHY = ("The build judged that this issue breaks none of its requirements, so it left the issue for a follow-up build. The build's rule "
            "was to fix an issue the exploratory testers found only when the issue broke a ticket's requirement, a part of the design the "
            "build covers, or one of the browser tests' automatic failures (a console error, a failed request, sideways scrolling). The later "
            "fix round did not change that decision. The build's own words for it are \"none breaks an acceptance box, an In or Partly-in "
            "row, or a walk guard\" (.scratch/html-front-end/spec.md, Further Notes; the rule is its End State 5). The fix round's decision "
            'is in .scratch/pr-1-review/ranked.md ("Decided earlier, not re-classed").')
CSV_FIXED = ("summary 6", "08", "tests/test_api_summary.py::test_a_title_that_looks_like_a_formula_is_prefixed_in_the_csv_only",
             "The first build left this issue unfixed, as needing a decision. The fix round then took it on (item 6 of its open list, "
             "recommended: do), and fix ticket 08's ticked requirement names this test; the commit is that ticket's merge. Recorded in "
             ".scratch/html-front-end/spec.md (Further Notes) and .scratch/pr-1-review/spec.md (Open list).")
LEDGER = "docs/agents/local/escapes.jsonl"
CITED = re.compile(r"; (?=(?:walk|explore findings|explore|findings|pr-1-review findings): )")  # where the defect text turns to its citations


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def merge_of(ticket: str, fix_round: bool) -> str:
    """The short sha of 'Merge ticket NN: ...', in the fix round's commits or the first build's."""
    span = f"{REVIEW_TIP}..{TIP}" if fix_round else f"{BASE}..{REVIEW_TIP}"
    found = git("log", "--format=%h", f"--grep=^Merge ticket {ticket}: ", span).split()
    assert len(found) == 1, (ticket, fix_round, found)
    return found[0]


def areas(defect: str) -> str:
    """The files cited after the last 'explore:' / 'findings:' of the defect text, e.g. 'find-trials, dialogs'."""
    cited = re.split(r"(?:explore findings|explore|findings):", defect)
    if len(cited) < 2:
        return "not recorded"
    names = re.findall(r"([a-z]+(?:-[a-z]+)*) [A-Z]?\d", cited[-1].split(";")[0])
    return ", ".join(dict.fromkeys(name for name in names if name != "and")) or "not recorded"


def walk_named(defect: str) -> str:
    """'walks/<file>.py::<test>' for the walk the defect text names after 'walk:', or '' when it names none."""
    named = re.search(r"walk: (test_\w+)", defect)
    if not named:
        return ""
    files = git("grep", "-l", f"def {named.group(1)}(", "--", "walks", "tests").split()
    assert len(files) == 1, (named.group(1), files)
    return f"{files[0]}::{named.group(1)}"


def said(text: str) -> str:
    """A sentence about what a user saw, ending as a sentence."""
    return text if text.endswith((".", "?", "!")) else text + "."


def follow_ups(spec: str) -> tuple[list[dict], list[dict]]:
    """The bullets under spec.md's follow-up line, as walker first-pass findings and their fates."""
    lines = spec.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(FOLLOW_UPS)) + 1
    found, fates = [], []
    for line in lines[start:]:
        if not line.startswith("  - "):
            break
        cited = re.search(r"\(([a-z]+(?: [a-z]+)*) (\d+)[;)]", line)  # "(saved search 3)", "(trial page 6; also seen in ...)"
        area, name = cited.group(1).replace(" ", "-"), f"{cited.group(1)} {cited.group(2)}"
        what = line[4:].replace(f" ({name})", "").replace(f"({name}; ", "(")  # the bracket's citation goes to `where`; "also seen in ..." stays
        assert name not in what, line
        found.append({"id": f"walker-{area}-{cited.group(2)}", "finder": "walker", "pass": "first", "area": area,
                      "severity": "", "what": what, "where": f"Cited as {name} in .scratch/html-front-end/spec.md, Further Notes.",
                      "check": ""})
        if name == CSV_FIXED[0]:
            fates.append({"id": found[-1]["id"], "fate": "fixed", "commit": merge_of(CSV_FIXED[1], True), "check": CSV_FIXED[2], "why": CSV_FIXED[3]})
        else:
            fates.append({"id": found[-1]["id"], "fate": "left", "commit": "", "check": "", "why": LEFT_WHY})
    assert len(found) == 9, len(found)
    return found, fates


def convert(rows: list[dict], spec: str) -> tuple[dict[str, list[dict]], list[dict]]:
    files: dict[str, list[dict]] = {"1-walker": [], "2-review": [], "3-walker-recheck": []}  # file-name order is page order
    fates = []
    for row in rows:
        walker = {"exploration": True, "branch-review": False}[row["found_by"]]
        recheck = row["feature"] == "pr-1-review"
        check = walk_named(row["defect"])
        files["3-walker-recheck" if recheck else "1-walker" if walker else "2-review"].append({
            "id": row["id"], "finder": "walker" if walker else "review", "pass": "recheck" if recheck else "first",
            "area": areas(row["defect"]), "severity": "", "what": said(CITED.split(row["defect"], maxsplit=1)[0]),
            "where": f"Row {row['id']} of the old defect log ({LEDGER}), which goes on: {CITED.split(row['defect'], maxsplit=1)[1]}", "check": check,
        })
        ticket = re.match(r"ticket (\d+)", row["fixed_in"])
        if ticket:
            whose = "the fix round (.scratch/pr-1-review/issues/)" if recheck else "the first build (.scratch/html-front-end/issues/)"
            fates.append({"id": row["id"], "fate": "fixed", "commit": merge_of(ticket.group(1), recheck), "check": check,
                          "why": (f"The old defect log records the fix in these words: \"{row['fixed_in']}\". That is ticket {ticket.group(1)} of {whose}; "
                                  f"the commit is that ticket's merge. Recorded in {LEDGER}, field fixed_in.")})
        elif row["id"] in RANKED:
            number, sources, fix = RANKED[row["id"]]
            spec_number, named, more = CONFIRMED.get(row["id"], ("", "", ""))
            landed = LANDED.get(row["id"])
            fates.append({"id": row["id"], "fate": "fixed", "commit": merge_of(fix, True), "check": named,
                          "why": (f"The code review ranked this issue as blocking. That ranking is in the review's own list, not in the report this page read, "
                                  f"which is why the page shows no severity for the issue. The review gave it to fix ticket {fix} of the fix round, which is marked done; "
                                  "the commit is that ticket's merge. The old defect log itself names no fix."
                                  + (f" The review's second read names a test for the fix.{more}" if named else
                                     f" The review's second read records whether the fix landed as \"{landed[1]}\". It names no test for the fix: it cites "
                                     "lines of code, or mentions a test without naming it.")
                                  + LATER.get(row["id"], "")
                                  + f" Recorded in .scratch/pr-1-review/ranked.md (Blocking table, row {number}: {sources})"
                                  + f" and {ROUND_1}, row {spec_number or landed[0]}).")})
    left, left_fates = follow_ups(spec)
    files["1-walker"] += left
    fates += left_fates
    ids = [f["id"] for group in files.values() for f in group]
    assert len(ids) == len(set(ids)) and sorted(ids) == sorted(f["id"] for f in fates), "ids must be distinct, one fate each"
    return files, fates


def main() -> None:
    ledger = ROOT / "docs" / "agents" / "local" / "escapes.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["feature"] in ("html-front-end", "pr-1-review")]
    files, fates = convert(rows, (HERE / "spec.md").read_text(encoding="utf-8"))
    (HERE / "findings").mkdir(exist_ok=True)
    for name, found in files.items():
        (HERE / "findings" / f"{name}.jsonl").write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in found), encoding="utf-8")
        print(f"findings/{name}.jsonl: {len(found)}")
    (HERE / "fates.jsonl").write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in fates), encoding="utf-8")
    print(f"fates.jsonl: {len(fates)} of {sum(len(found) for found in files.values())} findings")
    for found in (f for group in files.values() for f in group):
        fate = next((f for f in fates if f["id"] == found["id"]), {})
        print(found["id"], "|", found["area"], "|", fate.get("commit", "NO FATE"), "|", fate.get("check", ""))


if __name__ == "__main__":
    main()
