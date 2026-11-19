"""handover.py: the one page a build ends with.

These test the parts that read and compute, what the page draws for each state of the
records, and that the page escapes what it is given. Git facts come from a small real
repository made in a temporary folder; the walk is run through a stand-in for
.venv/bin/python. Lacks: the real browser run (`handover.py` is run for real for that),
and so the page's script, which only steps through pictures the page already shows.
"""

from __future__ import annotations

import html
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

import handover


def finding(id, finder="walker", round="first", **more):
    return {"id": id, "finder": finder, "pass": round, "area": "find-trials", "severity": "wrong",
            "what": f"what {id} looks like", "where": "Find trials", "check": "", **more}


def fate(id, fate="fixed", check="walks/test_x.py::test_y", **more):
    return {"id": id, "fate": fate, "commit": "abc1234", "check": check, "why": "", **more}


def write_lines(path: pathlib.Path, rows) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def page(findings=(), **more) -> str:
    """The page for these findings, as if read from one walker's file (no findings: no file)."""
    files = more.pop("files", {"walker-find-trials.jsonl": list(findings)} if findings else None)
    return handover.render(handover.page_data("feat", files=files, **more))


def row(text: str, label: str) -> str:
    """The value drawn for one fact, without its source line."""
    return re.search(rf"<dt>{re.escape(label)}</dt><dd>(.*?)<small>", text, re.S).group(1)


def top(text: str) -> str:
    """What the page says before its first section: the title and the board under it."""
    return text[:text.index('<section id="recording">')]


def tile(text: str, href: str) -> tuple[str, str]:
    """(colour, words) of the board's verdict tile that links to `href`."""
    return re.search(rf'<a class="tile (\w*)" href="{href}">.*?<strong>(.*?)</strong>', top(text), re.S).groups()


def chip(text: str, look: str, href: str, words: str) -> bool:
    """Whether the board has this label, with this look, linking to `href`."""
    return bool(re.search(rf'<a class="pill {look}" href="{href}">(?:<i class="sw [\w-]+"></i>)?{re.escape(words)}</a>', top(text)))


LOOK = re.compile(r'<li class="(\w+)"><span class="mark"[^>]*>[^<]*</span><div><a href="([^"]*)"><strong>(.*?)</strong></a>'
                  r'<span class="sub">(.*?)</span>(?:<details><summary>Why this matters</summary><p>(.*?)</p></details>)?</div></li>')


def looks(text: str) -> list[tuple[str, str, str, str, str]]:
    """(colour, link, what, the line in view, the words folded under it) of each thing the list tells the owner to look at."""
    listed = re.search(r'<ol class="look">(.*?)</ol>', top(text), re.S)
    return LOOK.findall(listed.group(1)) if listed else []


def things(text: str) -> list[tuple[str, str, str, str]]:
    """(colour, link, what, why) of each thing the list under the headline tells the owner to look at, in order: `why` is
    everything the item says, the folded reason first and then the line in view, as one text."""
    return [(tone, href, what, f"{folded} {shown}".strip()) for tone, href, what, shown, folded in looks(text)]


def reviewer(name: str) -> str:
    """The head cell of one review's row in the table of who reviewed the build: its name, then what it does."""
    return f"<th>{handover.FINDERS[name]}<small>{handover.e(handover.FINDER_NOTES[name])}</small></th>"


def cards(text: str) -> list[str]:
    """Each issue as the page draws it, its folded record included."""
    return [card.split("</li>")[0] for card in text.split('<li class="finding">')[1:]]


def record(text: str, id: str) -> dict[str, str]:
    """The folded record of one issue: {label: value as drawn}."""
    folded = re.search(rf"<summary>Record <code>{re.escape(id)}</code></summary><dl>(.*?)</dl>", text, re.S).group(1)
    return dict(re.findall(r"<div><dt>(.*?)</dt><dd>(.*?)</dd></div>", folded))


def drawn_green(text: str) -> list[str]:
    """Everything the page draws as passed: a tile, a label, a check or the headline. (A square of the run history is
    drawn blue or red, never in the passed green: an old run is not a verdict.)"""
    return re.findall(r'class="[^"]*(?<![\w-])green(?![\w-])[^"]*"', text)



def test_a_finding_with_no_fate_line_is_grouped_first_under_no_fate_recorded():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C"), finding("D")],
        {"A": fate("A"), "C": fate("C", "left", check=""), "D": fate("D", "")},
    )
    groups = handover.group_by_state(joined)
    assert [state for state, _ in groups][0] == "no-fate"
    assert [f["id"] for f in groups[0][1]] == ["B", "D"]
    assert handover.STATES["no-fate"][0] == "No outcome recorded"
    what, so_what = handover.state_said("no-fate", groups[0][1])
    assert what == "The build's record gives no outcome for 2 issues" and "treat each one as open" in so_what


def test_a_fixed_fate_that_names_no_check_is_marked_fixed_no_check_named():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C")],
        {"A": fate("A"), "B": fate("B", check=""), "C": fate("C", check="   ")},
    )
    assert {f["id"]: f["state"] for f in joined} == {"A": "fixed", "B": "fixed-no-check", "C": "fixed-no-check"}
    assert handover.STATES["fixed-no-check"][0] == "Marked fixed, no test named"


def test_a_fixed_fate_whose_check_or_commit_was_not_found_is_not_fixed():
    joined = handover.join([finding("A"), finding("B")], {"A": fate("A"), "B": fate("B")}, {"B": "commit abc1234 is not in the repository"})
    assert {f["id"]: f["state"] for f in joined} == {"A": "fixed", "B": "fixed-not-found"}
    text = page([finding("A"), finding("B")], fates={"A": fate("A"), "B": fate("B")}, missing={"B": "commit abc1234 is not in the repository"})
    assert "Missing: commit abc1234 is not in the repository." in text
    assert 'class="group warn" open' in group_tag(text, "what B looks like")
    assert "This page found the test&#x27;s file" in text and "It did not run the test." in text
    both = page([finding("A"), finding("B")], fates={"A": fate("A"), "B": fate("B")}, missing={})
    assert "This page found each test&#x27;s file" in both and "It did not run the tests." in both
    assert "This page found the test" not in page([finding("A")], fates={"A": fate("A")})


def test_the_groups_are_in_order_with_a_fate_the_format_does_not_name_straight_after_no_fate():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C"), finding("D"), finding("E"), finding("F")],
        {"A": fate("A"), "B": fate("B", "not-a-defect"), "C": fate("C", "left"), "D": fate("D", check=""), "F": fate("F", "Fixed")},
    )
    assert [(state, [f["id"] for f in rows]) for state, rows in handover.group_by_state(joined)] == [
        ("no-fate", ["E"]), ("fate: Fixed", ["F"]), ("left", ["C"]), ("fixed-no-check", ["D"]), ("fixed", ["A"]),
        ("not-a-defect", ["B"])]


def test_a_fate_whose_id_matches_no_finding_is_reported_not_dropped():
    assert handover.orphan_fates([finding("A")], {"A": fate("A"), "Z": fate("Z")}) == [fate("Z")]



def test_findings_are_counted_by_finder_with_first_pass_and_recheck_apart():
    rows = [finding("1"), finding("2"), finding("3", round="recheck"),
            finding("4", "review")]
    counts = handover.count_by_finder(rows)
    assert counts["walker"] == {"first": 2, "recheck": 1, "other": 0}
    assert counts["review"] == {"first": 1, "recheck": 0, "other": 0}
    assert counts["early-read"] == {"first": 0, "recheck": 0, "other": 0}
    assert list(counts)[:3] == ["walker", "review", "early-read"]


def test_a_finder_the_contract_does_not_name_is_still_counted():
    counts = handover.count_by_finder([finding("1", "a-stranger")])
    assert counts["a-stranger"] == {"first": 1, "recheck": 0, "other": 0}


def test_a_pass_the_format_does_not_name_is_counted_in_a_column_drawn_only_then():
    rows = [finding("1"), finding("2", round="re-check"), finding("3", round=None), finding("4", round="second")]
    del rows[3]["pass"]
    assert handover.count_by_finder(rows)["walker"] == {"first": 1, "recheck": 0, "other": 3}
    text = page(rows)
    assert "Round not recognised" in text
    walker = re.search(rf"<tr>{re.escape(reviewer('walker'))}(.*?)</tr>", text).group(1)
    assert sum(int(n) for n in re.findall(r">(\d+)<", walker)) == 4
    assert "Round not recognised" not in page([finding("1"), finding("2", round="recheck")])



def test_findings_are_read_from_every_jsonl_file_in_the_folder_and_fates_by_id(tmp_path):
    feature = tmp_path / ".scratch" / "feat"
    write_lines(feature / "findings" / "walker.jsonl", [finding("W-1"), finding("W-2")])
    write_lines(feature / "findings" / "review.jsonl", [finding("R-1", "review")])
    write_lines(feature / "findings" / "early-read-whole.jsonl", [])
    files = handover.read_findings(feature)
    assert {name: [f["id"] for f in rows] for name, rows in files.items()} == {
        "early-read-whole.jsonl": [], "review.jsonl": ["R-1"], "walker.jsonl": ["W-1", "W-2"]}
    write_lines(feature / "fates.jsonl", [fate("W-1", "left"), fate("W-1")])
    fates = handover.read_fates(feature)
    assert list(fates) == ["W-1"] and fates["W-1"]["fate"] == "fixed"


def test_two_findings_sharing_an_id_stop_the_run_name_both_files_and_say_what_to_do(tmp_path):
    write_lines(tmp_path / "findings" / "walker-a.jsonl", [finding("walker-a-01")])
    write_lines(tmp_path / "findings" / "walker-a-recheck.jsonl", [finding("walker-a-01", round="recheck")])
    with pytest.raises(SystemExit) as stopped:
        handover.read_findings(tmp_path)
    assert "walker-a-01" in str(stopped.value)
    assert "walker-a.jsonl" in str(stopped.value) and "walker-a-recheck.jsonl" in str(stopped.value)
    assert "a new id" in str(stopped.value) and "fates.jsonl" in str(stopped.value)


def test_missing_record_files_read_as_nothing_and_a_broken_line_names_its_file_and_line(tmp_path):
    feature = tmp_path / ".scratch" / "feat"
    assert handover.read_findings(feature) == {}
    assert handover.read_fates(feature) == {}
    assert handover.read_summary(feature) is None
    bad = feature / "fates.jsonl"
    bad.parent.mkdir(parents=True)
    bad.write_text('{"id": "A", "fate": "fixed"}\n\nnot json\n', encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        handover.read_fates(feature)
    assert "fates.jsonl" in str(stopped.value) and "line 3" in str(stopped.value)


@pytest.mark.parametrize("wrong", [["a list"], {"what": "one sentence, not a list"}, {"what": ["fine"], "now_what": [{"not": "a sentence"}]}])
def test_a_hand_over_json_of_the_wrong_shape_stops_the_run_and_names_the_file(tmp_path, wrong):
    (tmp_path / "hand-over.json").write_text(json.dumps(wrong), encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        handover.read_summary(tmp_path)
    assert "hand-over.json" in str(stopped.value) and "\n" not in str(stopped.value)
    (tmp_path / "hand-over.json").write_text(json.dumps({"what": ["Built."]}), encoding="utf-8")
    assert handover.read_summary(tmp_path) == {"what": ["Built."]}


def test_a_summary_too_long_to_read_at_a_glance_stops_the_run_and_says_what_to_cut(tmp_path):
    longest, most = "x" * handover.LINE_LENGTH, ["One thing."] * handover.SUMMARY_LINES
    fits = {"what": most, "so_what": [longest], "now_what": most + most}
    (tmp_path / "hand-over.json").write_text(json.dumps(fits), encoding="utf-8")
    assert handover.read_summary(tmp_path) == fits
    for wrong, said in (({"what": most + ["One more."]}, "what has 6 lines"), ({"so_what": most + ["One more."]}, "so_what has 6 lines"),
                        ({"now_what": ["Short.", longest + "x"]}, f"now_what line 2 is {handover.LINE_LENGTH + 1} characters")):
        (tmp_path / "hand-over.json").write_text(json.dumps(wrong), encoding="utf-8")
        with pytest.raises(SystemExit) as stopped:
            handover.read_summary(tmp_path)
        assert said in str(stopped.value) and "hand-over.json" in str(stopped.value) and "\n" not in str(stopped.value)



def run(branch, result, at="2026-11-16T10:00:00Z", names=tuple(handover.CHECK_NAMES), **more):
    return {"at": at, "branch": branch, "tip": "abc1234", "dirty": False, "result": result, "minutes": 2.5,
            "checks": [{"name": name, "result": result, "minutes": 0.5, "output": f".checks/{name}.txt"} for name in names], **more}


GIT = {"base": "0000000", "tip": "abc1234", "commits": 1, "first": None, "last": None, "minutes": None, "files": 1,
       "added": 1, "added_by": {}, "removed": 0, "tests_added": 0, "tests_removed": 0}


def test_red_runs_are_counted_for_this_branch_only_and_the_last_run_is_this_branch_s(tmp_path):
    log = write_lines(tmp_path / ".checks" / "runs.jsonl", [
        run("feature/x", "red", "2026-11-16T10:00:00Z"),
        run("feature/other", "red", "2026-11-16T10:05:00Z"),
        run("feature/x", "red", "2026-11-16T10:10:00Z"),
        run("feature/x", "green", "2026-11-16T10:20:00Z"),
        run("feature/other", "red", "2026-11-16T10:30:00Z"),
    ])
    facts = handover.run_facts(handover.read_runs(log), "feature/x")
    assert facts["red"] == 2
    assert facts["runs"] == 3
    assert facts["full"]["at"] == "2026-11-16T10:20:00Z" and facts["full"]["result"] == "green"
    assert facts["since"] == {} and facts["why_unknown"] == ""
    assert [(r["result"], r["full"]) for r in facts["history"]] == [("red", True), ("red", True), ("green", True)]


def test_an_absent_run_log_is_unknown_never_zero(tmp_path):
    runs = handover.read_runs(tmp_path / ".checks" / "runs.jsonl")
    assert runs is None
    facts = handover.run_facts(runs, "feature/x")
    assert facts["red"] is None and facts["runs"] is None and facts["full"] is None
    assert "does not exist" in facts["why_unknown"]


def test_a_run_log_with_no_line_for_this_branch_is_unknown_never_zero(tmp_path):
    log = write_lines(tmp_path / "runs.jsonl", [run("feature/other", "red")])
    facts = handover.run_facts(handover.read_runs(log), "feature/x")
    assert facts["red"] is None and facts["full"] is None
    assert "feature/x" in facts["why_unknown"]


def test_what_is_unknown_is_drawn_as_unknown_never_as_a_number_or_a_pill():
    text = page(runs=handover.run_facts(None, "feature/x"))
    for label in ("Last full run of the checks", "Failed runs of the checks", "Commits", "Files changed", "Lines added", "Tests",
                  "Issues reported", "Issues with no outcome recorded"):
        assert re.fullmatch(r'<span class="unknown">[a-z ]+</span>', row(text, label)), label
    assert "does not exist" in text
    assert not drawn_green(text) and tile(text, "#facts") == ("amber", "No result on record")
    one_empty_file = page(files={"walker-find-trials.jsonl": []})
    assert row(one_empty_file, "Issues reported") == "0" and row(one_empty_file, "Issues with no outcome recorded") == "0"


def test_a_run_of_one_named_check_is_never_the_last_checks_run_and_never_turns_the_pill_green():
    runs = handover.run_facts([run("feature/x", "red", "2026-11-16T10:00:00Z"),
                               run("feature/x", "green", "2026-11-16T10:20:00Z", names=("unit",))], "feature/x")
    assert runs["full"]["result"] == "red" and runs["since"] == {"unit": {"result": "green", "at": "2026-11-16T10:20:00Z"}}
    text = page(runs=runs, git=GIT)
    last = row(text, "Last full run of the checks")
    assert 'pill red">failed<' in last and not drawn_green(text)
    assert ("After the last run of every check, some checks were run again: most recently, the unit tests (unit) passed (16 Nov 2026, 10:20 UTC). "
            "The check of the code for common mistakes (lint), the scan for forbidden code patterns (patterns), the check of the defect log (escapes) and the browser tests (walks) were not run again.") in last
    assert tile(text, "#facts") == ("red", "Failed")
    assert re.findall(r'<span class="(r-\w+)( part)?" title', text) == [("r-red", ""), ("r-green", " part")]
    assert "1 of 2 runs" in row(text, "Failed runs of the checks") and "a run of one named check too" in text


def test_with_no_run_of_every_check_the_last_checks_run_is_unknown_and_says_why():
    old_line = run("feature/x", "green", names=("patterns", "escapes"), all=True)
    runs = handover.run_facts([old_line], "feature/x")
    assert runs["full"] is None and set(runs["since"]) == {"patterns", "escapes"}
    text = page(runs=runs, git=GIT)
    assert row(text, "Last full run of the checks").startswith('<span class="unknown">unknown</span>')
    assert ("The log holds runs of only some checks: most recently, the scan for forbidden code patterns (patterns) passed (16 Nov 2026, 10:00 UTC) "
            "and the check of the defect log (escapes) passed (16 Nov 2026, 10:00 UTC).") in text
    assert "The check of the code for common mistakes (lint), the unit tests (unit) and the browser tests (walks) were not run in them." in text
    assert "none of them is a full run, one of every check (lint, patterns, escapes, unit, walks)" in text
    assert not drawn_green(text) and tile(text, "#facts") == ("amber", "No result on record")


def test_a_quick_run_after_a_full_one_never_replaces_it_as_the_last_full_run():
    full = run("feature/x", "green", "2026-11-16T10:00:00Z", quick=False)
    quick = run("feature/x", "green", "2026-11-16T10:20:00Z", quick=True)
    runs = handover.run_facts([full, quick], "feature/x")
    assert runs["full"]["at"] == "2026-11-16T10:00:00Z" and runs["runs"] == 2
    assert [(r["result"], r["full"]) for r in runs["history"]] == [("green", True), ("green", False)]
    text = page(runs=runs, git=GIT)
    assert "16 Nov 2026, 10:00 UTC" in row(text, "Last full run of the checks") and tile(text, "#facts") == ("green", "Passed on the build&#x27;s last commit")
    assert re.findall(r'<span class="(r-\w+)( part)?" title', text) == [("r-green", ""), ("r-green", " part")]
    assert "16 Nov 2026, 10:20 UTC: passed, a quick run, with the browser tests at one window size" in text


def test_a_red_quick_run_after_a_green_full_run_shows_as_a_later_failure():
    walked = {"git": GIT, "recording": {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0},
              "files": {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}}
    runs = handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z"),
                               run("feature/x", "red", "2026-11-16T10:20:00Z", quick=True)], "feature/x")
    assert runs["full"]["at"] == "2026-11-16T10:00:00Z" and handover.since_result(runs) == "red"
    text = page(runs=runs, **walked)
    assert tile(text, "#facts") == ("red", "Passed, then a later partial run failed") and '<p class="headline red">' in top(text)
    assert "After the last run of every check, some checks were run again: most recently, the check of the code for common mistakes (lint) failed" in top(text)


def test_a_branch_with_only_quick_runs_has_no_full_run_and_the_page_says_so():
    runs = handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z", quick=True),
                               run("feature/x", "green", "2026-11-16T10:20:00Z", quick=True)], "feature/x")
    assert runs["full"] is None and [r["full"] for r in runs["history"]] == [False, False]
    text = page(runs=runs, git=GIT)
    assert row(text, "Last full run of the checks").startswith('<span class="unknown">unknown</span>')
    assert "none of them is a full run, one of every check (lint, patterns, escapes, unit, walks)" in text
    assert not drawn_green(text) and tile(text, "#facts") == ("amber", "No result on record")
    red = page(runs=handover.run_facts([run("feature/x", "red", quick=True)], "feature/x"), git=GIT)
    assert tile(red, "#facts") == ("red", "Failed in their last run")


def test_a_run_line_with_no_quick_field_is_a_full_run():
    old = run("feature/x", "green", "2026-11-16T10:00:00Z")
    assert "quick" not in old
    runs = handover.run_facts([old, run("feature/x", "green", "2026-11-16T10:20:00Z", quick=True)], "feature/x")
    assert runs["full"] is old and [r["full"] for r in runs["history"]] == [True, False]
    assert "a quick run" not in re.findall(r'title="([^"]*)"></span>', page(runs=runs, git=GIT))[0]


def test_a_picked_run_after_a_full_one_never_replaces_it_as_the_last_full_run_and_is_counted_apart():
    full = run("feature/x", "green", "2026-11-16T10:00:00Z", quick=False, picked=False)
    picked = run("feature/x", "green", "2026-11-16T10:20:00Z", quick=False, picked=True,
                 base="the last green full run, at 1234567", picks=[{"check": "unit", "ran": 12, "of": 767, "why": "the tests that ran the changed Python"}])
    runs = handover.run_facts([full, picked], "feature/x")
    assert runs["full"]["at"] == "2026-11-16T10:00:00Z" and runs["runs"] == 2
    assert [(r["result"], r["full"]) for r in runs["history"]] == [("green", True), ("green", False)]
    text = page(runs=runs, git=GIT)
    assert "16 Nov 2026, 10:00 UTC" in row(text, "Last full run of the checks") and tile(text, "#facts") == ("green", "Passed on the build&#x27;s last commit")
    assert re.findall(r'<span class="(r-\w+)( part)?" title', text) == [("r-green", ""), ("r-green", " part")]
    assert "16 Nov 2026, 10:20 UTC: passed, a run of only the tests the change could reach" in text
    assert "1 of them ran only the tests the change could reach, so it is not a full run." in text
    assert "picked" not in text


def test_a_branch_with_only_picked_runs_after_the_last_change_has_no_full_run_and_the_page_says_so():
    runs = handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z", quick=True, picked=True),
                               run("feature/x", "green", "2026-11-16T10:20:00Z", picked=True)], "feature/x")
    assert runs["full"] is None and [r["full"] for r in runs["history"]] == [False, False]
    text = page(runs=runs, git=GIT)
    assert row(text, "Last full run of the checks").startswith('<span class="unknown">unknown</span>')
    assert "none of them is a full run, one of every check (lint, patterns, escapes, unit, walks)" in text
    assert not drawn_green(text) and tile(text, "#facts") == ("amber", "No result on record")
    assert "2 of them ran only the tests the change could reach, so none of those is a full run." in text
    assert ("16 Nov 2026, 10:00 UTC: passed, a quick run, with the browser tests at one window size, "
            "and a run of only the tests the change could reach") in text


def test_a_run_log_with_no_picked_field_gives_the_page_it_gave_before_picked_runs():
    old = [run("feature/x", "green", "2026-11-16T10:00:00Z"), run("feature/x", "green", "2026-11-16T10:20:00Z", quick=True)]
    assert all("picked" not in line for line in old)
    unpicked = [{**line, "picked": False} for line in old]
    text = page(runs=handover.run_facts(old, "feature/x"), git=GIT)
    assert text == page(runs=handover.run_facts(unpicked, "feature/x"), git=GIT)
    assert "the change could reach" not in text
    assert "1 of them" not in text


def test_a_green_run_is_drawn_green_only_on_the_build_s_last_commit_as_committed():
    green = lambda **more: page(runs=handover.run_facts([run("feature/x", "green", **more)], "feature/x"), git=GIT)  # noqa: E731 (a one-line helper local to this function)
    assert 'pill green">passed<' in row(green(), "Last full run of the checks") and tile(green(), "#facts") == ("green", "Passed on the build&#x27;s last commit")
    assert top(green()).count('<span class="chk green">') == 5
    for text, words in ((green(tip="fff9999"), "Not shown to pass on the build&#x27;s last commit"),
                        (green(dirty=True), "Not shown to pass as committed")):
        assert not drawn_green(text) and top(text).count('<span class="chk ">') == 5
        assert tile(text, "#facts") == ("amber", words)
        assert things(text)[1][2] == "The build&#x27;s last commit is not shown to pass the automated checks"
    assert "on commit fff9999, not the build&#x27;s last commit (abc1234)" in green(tip="fff9999")
    assert "with uncommitted changes in the folder" in green(dirty=True)
    assert things(green(dirty=True))[1][3].endswith("Ask for every check to be run on the build&#x27;s last commit, with nothing uncommitted in the folder.")


def test_a_later_run_of_one_check_that_was_not_green_is_on_the_board_not_only_in_the_folded_list():
    walked = {"git": GIT, "recording": {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0},
              "files": {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}}
    then = lambda result: handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z"),  # noqa: E731 (a one-line helper local to this function)
                                              run("feature/x", result, "2026-11-16T10:20:00Z", names=("unit",))], "feature/x")
    red = page(runs=then("red"), **walked)
    assert tile(red, "#facts") == ("red", "Passed, then a later partial run failed")
    assert things(red)[0][2] == "A later run of only some of the automated checks failed"
    assert '<p class="headline red">' in top(red) and "1 thing to look at" in top(red) and "Nothing on record" not in red
    assert "some checks were run again: most recently, the unit tests (unit) failed (16 Nov 2026, 10:20 UTC). The check of the code for common mistakes (lint), the scan for forbidden code patterns (patterns)," in top(red)
    assert '<span class="chk green">' not in red and top(red).count('<span class="chk ">') == 5
    odd = page(runs=then("stopped"), **walked)
    assert tile(odd, "#facts") == ("amber", "Passed, then a later partial run did not pass") and '<p class="headline amber">' in top(odd)
    green = page(runs=then("green"), **walked)
    assert tile(green, "#facts") == ("green", "Passed on the build&#x27;s last commit") and "run again" not in top(green) and '<p class="headline green">' in top(green)
    only_red = page(runs=handover.run_facts([run("feature/x", "red", names=("unit",))], "feature/x"), **walked)
    assert tile(only_red, "#facts") == ("red", "Failed in their last run") and "The log holds runs of only some checks: most recently, the unit tests (unit) failed" in top(only_red)
    assert things(only_red)[0][2] == "The automated checks failed in their last run"


def test_a_check_that_failed_when_run_again_stays_failed_until_that_same_check_passes():
    walked = {"git": GIT, "recording": {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0},
              "files": {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}}
    start = [run("feature/x", "green", "2026-11-16T10:00:00Z"), run("feature/x", "red", "2026-11-16T10:20:00Z", names=("unit",))]
    hidden = handover.run_facts(start + [run("feature/x", "green", "2026-11-16T10:30:00Z", names=("patterns",))], "feature/x")
    assert hidden["since"] == {"unit": {"result": "red", "at": "2026-11-16T10:20:00Z"}, "patterns": {"result": "green", "at": "2026-11-16T10:30:00Z"}}
    assert handover.since_result(hidden) == "red"
    text = page(runs=hidden, **walked)
    assert tile(text, "#facts") == ("red", "Passed, then a later partial run failed") and '<p class="headline red">' in top(text)
    assert ("most recently, the unit tests (unit) failed (16 Nov 2026, 10:20 UTC) and the scan for forbidden code patterns (patterns) passed "
            "(16 Nov 2026, 10:30 UTC). The check of the code for common mistakes (lint), the check of the defect log (escapes) and the browser tests (walks) were not run again.") in top(text)
    mended = handover.run_facts(start + [run("feature/x", "green", "2026-11-16T10:30:00Z", names=("unit",))], "feature/x")
    assert handover.since_result(mended) == "green" and tile(page(runs=mended, **walked), "#facts") == ("green", "Passed on the build&#x27;s last commit")
    skipped = run("feature/x", "red", "2026-11-16T10:40:00Z", names=("unit", "walks"))
    skipped["checks"][1].update(result="not run")
    assert set(handover.run_facts(start[:1] + [skipped], "feature/x")["since"]) == {"unit"}
    bare = handover.run_facts(start[:1] + [{"at": "2026-11-16T10:50:00Z", "branch": "feature/x", "result": "red", "checks": []}], "feature/x")
    assert bare["since"] == {"a run that names no check": {"result": "red", "at": "2026-11-16T10:50:00Z"}} and handover.since_result(bare) == "red"
    assert handover.since_result(handover.run_facts(start[:1], "feature/x")) == "green"


def test_why_a_green_run_is_not_counted_is_said_on_the_tile_itself():
    green = lambda **more: top(page(runs=handover.run_facts([run("feature/x", "green", **more)], "feature/x"), git=GIT))  # noqa: E731 (a one-line helper local to this function)
    assert "This run was on commit fff9999, not the build&#x27;s last commit (abc1234)." in green(tip="fff9999")
    assert "This run was with uncommitted changes in the folder." in green(dirty=True)
    assert "This run was" not in green()


def test_the_squares_of_the_run_history_and_the_lines_bar_are_never_the_passed_green():
    css = handover.CSS
    ok = re.search(r"--ok: (#\w+)", handover.LIGHT).group(1)
    assert ".runs .r-green { background: var(--fixed); }" in css and ".runs .part.r-green { border-color: var(--fixed); }" in css
    for tokens in (handover.LIGHT, handover.DARK):
        colours = dict(re.findall(r"--([\w-]+): (#\w+)", tokens))
        assert len({colours[name] for name in ("ok", "warn-fill", "bad-fill", "fixed", "s1", "s2", "s3")}) == 7
    assert ok not in re.sub(r"--ok(-bg)?: #\w+", "", handover.LIGHT)
    assert "A blue square is a run that passed, a red one a run that failed" in page(runs=handover.run_facts([run("feature/x", "green")], "feature/x"))


def test_a_check_that_was_not_run_has_no_duration_and_a_very_short_one_is_not_zero_minutes():
    line = run("feature/x", "red")
    line["checks"][1].update(minutes=0.0)
    line["checks"][4].update(result="not run", minutes=0.0)
    last = row(page(runs=handover.run_facts([line], "feature/x")), "Last full run of the checks")
    assert "scan for forbidden code patterns (patterns): " in last and "under 0.1 minutes" in last
    assert re.search(r'browser tests \(walks\): <span class="pill ">not run</span> output', last)
    assert "0 minutes" not in last



def git(repo, *args, when="2026-11-01T10:00:00+00:00"):
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    done = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """main: one commit. feature/x: three commits over 90 minutes, adding 3 tests and removing 1 test and 1 other line."""
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "walks").mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "app.py").write_text("one\ntwo\nthree\n")
    (root / "tests" / "test_old.py").write_text("def test_old():\n    pass\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    git(root, "checkout", "-q", "-b", "feature/x")
    (root / "app.py").write_text("one\nthree\nfour\nfive\n")
    (root / "tests" / "test_new.py").write_text("def test_a():\n    pass\n\n\ndef test_b():\n    pass\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first", when="2026-11-02T09:00:00+00:00")
    (root / "walks" / "test_walk.py").write_text("def test_walk_it():\n    pass\n")
    (root / "notes.py").write_text("def test_not_a_test_folder():\n    pass\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "second", when="2026-11-02T09:40:00+00:00")
    (root / "walks" / "helper.py").write_text("def helper():\n    return 'def test_in_a_string'\n")
    (root / "tests" / "test_old.py").unlink()
    (root / ".claude").mkdir()
    (root / ".claude" / "notes.md").write_text("a\nb\nc\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "third", when="2026-11-02T10:30:00+00:00")
    return root


def test_git_facts_count_commits_time_files_lines_and_tests_added_and_removed(repo):
    facts = handover.git_facts(repo, "main", "feature/x")
    assert facts["commits"] == 3
    assert handover.when(facts["first"]) == "2 Nov 2026, 09:00 UTC"
    assert handover.when(facts["last"]) == "2 Nov 2026, 10:30 UTC"
    assert facts["minutes"] == 90
    assert facts["files"] == 7
    assert facts["added_by"] == {"product": 2 + 2, "tests and browser tests": 6 + 2 + 2, "build records and agent instructions (.scratch/, .claude/)": 3}
    assert facts["added"] == 17
    assert facts["removed"] == 1 + 2
    assert facts["tests_added"] == 3
    assert facts["tests_removed"] == 1
    assert facts["base"] == git(repo, "rev-parse", "--short", "main")
    assert facts["tip"] == git(repo, "rev-parse", "--short", "feature/x")
    assert facts["merged"] is False
    text = page(git=facts)
    assert row(text, "Tests") == "3 added, 1 removed"
    assert [text.count(f'title="{kind}: {count}"') for kind, count in (("product", 4), ("tests and browser tests", 10))] == [1, 1]
    assert "of them 4 product, 10 tests and browser tests, 3 build records and agent instructions (.scratch/, .claude/)" in text


def test_git_facts_of_an_empty_range_leave_the_times_unknown(repo):
    facts = handover.git_facts(repo, "feature/x", "feature/x")
    assert facts["commits"] == 0 and facts["merged"] is False
    assert handover.git_facts(repo, "main", "main")["merged"] is False
    assert facts["first"] is None and facts["last"] is None and facts["minutes"] is None


def test_a_fixed_fate_needs_its_check_s_file_in_the_last_commit_and_its_commit_in_the_repository(repo):
    tip = git(repo, "rev-parse", "--short", "feature/x")
    fates = {
        "ok": fate("ok", check="walks/test_walk.py::test_walk_it[chromium-1440x900]", commit=tip),
        "whole-file": fate("whole-file", check="tests/test_new.py", commit=tip),
        "gone": fate("gone", check="tests/test_old.py::test_old", commit=tip),
        "no-commit": fate("no-commit", check="tests/test_new.py::test_a", commit=""),
        "bad-commit": fate("bad-commit", check="tests/test_new.py::test_a", commit="0123abc"),
        "both": fate("both", check="nowhere.py::test_x", commit="--help"),
        "left": fate("left", "left", check="nowhere.py", commit=""),
        "no-check": fate("no-check", check="", commit=""),
        "no-check-found": fate("no-check-found", check="", commit=tip),
        "no-check-lost": fate("no-check-lost", check="", commit="0123abc"),
    }
    missing = handover.missing_proof(repo, tip, fates)
    assert set(missing) == {"gone", "no-commit", "bad-commit", "both", "no-check-lost"}
    assert missing["no-check-lost"] == "commit 0123abc is not in the repository"
    assert missing["gone"] == f"the test's file tests/test_old.py is not in the build's last commit ({tip})"
    assert missing["no-commit"] == "no commit is named"
    assert missing["bad-commit"] == "commit 0123abc is not in the repository"
    assert "nowhere.py" in missing["both"] and "commit --help is not in the repository" in missing["both"]


def test_the_script_run_on_a_real_repository_writes_the_page_and_ends_with_the_open_command(repo, capsys):
    feature = repo / ".scratch" / "feat"
    tip = git(repo, "rev-parse", "--short", "HEAD")
    write_lines(feature / "findings" / "walker-a.jsonl", [finding("W-1"), finding("W-2"), finding("W-3"), finding("W-4")])
    write_lines(feature / "findings" / "review-a.jsonl", [])
    write_lines(feature / "fates.jsonl", [fate("W-1", check="walks/test_walk.py::test_walk_it", commit=tip),
                                          fate("W-3", check="walks/test_gone.py::test_x", commit=tip), fate("W-4", "left")])
    write_lines(repo / ".checks" / "runs.jsonl", [run("feature/x", "red"), run("feature/x", "green"), run("main", "red")])
    assert handover.main(["feat", "--base", "main", "--tip", "feature/x", "--branch", "feature/x", "--no-walk"], root=repo) == 0
    page_file = feature / "hand-over" / "index.html"
    printed = capsys.readouterr().out.splitlines()
    assert printed[-1] == f"open {page_file}"
    text = page_file.read_text(encoding="utf-8")
    headline = re.search(r'<p class="headline \w+"><span[^>]*>[^<]*</span>(.*?)</p>', text).group(1)
    assert printed[-2] == f"The page's headline: {headline}" and "things to look at before you accept this build" in headline
    assert "No recording" in text and "<video" not in text
    assert "1 of 2 runs" in text
    assert "No outcome recorded" in text and text.index("what W-2") < text.index("what W-4") < text.index("what W-3") < text.index("what W-1")
    assert "Missing: the test&#x27;s file walks/test_gone.py is not in the build&#x27;s last commit" in text
    assert "hand-over.json is missing" in text
    assert "<code>review-a.jsonl</code>: reviewed, found nothing" in text and "<code>walker-a.jsonl</code>: 4 issues" in text
    assert reviewer("early-read") + '<td colspan="2"><span class="unknown">no report found</span>' in text
    assert reviewer("review") + '<td class="n">none found</td>' + handover.NO_REPORT_CELL in text


def test_the_branch_whose_runs_are_counted_is_the_one_asked_for_and_a_tip_needs_one(repo):
    write_lines(repo / ".checks" / "runs.jsonl", [run("feature/x", "green"), run("main", "red"), run("main", "red")])
    (repo / ".scratch" / "feat").mkdir(parents=True)
    handover.main(["feat", "--tip", "feature/x", "--branch", "main", "--no-walk"], root=repo)
    assert "2 of 2 runs" in (repo / ".scratch" / "feat" / "hand-over" / "index.html").read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        handover.main(["feat", "--tip", "feature/x", "--no-walk"], root=repo)
    assert "--tip needs --branch" in str(stopped.value)


def test_a_feature_with_no_folder_stops_the_run(repo):
    with pytest.raises(SystemExit) as stopped:
        handover.main(["nothing-here", "--no-walk"], root=repo)
    assert "no feature folder" in str(stopped.value)


def test_tests_changed_counts_only_added_or_only_removed_def_test_lines():
    diff = "\n".join([
        "+++ b/tests/test_a.py",
        "+def test_one():",
        "+    async def test_two(self):",
        "-def test_removed():",
        " def test_context():",
        "+    x = 'def test_three'",
        "+def testing():",
    ])
    assert handover.tests_changed(diff, "+") == 2
    assert handover.tests_changed(diff, "-") == 1



HOSTILE = '<script>alert("x")</script> & <img src=x onerror=1>'


def test_a_hostile_string_is_escaped_everywhere_it_is_drawn():
    findings = [finding(HOSTILE, finder=HOSTILE, round=HOSTILE, area=HOSTILE, severity=HOSTILE, what=HOSTILE, where=HOSTILE, check=HOSTILE),
                finding("B"), finding("C")]
    fates = {HOSTILE: fate(HOSTILE, commit=HOSTILE, check=HOSTILE, why=HOSTILE), "B": fate("B", HOSTILE, why=HOSTILE),
             "C": fate("C"), "orphan" + HOSTILE: fate("orphan" + HOSTILE, HOSTILE, why=HOSTILE)}
    hostile_run = {"at": HOSTILE, "branch": HOSTILE, "tip": HOSTILE, "dirty": True, "result": HOSTILE, "minutes": 1.0,
                   "checks": [{"name": HOSTILE, "result": HOSTILE, "minutes": 1.0, "output": HOSTILE}]}
    for last in (hostile_run, {**hostile_run, "result": "green"}):
        text = handover.render(handover.page_data(
            HOSTILE, base_ref=HOSTILE, tip_ref=HOSTILE, git={**GIT, "base": HOSTILE, "tip": HOSTILE},
            files={HOSTILE + ".jsonl": findings}, fates=fates, missing={"C": HOSTILE},
            runs=handover.run_facts([last, {**hostile_run, "checks": []}], HOSTILE, names=[HOSTILE]),
            summary={"what": [HOSTILE], "so_what": [HOSTILE], "now_what": [HOSTILE]},
            recording={"walk": HOSTILE, "at": HOSTILE, "commit": HOSTILE, "dirty": True, "result": HOSTILE, "reason": HOSTILE,
                       "minutes": 1.5, "megabytes": 1.0},
            shots=[HOSTILE + ".png"], built={"at": HOSTILE, "commit": HOSTILE},
        ))
        assert text.count("<script") == 1
        assert "<img src=x" not in text
        assert text.count("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &lt;img src=x onerror=1&gt;") > 30


def group_tag(text: str, marker: str) -> str:
    """The <details ...> tag of the group that holds `marker`."""
    return re.findall(r"<details[^>]*>", text[:text.index(marker)])[-1]


def test_no_fate_left_and_fixed_with_no_check_each_have_their_own_look_and_no_fate_comes_first():
    findings = [finding("FIXED-1"), finding("NOFATE-1"), finding("NOCHECK-1"), finding("LEFT-1"), finding("ODD-1")]
    fates = {"FIXED-1": fate("FIXED-1"), "NOCHECK-1": fate("NOCHECK-1", check=""), "LEFT-1": fate("LEFT-1", "left"),
             "ODD-1": fate("ODD-1", "Fixed")}
    text = page(findings, fates=fates)
    cards = text[text.index('<section id="findings">'):]
    assert cards.index("what NOFATE-1") < cards.index("what ODD-1") < cards.index("what LEFT-1") < cards.index("what NOCHECK-1") < cards.index("what FIXED-1")
    tags = {name: group_tag(cards, f"what {name}-1") for name in ("NOFATE", "ODD", "LEFT", "NOCHECK", "FIXED")}
    assert 'class="group bad" open' in tags["NOFATE"] and 'class="group bad" open' in tags["ODD"]
    assert 'class="group warn" open' in tags["LEFT"]
    assert 'class="group note"' in tags["NOCHECK"] and "open" not in tags["NOCHECK"]
    assert 'class="group "' in tags["FIXED"] and "open" not in tags["FIXED"]
    assert "No outcome recorded" in text and "Marked fixed, no test named" in text and "Outcome not recognised (&quot;Fixed&quot;)" in text
    assert row(text, "Issues with no outcome recorded") == '<span class="badly">1</span>'


def test_the_board_under_the_title_says_what_needs_the_owner_before_anything_else():
    green_run, every = handover.run_facts([run("feature/x", "green")], "feature/x"), {"walker-a.jsonl": [finding("A")], "review-a.jsonl": [], "early-read-whole.jsonl": []}
    settled = {"fates": {"A": fate("A")}, "git": GIT, "runs": green_run, "recording": {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0}}
    clean = page(files=every, **settled)
    assert '<p class="headline green">' in top(clean) and "This page found nothing that needs a second look before you accept this build" in top(clean)
    assert f"<p>To accept the build, tell the agent you are working with (a new session opened in this project will do). {handover.e(handover.ACCEPTING)}</p>" in top(clean)
    passed = "Passed on the build&#x27;s last commit"
    assert tile(clean, "#recording") == ("green", passed) and tile(clean, "#facts") == ("green", passed)
    assert "every reported issue is recorded either as not a defect or as fixed, each fix naming the test meant to show it works." in top(clean)
    assert chip(clean, "", "#group-0", "Marked fixed, test named: 1") and "1 reported" in top(clean)
    assert "The outcomes are the build's own record: this page did not test the fixes." in top(clean)
    assert '<a href="#summary">This build has no summary file (hand-over.json).</a>' in top(clean)
    left = lambda lines: top(page(files=every, summary={"what": [], "so_what": [], "now_what": lines}, **settled))  # noqa: E731 (a one-line helper local to this function)
    two = left(["Ticket 07 was not built.", "Try it in Safari."])
    assert ('<a href="#summary">The build&#x27;s summary file also lists what is left for you: 2 lines, further down this page. '
            "This page did not judge them: read them before you accept this build.</a>") in two
    assert ("The lines the build&#x27;s summary file (hand-over.json) lists as left for you are under &quot;The builder&#x27;s own summary&quot;. "
            "This page copied them as written.</p></details>") in two
    assert ("also lists what is left for you: 1 line, further down this page. This page did not judge it: "
            "read it before you accept this build.") in left(["One."])
    assert '<h2>The builder&#x27;s own summary</h2>' in clean
    assert '<a href="#summary">The build&#x27;s summary file (hand-over.json) is empty.</a>' in left([])
    built_only = top(page(files=every, summary={"what": ["Built."], "so_what": [], "now_what": []}, **settled))
    assert ('<a href="#summary">The build&#x27;s summary file is shown further down this page, under &quot;The builder&#x27;s own summary&quot;. '
            "It lists nothing as left for you.</a>") in built_only
    no_findings = top(page(files={name: [] for name in every}, **{**settled, "fates": {}}))
    assert '<p class="headline green">' in no_findings and "the reviewers reported no issues in the reports this page read." in no_findings and "did not test the fixes" not in no_findings
    odd_pass = page(files={**every, "walker-a.jsonl": [finding("A", round="third")]}, **settled)
    assert '<p class="headline amber">' in top(odd_pass) and "1 thing to look at" in top(odd_pass)
    assert chip(odd_pass, "amber", "#finders", "Review round not recognised: 1")
    two_did_not_look = top(page([finding("A")], **settled))
    assert '<p class="headline amber">' in two_did_not_look and "2 things to look at before you accept this build" in two_did_not_look
    assert "found nothing that needs" not in two_did_not_look
    red = page(files=every, fates={"A": fate("A")}, git=GIT, runs=handover.run_facts([run("feature/x", "red")], "feature/x"))
    assert tile(red, "#facts") == ("red", "Failed") and not drawn_green(red)
    assert '<p class="headline red">' in top(red) and "2 things to look at" in top(red)
    no_fate = page([finding("A"), finding("B"), finding("C"), finding("D")],
                   fates={"A": fate("A"), "C": fate("C", "left"), "D": fate("D", check=""), "Z": fate("Z")})
    for look, href, words in (("bad", "#group-0", "No outcome recorded: 1"), ("warn", "#group-1", "Left unfixed: 1"),
                              ("note", "#group-2", "Marked fixed, no test named: 1"), ("", "#group-3", "Marked fixed, test named: 1"),
                              ("amber", "#findings", "Outcomes matching no issue: 1"), ("amber", "#finders", "Code review: no report found")):
        assert chip(no_fate, look, href, words), words
    assert tile(no_fate, "#recording") == ("amber", "Not run for this page")
    assert re.findall(r'<span class="(s-\w+)" style="flex-grow: 1"', top(no_fate)) == ["s-bad", "s-left", "s-nocheck", "s-fixed"]
    assert '<p class="headline red">' in top(no_fate) and "8 things to look at" in top(no_fate) and "4 reported" in top(no_fate)
    assert 'id="group-0" class="group bad"' in no_fate
    nothing = top(page())
    nothing = nothing[nothing.index("<header>"):]
    assert "<strong>No review report found</strong>" in nothing and '<strong>This page found no review report for this build</strong>' in nothing
    assert not re.search(r">[^<]*\b0\b[^<]*<", nothing)


def test_a_reason_every_finding_of_a_group_shares_is_said_once_above_the_cards():
    why = "Out of scope for this build."
    same = page([finding("A"), finding("B"), finding("C")], fates={i: fate(i, "left", why=why) for i in "ABC"})
    assert f"<b>The reason recorded, the same for all 3:</b> {why}" in same
    assert "The build&#x27;s record gives the same reason for leaving all 3, printed once above the issues below. Read the reason and" in same
    assert next(why for _, href, _, why in things(same) if href == "#group-0").startswith("The build&#x27;s record gives the same reason for leaving all 3, printed with the issues, further down this "
                                          f"page. The reason, which this page did not check, begins: &quot;{why}&quot; Read the reason and")
    assert same.count(why) == 2 and top(same).count(why) == 1
    long = " ".join(["A reason that runs on and on"] * 12) + "."
    assert handover.first_sentence("One. Two.") == "One." and handover.first_sentence(long) == "" and handover.first_sentence("no end") == ""
    assert "begins:" not in top(page([finding("A"), finding("B")], fates={i: fate(i, "left", why=long) for i in "AB"}))
    mixed = page([finding("A"), finding("B")], fates={"A": fate("A", "left", why=why), "B": fate("B", "left", why="Another reason.")})
    assert mixed.count(why) == 1 and "Another reason." in mixed and "the same for all" not in mixed and "the same reason" not in mixed
    assert "The build&#x27;s record gives a reason for leaving each one, printed with the issues below. Read each reason and" in mixed
    assert mixed.count("<b>Reason recorded:</b>") == 2
    some = page([finding(i) for i in "ABCD"], fates={"A": fate("A", "left", why=why), "B": fate("B", "left", why="Another reason."),
                                                     "C": fate("C", "left", why=why), "D": fate("D", "left")})
    assert some.count(f"<b>Reason recorded:</b> {why}") == 1 and "the same for all" not in some
    assert some.count("<b>Reason recorded:</b> the same as for <code>A</code>, above.") == 1
    assert [record(some, i).get("Note recorded") for i in "ABCD"] == [None, None, None, None]
    assert "<b>Reason recorded:</b>" not in cards(some)[3] and cards(some)[2].index("what C looks like") < cards(some)[2].index("the same as for")
    alone = page([finding("A")], fates={"A": fate("A", "left", why=why)})
    assert alone.count(why) == 1 and "the same for all" not in alone
    assert "the same for all" not in page([finding("A"), finding("B")], fates={i: fate(i) for i in "AB"})
    folded = same[same.index('<section id="findings">'):]
    assert "A group is shown open when its issues were left unfixed, have no usable outcome recorded," in folded and "settled" not in folded


def test_the_headline_s_count_is_a_list_that_names_each_thing_says_why_and_links_to_it():
    green_run = handover.run_facts([run("feature/x", "green", tip="fff9999")], "feature/x")
    text = page([finding("A"), finding("B"), finding("C"), finding("D")], git=GIT, runs=green_run,
                fates={"A": fate("A"), "C": fate("C", "left"), "D": fate("D", check=""), "Z": fate("Z")},
                recording={"commit": "abc1234", "dirty": True, "result": "passed", "megabytes": 1.0})
    listed = things(text)
    assert [(colour, link, what) for colour, link, what, _ in listed] == [
        ("red", "#group-0", "The build&#x27;s record gives no outcome for 1 issue"),
        ("amber", "#recording", "The build&#x27;s last commit is not shown to pass the walk-through"),
        ("amber", "#facts", "The build&#x27;s last commit is not shown to pass the automated checks"),
        ("amber", "#group-1", "The record marks 1 issue as left unfixed"),
        ("amber", "#group-2", "The record names no test for 1 issue it marks as fixed"),
        ("amber", "#finders", "This page found no report from the code review"), ("amber", "#finders", "This page found no report from the early code review"),
        ("amber", "#findings", "The record gives an outcome for 1 issue that is in no review report this page read")]
    assert f"{len(listed)} things to look at before you accept this build" in top(text)
    whys = [why for *_, why in listed]
    assert whys[0] == ("Nothing on record says whether this issue was fixed, left unfixed or judged not a defect, so treat it as open. "
                       "Ask what became of it before you accept this build.")
    assert whys[1] == ("The walk-through passed, but with uncommitted changes in the folder. Ask for it to be run again on the build&#x27;s last commit, "
                       "with nothing uncommitted in the folder.")
    assert whys[2] == ("The last run of every check passed, but on commit fff9999, not the build&#x27;s last commit (abc1234). "
                       "Ask for every check to be run on the build&#x27;s last commit.")
    assert whys[3] == "The build&#x27;s record gives no reason for leaving it unfixed. Ask for the reason, then decide whether you accept it."
    assert whys[4].endswith("A test may exist that the record does not name. Try the fix yourself, or ask for a test.")
    assert whys[5] == handover.e(f"{handover.NO_REPORT} In this review, agents read the build's code changes for faults the tests would not catch. "
                                 "Ask whether it was made. If it was not, decide whether you want it made before you accept this build.")
    assert whys[6].endswith("Ask whether it was made. If it was not, it can now only be made late, on the finished build: decide whether you want that "
                            "before you accept this build.")
    assert "did not run" not in "".join(whys[5:7]) and "cannot tell which" in whys[5] and "cannot tell which" in whys[6]
    assert whys[7] == "So an issue may have been reported somewhere this page does not look. Ask where it was reported."
    assert all(re.search(r"\b(Ask|Decide|Read|Try|decide) [^.]*\.$", why) for why in whys), whys
    assert all(why for why in whys) and "names a test for each" not in "".join(what for _, _, what, _ in listed)
    red = page(runs=handover.run_facts([run("feature/x", "red")], "feature/x"), git=GIT, recording={**RECORDING, "result": "failed", "reason": "It was stopped after 15 minutes"})
    assert things(red)[:2] == [
        ("red", "#recording", "The walk-through failed", "It was stopped after 15 minutes. So nothing on this page shows that the app can be used from "
         "start to finish. What the run printed is in walk-output.txt, beside this page. It was started on commit dd4ea9d, not the build&#x27;s last "
         "commit (abc1234) and with uncommitted changes in the folder, so it does not show whether the build&#x27;s last commit fails either. "
         "Ask for it to be run again on the build&#x27;s last commit, with nothing uncommitted in the folder."),
        ("red", "#facts", "The automated checks failed", "The last run of every check failed at the check of the code for common mistakes (lint), the scan for forbidden code patterns (patterns), "
         "the check of the defect log (escapes), the unit tests (unit) and the browser tests (walks). Ask for the failure to be fixed before you "
         "accept this build.")]
    on_tip = page(git=GIT, recording={**RECORDING, "commit": "abc1234", "dirty": False, "result": "failed", "reason": "It was stopped after 15 minutes"})
    assert things(on_tip)[0][3].endswith("beside this page. Ask for this to be looked into before you accept this build.")
    assert things(page())[0] == ("amber", "#recording", "The walk-through was not run for this page",
                                 "There is no recording and there are no pictures, so this page does not show the app being used. "
                                 "Ask for this page to be built again with the walk-through.")
    assert things(page())[2] == ("amber", "#finders", "This page found no review report for this build",
                                 "It looks for the reports of the build&#x27;s reviews (exploratory testing, code review and early code review) in one "
                                 "place (findings/*.jsonl) and found none. Either no review was made or the reports are somewhere else: this page cannot "
                                 "tell which, so nothing on this page shows that anyone tested or read the build. Ask whether the reviews were made; if "
                                 "they were not, decide whether you want them made before you accept this build.")
    assert len(things(page())) == 3
    every = {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}
    clean = page(files=every, git=GIT, runs=handover.run_facts([run("feature/x", "green")], "feature/x"),
                 recording={"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0})
    assert things(clean) == [] and '<ol class="look">' not in clean


def test_the_page_labels_what_an_agent_wrote_and_what_the_script_computed():
    text = page([finding("A", what="The finder saw this.")], fates={"A": fate("A", "left", why="The fixer gave this reason.")},
                summary={"what": ["Built the thing."], "so_what": ["It matters."], "now_what": ["Decide."]})
    assert "Agents' words" in handover.CSS and "Counted by this page" in handover.CSS
    sections = {match.group(1): match.group(2) for match in re.finditer(r'<section id="(\w+)">(.*?)</section>', text, re.S)}
    agent_words = ("Built the thing.", "It matters.", "Decide.", "The finder saw this.", "The fixer gave this reason.")
    for name, body in sections.items():
        assert any(words in body for words in agent_words) == (name in ("summary", "findings")), name
    head = top(text)
    built = re.search(r'<details class="built">(.*?)</details>', head, re.S).group(1)
    assert '<span class="first">Built the thing.</span>' in built and "What was built, in the builder's words, not checked by this page" in built
    assert ("This line comes from the build's summary file (hand-over.json), which the agent that runs a build is meant to write. "
            "This page copied it as written and did not check it.") in html.unescape(built)
    assert built.index("not checked by this page") < built.index("Built the thing.") < built.index("did not check it")
    assert all(words not in head.replace(built, "") for words in agent_words)
    assert text.count("Built the thing.") == 1 and head.index('<details class="built">') < head.index('<p class="lead">')
    for name in sections:
        label = "agent" if name in ("summary", "findings") else "script"
        assert (f'class="source {label}"' in sections[name]) == (name != "recording"), name
    assert "did not check them" in sections["summary"] and "did not check them" in sections["findings"]
    assert "copied from the review report files as written" in sections["findings"] and "what the build's record says" in sections["findings"]


def test_what_is_left_shows_its_first_lines_and_folds_the_rest_under_their_count():
    lines = [f"Left {n}." for n in range(1, 8)]
    text = page(summary={"what": ["Built."], "so_what": ["It matters."], "now_what": lines})
    card = text[text.index("<h3>What is left for you"):text.index("</section>", text.index("<h3>What is left for you"))]
    shown, folded = card.split("<details>")
    assert [line in shown for line in lines] == [True] * 5 + [False] * 2
    assert "<summary>2 more</summary>" in folded and all(line in folded for line in lines[5:])
    assert "<details>" not in page(summary={"what": ["Built."], "so_what": ["It matters."], "now_what": lines[:5]}).split('id="summary"')[1].split("</section>")[0]


def test_the_page_says_so_when_there_is_no_summary_no_recording_and_no_findings_file():
    text = page()
    assert "<video" not in text
    assert "No recording: the walk-through was not run for this page." in text
    assert "No screenshots: the walk-through was not run for this page." in text
    assert "hand-over.json" in text
    assert "This page cannot say what was built: the build has no summary file (hand-over.json is missing)." in top(text)
    assert text.count("This page found no review report for this build.") == 1 and "So there is nothing to list." in text
    assert "<strong>This page found no review report for this build</strong>" in top(text)
    assert text.count('<span class="unknown">no report found</span>') == 3
    assert "This page found no review report, so nothing on this page shows that anyone tested or read the build." in text
    assert "did not run" not in text.replace("the walk-through was not run", "")


def test_a_finder_that_looked_and_found_nothing_is_told_apart_from_one_that_never_ran():
    looked = page(files={"walker-find-trials.jsonl": [], "early-read-whole.jsonl": []})
    assert looked.count("reviewed, found nothing") == 2
    assert looked.count('<span class="unknown">no report found</span>') == 1 and reviewer("review") + "<td colspan" in looked
    assert reviewer("walker") + '<td class="n">none found</td>' + handover.NO_REPORT_CELL in looked
    assert handover.NO_REPORT_CELL == '<td class="n soft">no report found<small>not made, or its report is elsewhere</small></td>'
    assert reviewer("early-read") + '<td class="n">none found</td><td class="n soft">none is made</td>' in looked
    assert looked.count("The reviewers reported no issues in the reports this page read.") == 1
    assert "No issues in the 2 reports read" in top(looked) and "Code review: no report found" in top(looked)
    assert "This page read no re-check report, so nothing on record shows that one was made." in looked
    rechecked = page(files={"walker-a.jsonl": [], "walker-a-recheck.jsonl": []})
    assert reviewer("walker") + '<td class="n">none found</td><td class="n">none found</td>' in rechecked
    only_again = page(files={"review-whole-recheck.jsonl": [finding("R-1", "review", "recheck")]})
    assert reviewer("review") + handover.NO_REPORT_CELL + '<td class="n">1</td>' in only_again
    assert "This page read no re-check report" not in rechecked and "This page read no re-check report" not in page()
    named_by_its_rows = page(files={"1-anything.jsonl": [finding("A", "review")]})
    assert reviewer("review") + '<td class="n">1</td>' in named_by_its_rows and reviewer("walker") + "<td colspan" in named_by_its_rows
    assert looked != page()


def test_a_report_is_matched_to_its_review_by_its_file_name_or_its_rows_and_an_unmatched_empty_file_is_said():
    assert handover.wrote("1-walker.jsonl", "walker") and handover.wrote("walker-find-trials-recheck.jsonl", "walker")
    assert handover.wrote("2-review.jsonl", "review") and handover.wrote("early-read-whole.jsonl", "early-read")
    assert not handover.wrote("preview-notes.jsonl", "review") and not handover.wrote("reviewer.jsonl", "review")
    assert handover.absent_finders({"1-walker.jsonl": [], "notes.jsonl": [finding("A", "review")]}) == ["early-read"]
    stray = page(files={"notes.jsonl": []})
    assert "<code>notes.jsonl</code>: empty report: its name does not say which review wrote it" in stray
    assert stray.count('<span class="unknown">no report found</span>') == 3


def test_fate_lines_that_match_no_finding_are_drawn_first_and_marked_with_or_without_findings():
    fates = {"Z1": fate("Z1"), "Z2": fate("Z2", "left", why="left on purpose")}
    alone = page(fates=fates)
    assert "The record gives outcomes for 2 issues that are in no review report this page read." in alone
    assert "<code>Z1</code>: fixed.</li>" in alone and "<code>Z2</code>: left unfixed. Reason recorded: left on purpose</li>" in alone
    assert "nothing to list" not in alone and "reported no issues" not in alone
    assert row(alone, "Outcomes matching no issue") == '<span class="warned">2</span>'
    beside = page([finding("A")], fates={**fates, "A": fate("A")})
    assert beside.index('<div class="orphans">') < beside.index("<details", beside.index('<section id="findings">'))
    assert row(page([finding("A")], fates={"A": fate("A")}), "Outcomes matching no issue") == "0"


def test_every_finding_read_is_drawn_once_as_a_card_and_counted_once_in_each_count():
    findings = [finding("A"), finding("B", round="recheck"), finding("C", "review"), finding("D", "stranger", "re-check"),
                finding("E", round=None), finding("F", ""), finding("G"), finding("H")]
    del findings[6]["finder"]
    fates = {"A": fate("A"), "B": fate("B", check=""), "C": fate("C", "left"), "D": fate("D", "not-a-defect"),
             "F": fate("F", "Fixed"), "G": fate("G", ""), "H": fate("H")}
    text = page(files={"walker-a.jsonl": findings[:4], "other.jsonl": findings[4:]}, fates=fates, missing={"H": "no commit is named"})
    drawn = cards(text)
    assert len(drawn) == 8
    for f in findings:
        assert sum(f'what {f["id"]} looks like</p>' in card for card in drawn) == 1, f["id"]
        assert text.count(f'<summary>Record <code>{f["id"]}</code></summary>') == 1, f["id"]
    assert sum(int(n) for n in re.findall(r"<h3>[^<]*?(\d+) issues?\b[^<]*</h3>", text)) == 8
    assert ("reported 8 issues in the reports this page read. The build&#x27;s record marks 3 as fixed (1 of them with no test named), 1 as left unfixed and 1 as not a defect. "
            "It gives no usable outcome for 3.") in text
    table = re.search(r"<tbody>(.*?)</tbody>", text, re.S).group(1)
    assert sum(int(n) for n in re.findall(r">(\d+)</(?:td|span)>", table)) == 8
    assert sum(int(n) for n in re.findall(r'href="#group-\d+"><i[^>]*></i>[^<]*: (\d+)<', top(text))) == 8
    assert sum(int(n) for n in re.findall(r'style="flex-grow: (\d+)" title', top(text))) == 8 and "8 reported" in top(text)
    assert row(text, "Issues reported") == "8"
    assert "<code>walker-a.jsonl</code>: 4 issues" in text and "<code>other.jsonl</code>: 4 issues" in text



def test_the_issues_sentence_counts_the_issues_and_their_recorded_outcomes_from_the_records():
    said = lambda findings, fates: handover.issues_said(handover.page_data("feat", files={"walker-a.jsonl": findings}, fates=fates))  # noqa: E731 (a one-line helper local to this function)
    three = [finding("A"), finding("B"), finding("C")]
    assert said(three, {i: fate(i) for i in "ABC"}) == "The reviewers reported 3 issues in the reports this page read. The build's record marks 3 as fixed."
    assert said(three, {"A": fate("A"), "B": fate("B", "left"), "C": fate("C", "left")}).endswith("The build's record marks 1 as fixed and 2 as left unfixed.")
    assert said(three, {"A": fate("A", "not-a-defect")}).endswith("The build's record marks 1 as not a defect. It gives no outcome for 2.")
    assert said(three, {}).endswith("reported 3 issues in the reports this page read. The build's record gives no outcome for 3.")
    assert said([finding("A")], {"A": fate("A", check="")}) == ("The reviewers reported 1 issue in the reports this page read. The build's record marks 1 as fixed "
                                                                "(with no test named).")
    assert said(three, {"A": fate("A"), "B": fate("B", check=""), "C": fate("C", "Fixed")}).endswith(
        "marks 2 as fixed (1 of them with no test named). It gives no usable outcome for 1.")
    text = page(three, fates={"A": fate("A"), "B": fate("B", "left")}, git=GIT)
    (verdict,) = re.findall(r'<p class="lead">(.*?)</p>', top(text), re.S)
    assert verdict == "<strong>Nothing on record shows that the build&#x27;s last commit passes the walk-through or the automated checks.</strong>"
    lead = "reported 3 issues in the reports this page read. The build&#x27;s record marks 1 as fixed and 1 as left unfixed. It gives no outcome for 1."
    assert text.count(lead) == 1 and lead not in top(text)
    assert (text.index('class="built"') < text.index(verdict) < text.index('<div class="board">') < text.index('class="headline') < text.index('<ol class="look">')
            < text.index('<details class="reading">') < text.index("For reference, this page covers commits") < text.index(lead))


def test_the_top_of_the_page_is_drawn_before_it_is_explained():
    """Nothing but the page's first sentence has to be read to reach the tiles and the list: what the page's words mean,
    where its list comes from and why each thing matters all open under folds, and are all still on the page."""
    more = dict(files={"walker-a.jsonl": [finding("A"), finding("B")]}, fates={"A": fate("A", "left", why="A reason."), "B": fate("B", check="")},
                summary={"what": ["Built one.", "Built two.", "Built three."], "so_what": [], "now_what": ["One."]})
    for merged in (False, True):
        data = handover.page_data("feat", git={**GIT, "merged": merged}, **more)
        text = handover.render(data)
        head = top(text)
        above = re.sub(r"(<details[^>]*>.*?</summary>).*?</details>", r"\1", head[head.index("</h1>"):head.index('<div class="board">')], flags=re.S)
        assert re.findall(r'<p class="([\w ]+)"', above) == ["kicker found", "lead"] + ["merged"] * merged
        assert '<span class="first">Built one. <span class="more">and 2 more lines</span></span></summary><ul><li>Built two.</li><li>Built three.</li></ul>' in head
        reading = re.search(r'<details class="reading"><summary>How to read this page, and what its words mean</summary>(.*?)</details>', head, re.S).group(1)
        for words in (handover.TERMS, handover.WORDS, handover.list_said(len(handover.to_look_at(data)))):
            assert head.count(handover.e(words)) == 1 and handover.e(words) in reading
        assert (handover.e(handover.MERGED_HOW) in reading) == merged
        listed = handover.to_look_at(data)
        assert len(listed) >= 4 and all(so and do for _, _, so, do, _ in listed)
        said = lambda words: handover.e(handover.undecided(words, data))  # noqa: E731 (a one-line helper local to this function)
        assert [(shown, folded) for _, _, _, shown, folded in looks(text)] == [(said(do), said(so)) for _, _, so, do, _ in listed]
        between = head[head.index("</ol>"):head.index('<details class="reading">')]
        assert between.count("<p") == 2


def test_the_page_has_every_section_once_in_the_order_it_is_read():
    text = page([finding("A")], fates={"A": fate("A", "left", why="A reason.")}, summary={"what": ["w"], "so_what": ["s"], "now_what": ["n"]})
    assert re.findall(r'<section id="(\w+)">', text) == ["recording", "summary", "findings", "finders", "facts"]
    assert text.count("<header>") == 1 and text.index("<header>") < text.index('<section id="recording">')
    for title in ("What it gives you", "What is left for you"):
        assert text.count(f"<h3>{title}</h3>") == 1
    assert text.count("What was built, in the builder's words, not checked by this page</span>") == 1 and "<h3>What was built</h3>" not in text
    empty = page()
    assert re.findall(r'<section id="(\w+)">', empty) == ["recording", "summary", "findings", "finders", "facts"]


def test_each_group_of_issues_says_what_the_record_shows_and_what_that_means_once_above_its_list():
    why = "Outside what this build set out to fix."
    findings = [finding(i) for i in "ABCDE"]
    text = page(findings, fates={**{i: fate(i, "left", why=why) for i in "ABC"}, "D": fate("D", check=""), "E": fate("E")}, missing={})
    body = text[text.index('<section id="findings">'):text.index('<section id="finders">')]
    assert re.findall(r"<h3>(.*?)</h3>", body) == ["The record marks 3 issues as left unfixed", "The record names no test for 1 issue it marks as fixed",
                                                  "The record marks 1 issue as fixed and names a test for it"]
    for state, rows in handover.page_data("feat", files={"w.jsonl": findings}, fates={i: fate(i, "left", why=why) for i in "ABC"}).get("groups"):
        what, so_what = handover.state_said(state, rows)
        assert body.count(handover.e(so_what)) == (1 if state == "left" else 0)
    drawn = cards(body)
    in_view = [re.sub(r'<details class="trace">.*', "", card, flags=re.S) for card in drawn]
    lines = [line for card in in_view for line in re.findall(r"<p[^>]*>.*?</p>", card, re.S)]
    assert len(lines) == len(set(lines)) == 5
    assert all(why not in card for card in drawn) and body.count(why) == 1


def test_a_recorded_fix_is_worded_as_the_record_s_claim_and_never_as_this_page_s_finding():
    findings, fates = [finding("A"), finding("B"), finding("C")], {"A": fate("A"), "B": fate("B", check=""), "C": fate("C")}
    for missing in (None, {}, {"C": "no commit is named"}):
        text = page(findings, fates=fates, missing=missing)
        heads = re.findall(r"<h3>(.*?)</h3>", text[text.index('<section id="findings">'):text.index('<section id="finders">')])
        assert heads and all(head.startswith(("The record marks ", "The record names no test for ")) for head in heads), heads
        assert "This page reproduces them and did not check them." in text
        assert ("It did not run the tests." in text, "It did not run the test." in text) == (missing == {}, bool(missing))
    for state in handover.STATES:
        what, so_what = handover.state_said(state, [{"fate": fate("A", why="r")}], verified=True)
        assert not re.search(r"\b(verified|confirmed|proven|proved|works)\b", what), what
        assert not re.search(r"\b(verified|confirmed|proven|proved)\b", so_what + handover.FOUND), so_what
        assert "The record" in what or "The build" in what, what


def test_a_severity_is_shown_only_where_a_reviewer_recorded_one_and_its_absence_is_said():
    bare = [finding("A", severity=""), finding("B", severity=None), finding("C")]
    del bare[2]["severity"]
    text = page(bare, fates={i: fate(i, "left", why="r") for i in "ABC"})
    assert '<span class="sev' not in text and "blocking use" not in text
    assert top(text).count("The reviewers&#x27; reports record no severity for any of the 3, so this page cannot say how serious they are.") == 1
    assert [record(text, i)["Severity"] for i in "ABC"] == ["not recorded in the review report"] * 3
    assert "reports record no severity for 1 of the 2, so this page cannot say how serious it is." in page(bare[:1] + [finding("D")], fates={})
    assert "reports record no severity for this issue, so this page cannot say how serious it is." in page(bare[:1], fates={})
    mixed = page([finding("A", severity="blocks"), finding("B", severity="urgent"), finding("C", severity="cosmetic"), finding("D")],
                 fates={i: fate(i, "left", why="r") for i in "ABCD"})
    assert re.findall(r'<span class="sev( blocks)?">(.*?)</span>', mixed) == [(" blocks", "blocks use"), ("", "wrong"), ("", "cosmetic")]
    assert "record no severity" not in mixed
    assert "1 issue records a severity this page does not recognise; it is shown as written in that issue's record." in mixed
    assert record(mixed, "B")["Severity"] == "urgent"
    assert mixed.count("The reviewers recorded 1 of the 4 as blocking use") == 2
    every = page([finding("A", severity="blocks"), finding("B", severity="blocks")], fates={})
    assert "The reviewers recorded all 2 as blocking use" in every
    assert "The reviewer recorded it as blocking use" in page([finding("A", severity="blocks")], fates={})
    assert "record no severity" not in page([finding("A")], fates={"A": fate("A")})
    fixed = page([finding("A", severity="blocks")], fates={"A": fate("A")})
    assert "blocking use" not in fixed


def test_the_most_serious_recorded_severity_comes_first_within_a_group():
    order = [finding("C", severity="cosmetic"), finding("N", severity=""), finding("W", severity="wrong"), finding("B", severity="blocks"),
             finding("W2", severity="wrong")]
    groups = handover.group_by_state(handover.join(order, {f["id"]: fate(f["id"], "left") for f in order}))
    assert [f["id"] for f in groups[0][1]] == ["B", "W", "W2", "C", "N"]


def test_everything_recorded_about_an_issue_stays_on_the_page_in_its_folded_record():
    found = finding("walker-find-trials-03", round="recheck", area="saved-search", where="webapp/static/app.js:12", check="walks/test_a.py::test_seen")
    fixed = page([found], fates={found["id"]: fate(found["id"], commit="abc1234", check="tests/test_b.py::test_fixed", why="Fixed in ticket 08.")})
    assert record(fixed, found["id"]) == {
        "Reported by": "Exploratory testing, re-check after the fixes", "Area": "saved-search", "Severity": "wrong", "Where": "webapp/static/app.js:12",
        "Reviewer&#x27;s test": "<code>walks/test_a.py::test_seen</code>", "Outcome recorded": "fixed", "Commit": "<code>abc1234</code>",
        "Test named": "<code>tests/test_b.py::test_fixed</code>", "Note recorded": "Fixed in ticket 08."}
    assert fixed.count("Fixed in ticket 08.") == 1 and "<b>Reason recorded:</b>" not in fixed
    left = page([found], fates={found["id"]: fate(found["id"], "left", commit="", check="", why="Could not be made to pass.")})
    assert "<b>Reason recorded:</b> Could not be made to pass." in left and left.count("Could not be made to pass.") == 1
    assert record(left, found["id"])["Outcome recorded"] == "left" and "Test named" not in record(left, found["id"])
    none = page([found])
    assert record(none, found["id"])["Outcome recorded"] == "none"
    no_test = page([found], fates={found["id"]: fate(found["id"], check="")})
    assert record(no_test, found["id"])["Test named"] == "none"


def test_a_reason_the_record_does_not_give_is_said_as_missing_not_assumed():
    left = lambda **whys: handover.state_said("left", [{"fate": fate(i, "left", why=why)} for i, why in whys.items()])[1]  # noqa: E731 (a one-line helper local to this function)
    assert left(A="r", B="q") == ("The build's record gives a reason for leaving each one, printed with the issues below. "
                                  "Read each reason and decide whether you accept it.")
    assert left(A="r", B=" r ") == ("The build's record gives the same reason for leaving all 2, printed once above the issues below. "
                                    "Read the reason and decide whether you accept it.")
    assert left(A="r") == "The build's record gives a reason for leaving it, printed with the issue below. Read the reason and decide whether you accept it."
    assert left(A="", B="  ") == "The build's record gives no reason for leaving them unfixed. Ask for the reason, then decide whether you accept it."
    assert left(A="r", B="", C="") == ("The build's record gives no reason for leaving 2 of the 3 unfixed. The reason it does give is printed with "
                                       "the issues below. Read it, ask for the rest, and decide whether you accept each reason.")
    assert left(A="r", B="q", C="").endswith("The reasons it does give are printed with the issues below. Read them, ask for the rest, and decide "
                                             "whether you accept each reason.")
    judged = handover.state_said("not-a-defect", [{"fate": fate("A", "not-a-defect", why="")}])[1]
    assert "this page did not check it" in judged and judged.endswith("The record gives no reason. Ask for the reason, then decide whether you agree.")


RECORDING = {"walk": "walks/test_acceptance_walk.py::test_x", "at": "2026-11-16T21:00:00+00:00",
             "commit": "dd4ea9d", "dirty": True, "result": "passed", "minutes": 1.5, "megabytes": 11.2}


def test_the_page_names_the_commit_the_recording_was_made_on_and_shows_the_video():
    text = page(recording=RECORDING, shots=["a-01-created.png"])
    assert '<video controls' in text and 'src="recording.webm"' in text
    assert "dd4ea9d" in text and "uncommitted changes" in text and "21:00 UTC" in text
    assert '<img src="shots/a-01-created.png" alt="Step 1: created">' in text and "<figcaption>Step 1: created</figcaption>" in text
    assert "walk-output.txt" not in text


def test_a_walk_is_drawn_as_passed_only_when_it_passed_on_the_build_s_last_commit_as_committed():
    on_tip = page(recording={**RECORDING, "commit": "abc1234", "dirty": False}, git=GIT)
    assert 'pill green">Passed on the build&#x27;s last commit<' in on_tip and "not the last commit" not in on_tip
    assert tile(on_tip, "#recording") == ("green", "Passed on the build&#x27;s last commit") and "The build&#x27;s last commit passed the walk-through." in top(on_tip)
    elsewhere = page(recording={**RECORDING, "dirty": False}, git=GIT)
    assert "That is not the last commit of the build (abc1234)" in elsewhere
    assert "It passed on commit <code>dd4ea9d</code>. It ran for 1.5 minutes." in top(elsewhere)
    assert "It passed on commit <code>abc1234</code>, with uncommitted changes in the folder." in top(page(recording={**RECORDING, "commit": "abc1234"}, git=GIT))
    for text, words in ((elsewhere, "Not shown to pass on the build&#x27;s last commit"),
                        (page(recording={**RECORDING, "commit": "abc1234"}, git=GIT), "Not shown to pass as committed")):
        assert not drawn_green(text)
        assert text.count("The build&#x27;s last commit is not shown to pass the walk-through") == 1
        assert text.count(words) == 2
        assert text.count("The walk-through passed") == text.count("The walk-through passed, but ") == 1
    longer = page(recording={**RECORDING, "commit": "abc1234def", "dirty": False}, git=GIT)
    assert tile(longer, "#recording") == ("green", "Passed on the build&#x27;s last commit") and "not the last commit" not in longer
    assert handover.same_commit("abc1234", "abc1234def") and handover.same_commit("abc1234def", "abc1234") and handover.same_commit("abc", "abc")
    assert not handover.same_commit("abc1234", "abc9999") and not handover.same_commit("abc", "abc1234") and not handover.same_commit("", "abc1234")


@pytest.mark.parametrize("result, words, short", [("failed", "The walk-through failed", "Failed"), ("did not run", "The walk-through did not run", "Did not run"),
                                                  ("did not finish", "The walk-through did not finish", "Did not finish"),
                                                  (None, "How the walk-through ended is unknown", "Result unknown")])
def test_a_walk_that_did_not_pass_is_never_drawn_as_passed_with_or_without_a_video(result, words, short):
    for megabytes in (11.2, None):
        text = page(recording={**RECORDING, "result": result, "megabytes": megabytes, "reason": "It was stopped after 15 minutes"})
        assert text.count(words) == (2 if result else 1) and "passed" not in top(text).lower() and not drawn_green(text)
        assert things(text)[0][2] == words and tile(text, "#recording") == ("red" if result else "amber", short)
        assert f'pill {"red" if result else "amber"}">{short}<' in text
        assert '<a href="walk-output.txt">' in text and "It was stopped after 15 minutes." in text
        assert ("<video" in text) == (megabytes is not None)
        assert ("It left no video file." in text) == (megabytes is None)
        assert "dd4ea9d" in text and "No recording" not in text
        assert "No screenshots: the walk-through left none." in text


def test_a_walk_that_passed_but_left_no_video_says_so():
    text = page(recording={**RECORDING, "megabytes": None})
    assert "<video" not in text and "It left no video file." in text and "MB" not in text


def test_the_walk_s_own_sentence_promises_only_what_the_walk_left():
    two, one = ["a-01-created.png", "a-02-fresh.png"], ["a-01-created.png"]
    passed = page(recording=RECORDING, shots=two)
    assert ("2 moments from the walk-through: one whole journey through the app, from start to finish, by keyboard alone. "
            "Step through them, or watch the recording of all of it.") in passed
    assert "It ran for 1.5 minutes" in top(passed)
    no_film = page(recording={**RECORDING, "megabytes": None}, shots=two)
    assert "Step through them." in no_film and "watch the recording" not in no_film
    failed = page(recording={**RECORDING, "result": "failed"}, shots=two)
    assert "2 moments from the walk-through: the app used up to where the run stopped. Step through them, or watch the recording." in failed
    assert "from start to finish" not in failed[failed.index('<section id="recording">'):] and "all of it" not in failed
    assert "Ended after 1.5 minutes" in top(failed) and "Ran for" not in top(failed)
    single = page(recording={**RECORDING, "result": "failed"}, shots=one)
    assert "1 moment from the walk-through: the app used up to where the run stopped. The recording shows the rest." in single and "Step through them" not in single
    assert "the app used" not in page(recording={**RECORDING, "result": "did not run", "megabytes": None})
    inside = page(recording=RECORDING, shots=[{"name": "a-01-created.png", "src": "data:image/png;base64,cG5n"}, {"name": "a-02-fresh.png", "src": "data:image/png;base64,cG5n"},
                                               {"name": "a-03-big.png", "src": "shots/a-03-big.png"}])
    assert inside.count('loading="lazy"') == 1 and '<img src="shots/a-03-big.png" alt="Step 3: big" loading="lazy">' in inside


def test_the_page_loads_nothing_from_outside_and_its_one_script_is_its_own():
    text = page([finding("A"), finding("B")], fates={"A": fate("A"), "Z": fate("Z")}, git=GIT, recording={**RECORDING, "result": "failed"},
                runs=handover.run_facts([run("feature/x", "green")], "feature/x"), shots=["a-01-created.png"],
                summary={"what": ["w"], "so_what": ["s"], "now_what": ["n"]}, built={"at": "2026-11-16T21:00:00+00:00", "commit": "abc1234"})
    assert text.count("<script") == 1 and f"<script>{handover.SCRIPT}</script>" in text and "javascript:" not in text
    assert not re.search(r"fetch|XMLHttp|WebSocket|import|http|location|cookie|eval|innerHTML", handover.SCRIPT)
    for part in ('a[href^="#group-"]', "g.open = true", "if (video.error)", "reel.scrollLeft", "ev.preventDefault()", "frames.length < 2"):
        assert part in handover.SCRIPT, part
    assert '[data-theme="dark"]' in text and ':root:not([data-theme="light"])' in text
    assert "http://" not in text and "https://" not in text and "//" not in text.replace("</", "")
    assert set(re.findall(r'(?:href|src)="([^"]*)"', text)) == {
        "#recording", "#facts", "#findings", "#finders", "#summary", "#group-0", "#group-1", "walk-output.txt", "recording.webm",
        "shots/a-01-created.png"}
    assert "prefers-color-scheme: dark" in text
    assert 'name="viewport"' in text
    assert "only you know" not in text


def test_times_are_written_in_utc_whatever_zone_they_were_recorded_in():
    assert handover.when("2026-11-08T16:20:11Z") == "8 Nov 2026, 16:20 UTC"
    assert handover.when("2026-10-01T19:32:28+01:00") == "1 Oct 2026, 18:32 UTC"
    assert handover.when(None) == "unknown"
    assert handover.when("last Tuesday") == "last Tuesday"


def test_durations_are_written_in_minutes():
    assert handover.minutes(851) == "851 minutes"
    assert handover.minutes(1) == "1 minute"
    assert handover.minutes(2.5) == "2.5 minutes"
    assert handover.minutes(0.04) == "under 0.1 minutes"
    assert handover.minutes(0) == "0 minutes"
    assert handover.minutes(None) == "unknown"



GREEN_RUN = [run("feature/x", "green")]
WALKED = {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0}


def test_the_page_opens_on_its_own_conclusion_about_the_walk_through_and_the_checks_then_says_what_each_one_is():
    said = lambda **more: handover.proof_said(handover.page_data("feat", git=GIT, **more))  # noqa: E731 (a one-line helper local to this function)
    green, red = handover.run_facts(GREEN_RUN, "feature/x"), handover.run_facts([run("feature/x", "red")], "feature/x")
    assert said(runs=green, recording=WALKED) == "The build's last commit passed the walk-through and the automated checks."
    assert said() == "Nothing on record shows that the build's last commit passes the walk-through or the automated checks."
    assert said(runs=green) == ("Nothing on record shows that the build's last commit passes the walk-through. The build's last commit passed "
                                "the automated checks.")
    assert said(runs=green, recording={**WALKED, "dirty": True}).startswith("Nothing on record shows that the build's last commit passes the walk-through.")
    assert said(runs=red, recording=WALKED) == "The automated checks failed. The build's last commit passed the walk-through."
    assert said(runs=red, recording={**WALKED, "result": "failed"}) == "The walk-through failed. The automated checks failed."
    assert said(runs=red) == ("The automated checks failed. Nothing on record shows that the build's last commit passes the walk-through.")
    text = top(page(git=GIT, runs=green, recording=WALKED, files={"walker-a.jsonl": []}))
    assert f'<p class="terms">{handover.e(handover.TERMS)}</p>' in text
    assert handover.TERMS.startswith("The walk-through is ") and " The automated checks are " in handover.TERMS
    assert f'<p class="terms">{handover.e(handover.WORDS)}</p>' in text
    assert all(word in handover.WORDS for word in ("A commit is ", "The reviewers are ", "The build's record is "))
    rule = (pathlib.Path(handover.__file__).parent / "CLAUDE.md").read_text()
    assert "**When the owner accepts a build:** the build already pushed its branch and opened a draft pull request" in rule
    assert "Mark the draft ready (`gh pr ready`) and give them the link; the owner merges it on GitHub." in rule
    assert handover.ACCEPTING.startswith("In this project, when you accept a build the agent marks its draft pull request ready to merge")
    assert set(handover.CHECK_GLOSS) == set(handover.CHECK_NAMES)


def test_each_outcome_s_sentences_are_worded_for_one_issue_and_for_many_and_claim_only_what_the_record_says():
    rows = lambda count, kind="left", why="r", **more: [{"fate": fate(str(n), kind, why=why), **more} for n in range(count)]  # noqa: E731 (a one-line helper local to this function)
    said = handover.state_said
    assert said("no-fate", rows(1)) == ("The build's record gives no outcome for 1 issue", "Nothing on record says whether this issue was fixed, left unfixed or "
                                        "judged not a defect, so treat it as open. Ask what became of it before you accept this build.")
    assert said("no-fate", rows(3))[1] == ("Nothing on record says whether any of these issues was fixed, left unfixed or judged not a defect, so treat each one "
                                           "as open. Ask what became of them before you accept this build.")
    assert said("fixed-not-found", rows(1)) == (
        "The record marks 1 issue as fixed, but the proof it gives is incomplete", "The test's file or the commit for the fix was not found, or no commit is "
        "named, so this page could not trace the fix. The issue says which. Ask for the missing proof before you count it as fixed.")
    assert said("fixed-not-found", rows(2))[1].endswith("could not trace each fix. Each issue says which. Ask for the missing proof before you count them as fixed.")
    assert said("fixed-no-check", rows(1)) == (
        "The record names no test for 1 issue it marks as fixed", "So this page can point to no test that shows this fix works, or that the fault would be "
        "caught if it came back. A test may exist that the record does not name. Try the fix yourself, or ask for a test.")
    assert said("fixed-no-check", rows(2))[1] == ("So this page can point to no test that shows these fixes work, or that the fault would be caught if it "
                                                  "came back. A test may exist that the record does not name. Try the fixes that matter to you, or ask "
                                                  "for a test for each.")
    assert "This page could not find the commit the record names for the fix." in said("fixed-no-check", rows(1, lacks="commit abc is not in the repository"))[1]
    assert ("This page could not find the commit the record names for 1 of the 2; each of those issues says which."
            in said("fixed-no-check", rows(1, lacks="commit abc is not in the repository") + rows(1))[1])
    assert said("fixed", rows(1)) == ("The record marks 1 issue as fixed and names a test for it", "The fix names the test that is meant to show it works.")
    assert said("fixed", rows(2)) == ("The record marks 2 issues as fixed and names a test for each", "Each fix names the test that is meant to show it works.")
    assert said("fixed", rows(2), verified=True)[1] == "Each fix names the test that is meant to show it works." + handover.FOUND
    assert said("fixed", rows(1), verified=True)[1] == "The fix names the test that is meant to show it works." + handover.FOUND_ONE
    whole = lambda count: [{"fate": fate(str(n), check="tests/test_b.py")} for n in range(count)]  # noqa: E731 (a one-line helper local to this test; its check is a file, with no test named in it)
    assert said("fixed", whole(1))[1] == "The fix names the test that is meant to show it works. The record names a whole test file, not one test in it."
    assert said("fixed", whole(1) + rows(2, "fixed"))[1].endswith("For 1 of the 3, the record names a whole test file, not one test in it.")
    assert said("fixed", whole(2))[1].endswith("For all 2, the record names a whole test file, not one test in it.")
    assert all(handover.FOUND not in said(state, rows(2), verified=True)[1] for state in handover.STATES if state != "fixed")
    assert said("not-a-defect", rows(1)) == ("The record judges 1 issue not to be a defect", "This is the build's own judgement, and this page did not check it. "
                                             "The record gives a reason, printed with the issue below.")
    assert said("not-a-defect", rows(1) + rows(1, why="q"))[1].endswith("The record gives a reason for each, printed with the issues below.")
    assert said("not-a-defect", rows(2))[1].endswith("The record gives the same reason for all 2, printed once above the issues below.")
    assert said("not-a-defect", rows(3, why="") + rows(1))[1].endswith("this page did not check it. The record gives no reason for 3 of the 4. "
                                                                        "Read the reasons it does give, ask for the rest, and decide whether you agree.")
    assert said("fate: Fixed", rows(1)) == (
        'The record gives 1 issue an outcome this page does not recognise: "Fixed"', "This page knows three outcomes: fixed, left unfixed and not a defect. "
        "This one tells it nothing, so treat the issue as open. Ask for the record to be corrected.")
    assert said("fate: Fixed", rows(2))[1].endswith("so treat each issue as open. Ask for the record to be corrected.")
    blocking = "as blocking use, which means a user cannot finish a task, or loses data."
    for state in ("no-fate", "fate: Fixed", "left", "fixed-not-found", "fixed-no-check", "not-a-defect"):
        assert f"The reviewers recorded 1 of the 2 {blocking}" in said(state, rows(1, severity="blocks") + rows(1))[1], state
        assert f"The reviewer recorded it {blocking}" in said(state, rows(1, severity="blocks"))[1], state
    assert said("not-a-defect", rows(2, severity="blocks"))[1].endswith(f"The reviewers recorded all 2 {blocking} Read the reason and decide whether you agree.")
    assert "blocking use" not in said("fixed", rows(2, severity="blocks"))[1]


def test_the_issues_sentence_counts_only_the_outcomes_of_reported_issues():
    text = page([finding("A"), finding("B")], fates={"A": fate("A"), "B": fate("B", "left"), "Z1": fate("Z1"), "Z2": fate("Z2", "left")})
    said = "The reviewers reported 2 issues in the reports this page read. The build&#x27;s record marks 1 as fixed and 1 as left unfixed."
    assert text.count(f'<p class="lead">{said}</p>') == 1 and said not in top(text)
    assert chip(text, "warn", "#group-0", "Left unfixed: 1") or "Left unfixed: 1" in top(text)
    assert chip(text, "amber", "#findings", "Outcomes matching no issue: 2")


def test_outcomes_matching_no_issue_are_counted_and_worded_as_recorded_one_or_many():
    three = page(fates={"Z1": fate("Z1"), "Z2": fate("Z2", "left", why="left on purpose"), "Z3": fate("Z3", "")})
    assert things(three)[-1][2:] == ("The record gives outcomes for 3 issues that are in no review report this page read",
                                     "So issues may have been reported somewhere this page does not look. Ask where they were reported.")
    assert "<code>Z1</code>: fixed.</li>" in three and "<code>Z2</code>: left unfixed. Reason recorded: left on purpose</li>" in three
    assert "<code>Z3</code>: no outcome named.</li>" in three and "<code>Z4</code>: &quot;Fixed&quot;, as written.</li>" in page(fates={"Z4": fate("Z4", "Fixed")})
    one = page(fates={"Z1": fate("Z1")})
    assert "<strong>The record gives an outcome for 1 issue that is in no review report this page read.</strong> The outcome below names" in one


def test_a_commit_and_a_test_stay_in_the_record_whatever_the_outcome_and_a_name_the_format_lacks_is_kept():
    sha = "0123456789abcdef0123456789abcdef01234567"
    found = [finding("A", finder="auditor", round="third", area="", check="walks/test_a.py::test_seen"), finding("B"), finding("C")]
    del found[0]["severity"]
    text = page(found, fates={"A": fate("A", "left", commit=sha, check="tests/test_b.py::test_kept", why="A reason."), "B": fate("B", commit=sha),
                              "C": fate("C", "not-a-defect", commit=sha, check="tests/test_c.py", why="Another.")},
                missing={"B": "commit abc is not in the repository"})
    a = record(text, "A")
    assert a["Reported by"] == "A review this page does not recognise: &quot;auditor&quot;, third"
    assert a["Area"] == "not recorded" and a["Severity"] == "not recorded in the review report"
    assert a["Commit"] == f"<code>{sha}</code>" and a["Test named"] == "<code>tests/test_b.py::test_kept</code>" and a["Outcome recorded"] == "left"
    assert a["Reviewer&#x27;s test"] == "<code>walks/test_a.py::test_seen</code>"
    assert record(text, "B")["Commit"] == f"<code>{sha}</code>" and record(text, "B")["Test named"] == "<code>walks/test_x.py::test_y</code>"
    assert record(text, "C")["Outcome recorded"] == "not-a-defect" and record(text, "C")["Test named"] == "<code>tests/test_c.py</code> (a whole test file: the record does not say which test in it)"
    labels = {"B": ("Marked fixed, proof incomplete", "warn", True), "C": ("Not a defect", "", False)}
    for id, (label, look, opened) in labels.items():
        tag = group_tag(text, f"what {id} looks like")
        assert f'class="group {look}"' in tag and ("open" in tag) == opened and label in top(text), id
    assert text.index("what A looks like") < text.index("what B looks like") < text.index("what C looks like")


def test_a_long_description_and_a_long_reason_are_on_the_page_whole_and_a_reason_is_there_once_for_every_outcome():
    what, why = "A description. " * 40, ("A reason. " * 90).strip()
    for kind in ("fixed", "left", "not-a-defect", "Fixed"):
        alone = page([finding("A", what=what)], fates={"A": fate("A", kind, why=why)})
        assert alone.count(handover.e(what)) == 1 and alone.count(handover.e(why)) == 1, kind
        shared = page([finding("A"), finding("B")], fates={i: fate(i, kind, why=why) for i in "AB"})
        assert shared.count(handover.e(why)) == 1 and "the same for all 2:" in shared, kind
    fixed = page([finding("A", what=what)], fates={"A": fate("A", why=why)})
    assert record(fixed, "A")["Note recorded"] == handover.e(why)


def test_a_page_with_nothing_to_look_at_still_says_what_it_did_not_check():
    settled = {"git": GIT, "runs": handover.run_facts(GREEN_RUN, "feature/x"), "recording": WALKED}
    every = lambda rows: {"walker-a.jsonl": rows, "review-a.jsonl": [], "early-read-whole.jsonl": []}  # noqa: E731 (a one-line helper local to this function)
    judged = top(page(files=every([finding("A"), finding("B"), finding("C")]), **settled,
                      fates={"A": fate("A", "not-a-defect", why="By design."), "B": fate("B", "not-a-defect", why="Not in the spec."), "C": fate("C")}))
    assert '<p class="headline green">' in judged and "This page found nothing that needs a second look before you accept this build" in judged
    assert ("The outcomes are the build's own record: this page did not test the fixes. 2 issues are judged not a defect: that is the build's own "
            "judgement, which this page did not check. This page read no re-check report, so nothing on record shows that a review "
            "read the fix.</p>") in judged
    assert "1 issue is judged not a defect: that" in top(page(files=every([finding("A")]), fates={"A": fate("A", "not-a-defect", why="By design.")}, **settled))
    fixed = top(page(files=every([finding("A")]), fates={"A": fate("A")}, **settled))
    assert "judged not a defect" not in fixed and "this page did not test the fixes. This page read no re-check report" in fixed
    rechecked = top(page(files={**every([finding("A")]), "walker-a-recheck.jsonl": []}, fates={"A": fate("A")}, **settled))
    assert "this page did not test the fixes.</p>" in rechecked


def test_a_judgement_of_not_a_defect_is_for_the_owner_to_read_when_it_gives_no_reason_or_overrules_a_blocking_rating():
    settled = {"git": GIT, "runs": handover.run_facts(GREEN_RUN, "feature/x"), "recording": WALKED}
    every = lambda rows: {"walker-a.jsonl": rows, "review-a.jsonl": [], "early-read-whole.jsonl": []}  # noqa: E731 (a one-line helper local to this function)
    mixed = page(files=every([finding("A", severity="blocks"), finding("B")]), **settled,
                 fates={"A": fate("A", "not-a-defect"), "B": fate("B", "not-a-defect", why="By design.")})
    assert '<p class="headline amber">' in top(mixed) and "1 thing to look at before you accept this build" in top(mixed)
    assert things(mixed) == [("amber", "#group-0", "The record judges 2 issues not to be a defect",
                              "This is the build&#x27;s own judgement, and this page did not check it. The record gives no reason for 1 of the 2. "
                              "The reviewers recorded 1 of the 2 as blocking use, which means a user cannot finish a task, or loses data. "
                              "Read the reasons it does give, ask for the rest, and decide whether you agree.")]
    assert 'class="group warn" open' in group_tag(mixed, "what A looks like")
    overruled = page(files=every([finding("A", severity="blocks")]), fates={"A": fate("A", "not-a-defect", why="By design.")}, **settled)
    assert things(overruled)[0][3].endswith("The reviewer recorded it as blocking use, which means a user cannot finish a task, or loses data. "
                                            "Read the reason and decide whether you agree.")
    unreasoned = page(files=every([finding("A")]), fates={"A": fate("A", "not-a-defect")}, **settled)
    assert things(unreasoned)[0][3].endswith("The record gives no reason. Ask for the reason, then decide whether you agree.")
    plain = page(files=every([finding("A")]), fates={"A": fate("A", "not-a-defect", why="By design.")}, **settled)
    assert things(plain) == [] and "open" not in group_tag(plain, "what A looks like")
    assert handover.state_look("not-a-defect", [{"severity": "wrong", "fate": fate("A", "not-a-defect", why="r")}]) == handover.state_look("not-a-defect")
    assert handover.state_look("fixed-no-check", [{"lacks": "commit abc is not in the repository"}])[1:] == ("warn", True)
    assert handover.state_look("fixed-no-check", [{"lacks": ""}]) == handover.state_look("fixed-no-check")


def test_the_builder_s_account_of_what_was_built_leads_the_page_as_its_words_and_changes_nothing_the_page_concludes():
    settled = {"git": GIT, "runs": handover.run_facts(GREEN_RUN, "feature/x"), "recording": WALKED,
               "files": {"walker-a.jsonl": [finding("A")], "review-a.jsonl": [], "early-read-whole.jsonl": []}, "fates": {"A": fate("A", "left", why="r")}}
    boast = {"what": ["Everything works and every issue is fixed.", "A second line."], "so_what": ["s"], "now_what": []}
    without, with_it = page(**settled), page(summary=boast, **settled)
    head = top(with_it)
    assert head.index("<h1>") < head.index("What was built, in the builder's words") < head.index("Everything works") < head.index("What this page found, from git")
    assert ("These lines come from the build's summary file (hand-over.json), which the agent that runs a build is meant to write. "
            "This page copied them as written and did not check them.") in html.unescape(head)
    conclusions = lambda text: (things(text), re.findall(r'<p class="headline (\w+)">(.*?)</p>', text), re.findall(r'<p class="lead">(.*?)</p>', text, re.S),  # noqa: E731 (a one-line helper local to this function)
                                tile(text, "#recording"), tile(text, "#facts"), drawn_green(text))
    assert conclusions(without) == conclusions(with_it)
    empty = top(page(summary={"what": [], "so_what": ["s"], "now_what": []}, **settled))
    assert "This page cannot say what was built: the build&#x27;s summary file (hand-over.json) has nothing under &quot;what&quot;." in empty
    assert "This page cannot say what was built: the build has no summary file (hand-over.json is missing)." in top(without)


def test_a_range_that_holds_no_commit_is_one_of_the_things_to_look_at():
    listed = things(page(git={**GIT, "commits": 0}))
    assert ("amber", "#facts", "This page covers no commits") in [(colour, link, what) for colour, link, what, _ in listed]
    why = next(why for _, _, what, why in listed if what == "This page covers no commits")
    assert why == ("The range it was asked for (0000000..abc1234) holds no commit, so its numbers describe no build. "
                   "Ask for this page to be built again from the build&#x27;s first commit to its last.")
    assert "This page covers no commits" not in page(git=GIT) and "This page covers no commits" not in page()


def test_the_builder_s_summary_is_pointed_to_apart_from_the_page_s_own_list_and_never_quoted_in_it():
    left = lambda lines, **more: top(page(summary={"what": [], "so_what": [], "now_what": lines}, **more))  # noqa: E731 (a one-line helper local to this function)
    several = left(["Ticket 07 was not built.", "Try it in Safari."])
    own = ('<p class="terms">This page worked out these 3 itself, from git and from the build&#x27;s record files: they are not taken from the '
           "builder&#x27;s summary. Each one links to the part of this page that shows it.</p>")
    assert several.index('<ol class="look">') < several.index('<details class="reading">') < several.index(own)
    assert f"<p>To ask for any of this, or to accept the build, tell the agent you are working with (a new session opened in this project will do). {handover.e(handover.ACCEPTING)}</p>" in several
    assert ('<a href="#summary">The build&#x27;s summary file also lists what is left for you: 2 lines, further down this page. '
            "This page did not compare them with the 3 above, so read them as well.</a>") in several
    assert ("lists as left for you are under &quot;The builder&#x27;s own summary&quot;. This page copied them as written: "
            "a line there may repeat one of these, explain it or disagree with it.</p></details>") in several
    quoted = top(page(summary={"what": ["Built the thing."], "so_what": [], "now_what": ["One."]}))
    assert ("lists as left for you is under &quot;The builder&#x27;s own summary&quot; and the lines quoted at the top of this page come from "
            "the same file. This page copied it as written") in quoted
    assert "Ticket 07" not in several and "Safari" not in several
    one = top(page([finding("A")], fates={"A": fate("A")}, git=GIT, runs=handover.run_facts(GREEN_RUN, "feature/x"), recording=WALKED,
                   files={"walker-a.jsonl": [finding("A")], "review-a.jsonl": []}, summary={"now_what": ["One."]}))
    assert "1 thing to look at before you accept this build" in one and "This page worked this out itself" in one and "It links to the part of this page that shows it." in one
    assert "1 line, further down this page. This page did not compare it with the item above, so read it as well.</a>" in one
    assert "This page copied it as written: a line there may repeat it, explain it or disagree with it.</p></details>" in one


def test_the_page_says_where_its_issues_and_numbers_came_from():
    text = page([finding("A")], fates={"A": fate("A", "left", why="r")}, git={**GIT, "commits": 3, "first": "2026-11-02T09:00:00+00:00", "last": "2026-11-02T10:30:00+00:00"},
                base_ref="main", tip_ref="feature/x", recording=RECORDING, built={"at": "2026-11-16T21:00:00+00:00", "commit": "abc1234"})
    assert "Issues the reviewers reported, by recorded outcome" in top(text)
    assert "Sources: findings/*.jsonl and fates.jsonl." in text and "issues with no outcome named in fates.jsonl" in text
    assert ("The build is 3 commits, made between 2 Nov 2026, 09:00 UTC and 2 Nov 2026, 10:30 UTC. For reference, this page covers commits "
            "<code>0000000..abc1234</code> (asked for as main to feature/x).") in top(text)
    assert ("<summary>The browser test behind it</summary>"
            '<ul class="files"><li><code>walks/test_acceptance_walk.py::test_x</code></li></ul>') in text
    assert "from the folder at commit <code>abc1234</code>." in text
    unsaved = page(built={"at": "2026-11-16T21:00:00+00:00", "commit": "abc1234", "dirty": True})
    assert "from the folder at commit <code>abc1234</code>, with uncommitted changes in the folder." in unsaved
    same_minute = top(page(git={**GIT, "first": "2026-11-02T09:00:00+00:00", "last": "2026-11-02T09:00:30+00:00"}))
    assert "The build is 1 commit, made on 2 Nov 2026, 09:00 UTC." in same_minute



PREFIX = "test-walk-the-whole-journey-by-keyboard-alone-chromium-1440x900"


def stand_in(repo: pathlib.Path, exit_code: int, video: bool) -> None:
    """A .venv/bin/python that plays the walk: says what it was given, leaves what a walk leaves, exits as told."""
    python = repo / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("\n".join([
        "#!/bin/sh",
        'echo "$WALK_RECORD|$WALK_FEATURE|$*" > given.txt',
        'printf stray > "$WALK_RECORD/a-stray.webm"',
        f'printf named > "$WALK_RECORD/{PREFIX}.webm"' if video else ":",
        "mkdir -p .scratch/feat/walks",
        f"printf png > .scratch/feat/walks/{PREFIX}-02-fresh.png",
        "echo what the walk printed",
        f"exit {exit_code}", ""]))
    python.chmod(0o755)


@pytest.fixture
def feat(repo):
    """The feature folder of `repo`, holding an earlier run's recording and a screenshot from an hour ago."""
    out = repo / ".scratch" / "feat" / "hand-over"
    out.mkdir(parents=True)
    (out / "recording.webm").write_text("an earlier video")
    (out / "recording.json").write_text(json.dumps({"result": "passed", "commit": "0ld0ld0"}))
    stale = repo / ".scratch" / "feat" / "walks" / f"{PREFIX}-01-stale.png"
    stale.parent.mkdir()
    stale.write_text("png")
    os.utime(stale, (time.time() - 3600, time.time() - 3600))
    return out


@pytest.fixture
def whole(monkeypatch):
    """A build that added or changed no walk of its own, so the standing walk through the whole app is the one recorded."""
    monkeypatch.setattr(handover, "changed_walks", lambda *args: [])


def test_a_walk_that_passes_leaves_its_own_video_this_run_s_screenshots_and_its_record(repo, feat, whole, capsys):
    stand_in(repo, 0, video=True)
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == "passed" and record["returncode"] == 0 and record["walk"] == handover.WALK and record["shows"] == "whole"
    assert record["commit"] == git(repo, "rev-parse", "--short", "HEAD")
    assert (feat / "recording.webm").read_text() == "named"
    assert [shot.name for shot in (feat / "shots").iterdir()] == [f"{PREFIX}-02-fresh.png"]
    scratch, feature, asked = (repo / "given.txt").read_text().strip().split("|")
    assert scratch == str(feat / "recording-tmp") and feature == "feat" and handover.WALK in asked
    assert not (feat / "recording-tmp").exists()
    assert (feat / "walk-output.txt").read_text() == "what the walk printed\n"
    text = (feat / "index.html").read_text()
    assert "<video" in text and re.search(r'pill \w*">(Passed|Not shown to pass)', text) and "The walk-through failed" not in text
    assert '<img src="data:image/png;base64,cG5n" alt="Step 2: fresh">' in text and "stale" not in text
    assert "handover:" not in capsys.readouterr().out


@pytest.mark.parametrize("exit_code, result, words", [(1, "failed", "failed"), (4, "did not run", "did not run")])
def test_a_walk_that_fails_is_said_on_the_page_and_in_one_printed_line_and_the_page_is_still_built(repo, feat, whole, capsys, exit_code, result, words):
    stand_in(repo, exit_code, video=False)
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == result and record["returncode"] == exit_code
    assert not (feat / "recording.webm").exists()
    assert handover.read_recording(feat)["megabytes"] is None
    text = (feat / "index.html").read_text()
    assert f"The walk-through {words}" in text and "The walk-through passed" not in text and "<video" not in text and "0ld0ld0" not in text
    printed = capsys.readouterr().out.splitlines()
    assert printed[-2] == f"handover: the acceptance walk {words}; what it printed is in {feat / 'walk-output.txt'}"
    assert printed[-1] == f"open {feat / 'index.html'}"


def test_a_walk_that_cannot_start_or_is_stopped_leaves_no_earlier_pass_standing(repo, feat, whole, capsys, monkeypatch):
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == "did not run" and record["reason"].startswith("The command that runs it could not start: ")
    assert "The walk-through did not run" in (feat / "index.html").read_text() and not (feat / "recording.webm").exists()
    real = subprocess.run

    def timing_out(command, **more):
        if command[0] == "git":
            return real(command, **more)
        raise subprocess.TimeoutExpired(command, more["timeout"], output=b"half a walk", stderr=None)

    monkeypatch.setattr(handover.subprocess, "run", timing_out)
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == "did not finish" and record["reason"] == "It was stopped after 15 minutes"
    assert (feat / "walk-output.txt").read_text() == "half a walk"
    assert "the acceptance walk did not finish" in capsys.readouterr().out
    assert "It was stopped after 15 minutes." in (feat / "index.html").read_text()


@pytest.mark.parametrize("spoil", ["shared id", "summary", "fates"])
def test_a_record_file_that_stops_the_run_stops_it_before_the_walk_is_recorded(repo, feat, monkeypatch, spoil):
    feature = feat.parent
    if spoil == "shared id":
        write_lines(feature / "findings" / "walker-a.jsonl", [finding("W-1"), finding("W-1")])
    elif spoil == "summary":
        (feature / "hand-over.json").write_text('["not an object"]')
    else:
        (feature / "fates.jsonl").write_text("not json\n")
    monkeypatch.setattr(handover, "record_walk", lambda *args: pytest.fail("the walk was recorded first"))
    with pytest.raises(SystemExit) as stopped:
        handover.main(["feat"], root=repo)
    assert str(stopped.value).startswith("handover: ")
    assert (feat / "recording.webm").read_text() == "an earlier video"


def test_a_small_screenshot_goes_inside_the_page_and_a_very_large_one_stays_a_file_beside_it(tmp_path, monkeypatch):
    (tmp_path / "shots").mkdir()
    (tmp_path / "shots" / "a-01-small.png").write_bytes(b"png")
    (tmp_path / "shots" / "a-02-large one.png").write_bytes(b"p" * 50)
    monkeypatch.setattr(handover, "PICTURE_BYTES", 10)
    assert handover.shots_of(tmp_path) == [{"name": "a-01-small.png", "src": "data:image/png;base64,cG5n"},
                                           {"name": "a-02-large one.png", "src": "shots/a-02-large%20one.png"}]
    assert handover.shots_of(tmp_path / "nowhere") == []


def test_run_as_a_script_the_page_is_opened_in_the_browser_unless_told_not_to(repo, capsys):
    (repo / ".scratch" / "feat").mkdir(parents=True)
    opened = []

    def opens(page):
        opened.append(page)
        return ""
    assert handover.main(["feat", "--no-walk"], root=repo, show=opens) == 0
    page_file = repo / ".scratch" / "feat" / "hand-over" / "index.html"
    assert opened == [page_file.resolve()]
    printed = capsys.readouterr().out.splitlines()
    assert printed[-1] == "The page is open in your browser."
    assert not [line for line in printed if line.startswith("open ")]
    assert handover.main(["feat", "--no-walk", "--no-open"], root=repo, show=opens) == 0 and len(opened) == 1
    assert capsys.readouterr().out.splitlines()[-1] == f"open {page_file}"


def test_a_page_that_could_not_be_opened_says_why_and_ends_on_the_command_that_opens_it(repo, capsys):
    (repo / ".scratch" / "feat").mkdir(parents=True)
    page_file = repo / ".scratch" / "feat" / "hand-over" / "index.html"
    assert handover.main(["feat", "--no-walk"], root=repo, show=lambda page: "`open` ended 1 (not allowed)") == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed[-2:] == ["The page could not be opened in a browser: `open` ended 1 (not allowed). This command opens it:", f"open {page_file}"]

    def broken(page):
        raise OSError("no browser")
    assert handover.main(["feat", "--no-walk"], root=repo, show=broken) == 0
    printed = capsys.readouterr().out.splitlines()
    assert "no browser" in printed[-2] and printed[-1] == f"open {page_file}"


def test_on_a_mac_the_page_goes_to_the_app_that_opens_web_links_by_name(tmp_path):
    import plistlib
    import types
    record = tmp_path / "launch.plist"
    record.write_bytes(plistlib.dumps({"LSHandlers": [{"LSHandlerURLScheme": "mailto", "LSHandlerRoleAll": "com.apple.mail"},
                                                      {"LSHandlerURLScheme": "https", "LSHandlerRoleAll": "com.google.chrome"}]}))
    assert handover.default_browser(record) == "com.google.chrome"
    record.write_bytes(plistlib.dumps({"LSHandlers": [{"LSHandlerURLScheme": "mailto", "LSHandlerRoleAll": "com.apple.mail"}]}))
    assert handover.default_browser(record) == "com.apple.Safari"
    record.write_text("not a property list")
    assert handover.default_browser(record) == "com.apple.Safari"
    assert handover.default_browser(tmp_path / "missing.plist") == "com.apple.Safari"

    ran, asked = [], []
    page = tmp_path / "index.html"

    def run(command, **options):
        ran.append(command)
        return types.SimpleNamespace(returncode=0, stderr="")
    other = lambda address: asked.append(address) or True  # noqa: E731 (a one-line stand-in for the platform's opener)
    assert handover.open_in_browser(page, platform="darwin", run=run, browser=lambda: "com.google.chrome", other=other) == ""
    assert ran == [["open", "-b", "com.google.chrome", str(page)]] and asked == []

    refused = lambda command, **options: types.SimpleNamespace(returncode=1, stderr="not allowed\n")  # noqa: E731 (a one-line stand-in for `open`)
    assert handover.open_in_browser(page, platform="darwin", run=refused, browser=lambda: "com.apple.Safari", other=other) == "`open` ended 1 (not allowed)"

    def missing(command, **options):
        raise FileNotFoundError("open")
    assert "could not run" in handover.open_in_browser(page, platform="darwin", run=missing, other=other)
    assert handover.open_in_browser(page, platform="linux", run=run, other=other) == "" and asked == [page.as_uri()]
    assert handover.open_in_browser(page, platform="linux", run=run, other=lambda address: False) == "no browser was found"


def test_the_walk_helper_records_nothing_unless_it_is_asked_to(monkeypatch):
    from walks import helper
    for value in (None, ""):
        monkeypatch.delenv("WALK_RECORD", raising=False) if value is None else monkeypatch.setenv("WALK_RECORD", value)
        assert helper.launch_options() == {} and helper.context_options(1440, 900) == {}
        assert helper.keep_video(object(), "a-walk") is None


def test_a_build_whose_last_commit_is_already_in_main_is_said_to_be_merged_and_is_not_asked_to_be_accepted(repo):
    start = git(repo, "rev-parse", "main")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature/x")
    facts = handover.git_facts(repo, start, "feature/x")
    assert facts["merged"] is True and facts["commits"] == 3
    git(repo, "branch", "-m", "main", "trunk")
    assert handover.git_facts(repo, start, "feature/x")["merged"] is None
    every = {"walker-a.jsonl": [finding("A"), finding("B")], "review-a.jsonl": [], "early-read-whole.jsonl": []}
    fates = {"A": fate("A")}
    summary = {"what": ["Built."], "so_what": [], "now_what": ["One."]}
    open_, done = (page(files=every, fates=fates, summary=summary, git={**GIT, "merged": merged}) for merged in (False, True))
    assert "before you accept this build" in top(open_) and handover.e(handover.MERGED) not in open_ and handover.e(handover.ACCEPTING) in top(open_)
    assert "accept this build" not in done and "accept the build" not in done and handover.e(handover.ACCEPTING) not in done
    assert (f'</strong></p><p class="merged"><span class="pill">Already merged</span> {handover.e(handover.MERGED)}</p>' in top(done)
            and done.count(handover.e(handover.MERGED)) == 1)
    assert handover.MERGED_HOW.startswith("This build is already merged: this page found its last commit in main")
    assert done.count(handover.e(handover.MERGED_HOW)) == 1 and "already merged" not in open_.lower()
    count = len(things(done))
    assert f"{count} things to look at in this build, which is already merged</p>" in top(done)
    assert "<p>To ask for any of this, tell the agent you are working with (a new session opened in this project will do).</p>" in top(done)
    assert [(tone, href, what) for tone, href, what, _ in things(done)] == [(tone, href, what) for tone, href, what, _ in things(open_)]
    assert any(why.endswith("treat it as open. Ask what became of it before you accept this build.") for *_, why in things(open_))
    assert any(why.endswith("treat it as open. Ask what became of it.") for *_, why in things(done))
    assert handover.headline_said(0, True) == "This page found nothing that needs a second look in this build, which is already merged"
    settled = {"git": {**GIT, "merged": True}, "runs": handover.run_facts(GREEN_RUN, "feature/x"), "recording": WALKED,
               "files": every, "fates": {"A": fate("A"), "B": fate("B")}}
    green = top(page(summary={"what": [], "so_what": [], "now_what": ["One."]}, **settled))
    assert '<p class="headline green">' in green and "To accept the build" not in green and "judge it: read it.</a>" in green


def test_the_list_says_how_far_the_walk_through_s_commit_is_from_the_build_s_last_commit(repo):
    first, second, tip = (git(repo, "rev-parse", "--short", ref) for ref in ("feature/x~2", "feature/x~1", "feature/x"))
    assert handover.commit_gap(repo, tip, "feature/x") == (0, 0) and handover.commit_gap(repo, first, "feature/x") == (0, 2)
    git(repo, "checkout", "-q", "-b", "later", "feature/x")
    (repo / "more.py").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "later")
    later = git(repo, "rev-parse", "--short", "later")
    assert handover.commit_gap(repo, later, "feature/x") == (1, 0)
    assert handover.commit_gap(repo, "0123456789", "feature/x") is None and handover.commit_gap(repo, None, "feature/x") is None
    walk = lambda commit, gap: things(page(recording={**RECORDING, "commit": commit, "dirty": False}, git=GIT, walk_gap=gap))[0][3]  # noqa: E731 (a one-line helper local to this function)
    assert walk(later, (1, 0)) == (f"The walk-through passed, but on commit {later}, not the build&#x27;s last commit (abc1234). Commit {later} holds the whole build and 1 commit "
                                   "made after it, which is not part of the build, so the app the walk-through used may differ from the finished build. "
                                   "Ask for it to be run again on the build&#x27;s last commit.")
    assert f"Commit {first} is 2 commits before the build&#x27;s last commit, so the walk-through did not use the last 2 commits of the build." in walk(first, (0, 2))
    assert "so the walk-through did not use that last commit of the build." in walk(second, (0, 1))
    assert f"Commit {first} is on another line of work: it has 3 commits the build does not have, and lacks the build&#x27;s last 2 commits." in walk(first, (3, 2))
    assert "holds the whole build and 13 commits made after it, which are not part of the build, so" in walk(later, (13, 0))
    assert " is on another line" not in walk(first, None) and " before the build" not in walk(first, None)
    assert "Commit abc1234 is" not in page(recording={**RECORDING, "commit": "abc1234", "dirty": False}, git=GIT, walk_gap=(0, 0))


def test_merged_is_judged_against_main_as_last_fetched_when_the_folder_has_one(repo):
    start = git(repo, "rev-parse", "main")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature/x")
    assert handover.git_facts(repo, start, "feature/x")["merged"] is True
    git(repo, "update-ref", "refs/remotes/origin/main", start)
    assert handover.git_facts(repo, start, "feature/x")["merged"] is False
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    assert handover.git_facts(repo, start, "feature/x")["merged"] is True


def test_main_carries_the_merge_and_the_walk_through_s_distance_from_git_onto_the_page(repo, capsys):
    start, before = git(repo, "rev-parse", "main"), git(repo, "rev-parse", "--short", "feature/x~1")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature/x")
    out = repo / ".scratch" / "feat" / "hand-over"
    out.mkdir(parents=True, exist_ok=True)
    (out / "recording.json").write_text(json.dumps({**RECORDING, "commit": before, "dirty": False}))
    assert handover.main(["feat", "--base", start, "--tip", "feature/x", "--branch", "feature/x", "--no-walk", "--no-open"], root=repo) == 0
    said = [line for line in capsys.readouterr().out.splitlines() if line.startswith("The page's headline: ")][0]
    built = (out / "index.html").read_text()
    assert said.endswith("in this build, which is already merged") and handover.e(said.removeprefix("The page's headline: ")) in built
    assert handover.e(handover.MERGED) in built and "accept this build" not in built
    assert f"Commit {before} is 1 commit before the build&#x27;s last commit, so the walk-through did not use that last commit of the build." in built



OWN = {"shows": "build", "at": "2026-11-16T21:00:00+00:00", "commit": "abc1234", "dirty": False, "result": "passed", "minutes": 0.6,
       "megabytes": 2.0, "walks": [
           {"walk": "walks/test_z_walk.py::test_walk_a_removed_name_reads_removed[1440x900]", "result": "passed",
            "title": "A removed name is marked as removed", "legend": "A trial drops one name. The row should list it under Removed.",
            "clips": ["test-walk-a-removed-name-reads-removed-1440x900.webm"]},
           {"walk": "walks/test_z_walk.py::test_walk_a_comma_stays_one_name[1440x900]", "result": "passed",
            "title": "A name with a comma stays one name.", "legend": "A name holds a comma. It should read as one entry.",
            "clips": ["test-walk-a-comma-stays-one-name-1440x900.webm", "test-walk-a-comma-stays-one-name-1440x900-page2.webm"]}]}
OWN_SHOTS = ["test-walk-a-comma-stays-one-name-1440x900-01-comma.png", "test-walk-a-removed-name-reads-removed-1440x900-01-folded.png",
             "test-walk-a-removed-name-reads-removed-1440x900-02-unfolded.png"]


def recording_section(text: str) -> str:
    return text[text.index('<section id="recording">'):text.index("</section>", text.index('<section id="recording">'))]


def test_a_walk_through_of_what_the_build_changed_is_one_recording_in_parts_each_under_the_builder_s_words():
    text = page(recording=OWN, shots=OWN_SHOTS, git=GIT)
    section = recording_section(text)
    assert tile(text, "#recording") == ("green", "Passed on the build&#x27;s last commit")
    assert "A recording of what this build changed, in 2 parts. Ran for 0.6 minutes, on commit <code>abc1234</code>" in top(text)
    assert "<h2>The walk-through: what this build changed</h2>" in section
    assert ("One recording in 2 parts. Each part shows one thing this build changed, in a real browser, and the note under each part "
            "says what is being tested.</p>") in section
    assert ('<ol class="parts"><li><a href="#part-1" data-part="0" data-frame="0">A removed name is marked as removed</a></li>'
            '<li><a href="#part-2" data-part="1" data-frame="2">A name with a comma stays one name</a></li></ol>') in section
    legends = re.findall(r"<figcaption>(.*?)</figcaption>", section)
    one = "<b>Part 1 of 2. A removed name is marked as removed.</b> A trial drops one name. The row should list it under Removed."
    two = "<b>Part 2 of 2. A name with a comma stays one name.</b> A name holds a comma. It should read as one entry."
    assert legends == [f'{one} <span class="soft">Picture 1 of 2 from this part.</span>', f'{one} <span class="soft">Picture 2 of 2 from this part.</span>',
                       f'{two} <span class="soft">Picture 1 of 1 from this part.</span>', one, two]
    assert 'alt="Part 1 of 2. A removed name is marked as removed. Picture 2 of 2 from this part."' in section
    assert section.count("<video") == 3 and 'src="recording.webm"' not in text and 'tabindex="-1" data-film>' in section
    assert ('<figure class="clip" id="part-1" data-part="0"><video controls preload="metadata" '
            'src="clips/test-walk-a-removed-name-reads-removed-1440x900.webm" data-frame="0">') in section
    assert 'src="clips/test-walk-a-comma-stays-one-name-1440x900-page2.webm" data-frame="2">' in section
    assert "The title and the note on each part are the builder&#x27;s words" not in section
    assert "The title and the note on each part are the builder's words. This page copied them as written" in section
    assert handover.e(handover.TERMS_OWN) in text and handover.e(handover.TERMS) not in text
    assert "from start to finish" not in text and "whole journey" not in text
    assert handover.e(handover.TERMS) in page(recording=RECORDING) and handover.e(handover.TERMS_OWN) not in page(recording=RECORDING)


def test_a_test_s_name_is_shown_only_behind_the_fold_that_says_which_test_each_part_runs():
    text = page(recording={**OWN, "left_out": ["walks/test_q_walk.py::test_walk_other"]}, shots=OWN_SHOTS, git=GIT)
    section = recording_section(text)
    fold = section[section.index('<details class="record">'):]
    assert ("<summary>The browser test behind each part</summary>" in fold
            and "<li>Part 2: <code>walks/test_z_walk.py::test_walk_a_comma_stays_one_name[1440x900]</code></li>" in fold
            and "<li>Changed by the build and left out of the recording: <code>walks/test_q_walk.py::test_walk_other</code></li>" in fold)
    shown = re.sub(r'(src|alt|href)="[^"]*"', "", section[:section.index('<details class="record">')])
    assert "test_walk" not in shown and "test-walk" not in shown and "::" not in shown and "1440x900" not in shown
    assert "The build changed 1 other browser test and left it out of this recording." in shown
    assert "left out of this recording" not in page(recording=OWN, shots=OWN_SHOTS, git=GIT)


def test_a_walk_through_of_what_the_build_changed_that_did_not_pass_says_how_each_part_ended():
    walks = [{**OWN["walks"][0]}, {**OWN["walks"][1], "result": "failed"},
             {"walk": "walks/test_z_walk.py::test_walk_never_reached[1440x900]", "title": "The list empties", "legend": "It should say none.", "result": None, "clips": []}]
    text = page(recording={**OWN, "result": "failed", "walks": walks}, shots=OWN_SHOTS, git=GIT)
    assert tile(text, "#recording") == ("red", "Failed") and not drawn_green(text)
    assert "One recording in 3 parts." in text and "The run did not pass: each part says how it ended.</p>" in text
    assert 'should list it under Removed. <span class="soft">This part passed.</span></figcaption>' in text
    assert 'It should read as one entry. <span class="soft">This part failed.</span></figcaption>' in text
    assert ('<figure class="clip" id="part-3" data-part="2"><p>This part left no video.</p><figcaption><b>Part 3 of 3. The list empties.</b> '
            'It should say none. <span class="unknown">How this part ended was not recorded.</span></figcaption>') in text
    assert "So this page does not show that what the build changed works in a browser." in top(text) and "from start to finish" not in text
    assert "This part passed." not in page(recording=OWN, shots=OWN_SHOTS, git=GIT)
    silent = page(recording={**OWN, "megabytes": None}, shots=OWN_SHOTS, git=GIT)
    assert "2 parts, in pictures only: the walk-through left no video." in silent and "<video" not in silent and "data-film" not in recording_section(silent)


def test_a_part_recorded_without_the_builder_s_words_says_so_and_never_shows_the_test_s_name():
    bare = [{key: value for key, value in walk.items() if key not in ("title", "legend")} for walk in OWN["walks"]]
    section = recording_section(page(recording={**OWN, "walks": bare}, shots=OWN_SHOTS, git=GIT))
    assert "<b>Part 1 of 2. A part the builder gave no title.</b> The builder wrote no note saying what this part tests." in section
    assert "Removed name" not in section and "removed name reads" not in section.split('<details class="record">')[0].replace("test-walk-a-removed-name-reads", "")


def test_the_standing_walk_is_said_to_be_a_stand_in_only_when_the_build_had_no_walk_of_its_own():
    said = "This build added or changed no browser test of its own, so this is the standing walk through the whole app."
    assert said in page(recording={**RECORDING, "shows": "whole"}) and said not in page(recording=RECORDING)
    assert "<h2>The walk-through, in pictures</h2>" in page(recording=RECORDING)


def test_the_parts_of_the_walk_through_are_the_changed_walks_the_summary_lists_in_its_order(tmp_path):
    changed = [("walks/test_a_walk.py", "test_walk_one"), ("walks/test_a_walk.py", "test_walk_two"), ("walks/test_b_walk.py", "test_walk_one")]
    path = tmp_path / "hand-over.json"

    def entry(test, title="Two.", legend="It should say two."):
        return {"test": test, "title": title, "legend": legend}

    parts, left = handover.walk_parts({"walk_through": [entry("test_walk_two"), entry("walks/test_b_walk.py::test_walk_one", " One ")]}, changed, path)
    assert parts == [{"test": ("walks/test_a_walk.py", "test_walk_two"), "title": "Two.", "legend": "It should say two."},
                     {"test": ("walks/test_b_walk.py", "test_walk_one"), "title": "One", "legend": "It should say two."}]
    assert left == ["walks/test_a_walk.py::test_walk_one"]
    assert handover.walk_parts(None, [], path) == ([], []) and handover.walk_parts({"what": ["Built."]}, [], path) == ([], [])
    for summary, said in (
            (None, "has no walk_through"), ({"what": ["Built."]}, "this build added or changed 3 browser tests"),
            ({"walk_through": [entry("test_walk_one")]}, "test_walk_one is the name of more than one of them: write it as file::name"),
            ({"walk_through": [entry("test_walk_gone")]}, "test_walk_gone is not a browser test this build added or changed"),
            ({"walk_through": [entry("test_walk_two"), entry("walks/test_a_walk.py::test_walk_two")]}, "walk_through entry 2: walks/test_a_walk.py::test_walk_two is listed twice")):
        with pytest.raises(SystemExit) as stopped:
            handover.walk_parts(summary, changed, path)
        assert said in str(stopped.value) and "hand-over.json" in str(stopped.value) and "\n  walks/test_b_walk.py::test_walk_one" in str(stopped.value)
    with pytest.raises(SystemExit) as stopped:
        handover.walk_parts({"walk_through": [entry("test_walk_two")]}, [], path)
    assert "(none)" in str(stopped.value)


def test_a_part_s_title_and_legend_are_refused_when_missing_too_long_or_a_name_from_the_code(tmp_path):
    good = {"test": "test_walk_two", "title": "A removed name is marked as removed", "legend": "x" * handover.LEGEND_LENGTH}
    (tmp_path / "hand-over.json").write_text(json.dumps({"what": ["Built."], "walk_through": [good]}), encoding="utf-8")
    assert handover.read_summary(tmp_path)["walk_through"] == [good]
    for wrong, said in (
            ({"walk_through": "one"}, "walk_through must be a list of objects, each with a test, a title and a legend"),
            ({"walk_through": [{**good, "legend": " "}]}, "walk_through must be a list of objects"),
            ({"walk_through": [{"test": "test_walk_two", "title": "No legend"}]}, "walk_through must be a list of objects"),
            ({"walk_through": [good, {**good, "title": "x" * (handover.TITLE_LENGTH + 1)}]}, f"walk_through entry 2: the title is {handover.TITLE_LENGTH + 1} characters"),
            ({"walk_through": [{**good, "legend": "x" * (handover.LEGEND_LENGTH + 1)}]}, f"the legend is {handover.LEGEND_LENGTH + 1} characters"),
            ({"walk_through": [{**good, "title": "test_walk_a_removed_name reads removed"}]}, "the title holds a name from the code (test_walk_a_removed_name)"),
            ({"walk_through": [{**good, "legend": "Runs walks/test_a.py::test_x in a browser."}]}, "the legend holds a name from the code (walks/test_a.py::test_x)")):
        (tmp_path / "hand-over.json").write_text(json.dumps(wrong), encoding="utf-8")
        with pytest.raises(SystemExit) as stopped:
            handover.read_summary(tmp_path)
        assert said in str(stopped.value) and "hand-over.json" in str(stopped.value) and "\n" not in str(stopped.value)


def test_the_walks_a_build_added_or_changed_are_the_test_functions_with_a_line_of_their_own_changed(tmp_path):
    root = tmp_path / "repo"
    (root / "walks").mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    (root / "walks" / "helper.py").write_text("def test_looks_like_a_walk():\n    pass\n")
    (root / "walks" / "test_a_walk.py").write_text(
        "def open_it():\n    return 1\n\n\ndef test_walk_kept():\n    open_it()\n# a note\n\n\n"
        "def test_walk_edited():\n    open_it()\n    assert 1\n\n\ndef test_walk_trimmed():\n    open_it()\n    assert 1\n    assert 2\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    git(root, "checkout", "-q", "-b", "feature/x")
    (root / "walks" / "helper.py").write_text("def test_looks_like_a_walk():\n    return 2\n")
    (root / "walks" / "test_a_walk.py").write_text(
        "def open_it():\n    return 2\n\n\ndef test_walk_kept():\n    open_it()\n\n\n"
        "def test_walk_edited():\n    open_it()\n    assert 3\n\n\ndef test_walk_trimmed():\n    open_it()\n    assert 2\n")
    (root / "walks" / "test_b_walk.py").write_text(
        "import pytest\n\n\ndef not_a_test():\n    pass\n\n\n@pytest.mark.slow\ndef test_walk_new():\n    pass\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "build")
    assert handover.changed_walks(root, "main", "HEAD") == [
        ("walks/test_a_walk.py", "test_walk_edited"), ("walks/test_a_walk.py", "test_walk_trimmed"), ("walks/test_b_walk.py", "test_walk_new")]
    assert handover.changed_walks(root, "main", "main") == [] and handover.changed_walks(root, "no-such-branch", "HEAD") == []


def test_each_changed_walk_is_recorded_once_at_one_window_size(tmp_path):
    tests = [("walks/test_a_walk.py", "test_walk_edited"), ("walks/test_acc.py", "test_j"), ("walks/test_b_walk.py", "test_plain"),
             ("walks/test_b_walk.py", "test_not_collected")]
    bare = [f"{path}::{name}" for path, name in tests]
    assert handover.walk_ids(tmp_path, tests) == bare and handover.walk_ids(tmp_path, []) == []
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("\n".join(["#!/bin/sh", "cat <<'END'",
                                 "walks/test_a_walk.py::test_walk_edited[1024x768]", "walks/test_a_walk.py::test_walk_edited[1440x900]",
                                 "walks/test_acc.py::test_j[webkit-1440x900]", "walks/test_acc.py::test_j[chromium-1024x768]",
                                 "walks/test_acc.py::test_j[chromium-1440x900]", "walks/test_b_walk.py::test_plain", "", "6 tests collected in 0.01s",
                                 "END", ""]))
    python.chmod(0o755)
    assert handover.walk_ids(tmp_path, tests) == ["walks/test_a_walk.py::test_walk_edited[1440x900]", "walks/test_acc.py::test_j[chromium-1440x900]",
                                                  "walks/test_b_walk.py::test_plain", "walks/test_b_walk.py::test_not_collected"]


def test_a_build_with_walks_of_its_own_gets_those_recorded_and_not_the_whole_app(repo, feat, capsys):
    (repo / "walks" / "test_new_walk.py").write_text("def test_walk_one():\n    pass\n\n\ndef test_walk_two():\n    pass\n")
    git(repo, "add", "walks")
    git(repo, "commit", "-q", "-m", "two walks")
    one, two = "test-walk-one-1440x900", "test-walk-two-1440x900"
    python = repo / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("\n".join([
        "#!/bin/sh",
        'case "$*" in *--collect-only*)',
        "  echo 'walks/test_new_walk.py::test_walk_one[1440x900]'; echo 'walks/test_new_walk.py::test_walk_one[1024x768]'",
        "  echo 'walks/test_new_walk.py::test_walk_two[1440x900]'; exit 0;; esac",
        'echo "$WALK_SLOW_MO|$*" > given.txt',
        'for a in "$@"; do case "$a" in --junitxml=*) J="${a#--junitxml=}";; esac; done',
        f'printf first > "$WALK_RECORD/{one}.webm"; printf second > "$WALK_RECORD/{one}-page2.webm"; printf third > "$WALK_RECORD/{two}.webm"',
        'printf stray > "$WALK_RECORD/a-stray.webm"',
        "mkdir -p .scratch/feat/walks",
        f"printf png > .scratch/feat/walks/{one}-01-opened.png; printf png > .scratch/feat/walks/{two}-01-broke.png",
        """printf '<testsuites><testsuite><testcase classname="walks.test_new_walk" name="test_walk_one[1440x900]"/>'"""
        """'<testcase classname="walks.test_new_walk" name="test_walk_two[1440x900]"><failure/></testcase></testsuite></testsuites>' > "$J\"""",
        "echo what the walks printed",
        "exit 1", ""]))
    python.chmod(0o755)
    with pytest.raises(SystemExit) as stopped:
        handover.main(["feat"], root=repo)
    assert "has no walk_through" in str(stopped.value) and "\n  walks/test_new_walk.py::test_walk_two" in str(stopped.value)
    assert not (repo / "given.txt").exists() and (feat / "recording.webm").exists()
    summary = {"what": ["Built."], "walk_through": [
        {"test": "test_walk_two", "title": "The second thing", "legend": "The list should say two."},
        {"test": "walks/test_new_walk.py::test_walk_one", "title": "The first thing", "legend": "The list should say one."}]}
    (repo / ".scratch" / "feat" / "hand-over.json").write_text(json.dumps(summary), encoding="utf-8")
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["shows"] == "build" and record["result"] == "failed" and "walk" not in record
    assert record["walks"] == [
        {"walk": "walks/test_new_walk.py::test_walk_two[1440x900]", "title": "The second thing", "legend": "The list should say two.",
         "result": "failed", "clips": [f"{two}.webm"]},
        {"walk": "walks/test_new_walk.py::test_walk_one[1440x900]", "title": "The first thing", "legend": "The list should say one.",
         "result": "passed", "clips": [f"{one}-page2.webm", f"{one}.webm"]}]
    assert record["left_out"] == ["walks/test_walk.py::test_walk_it"]
    assert sorted(clip.name for clip in (feat / "clips").iterdir()) == [f"{one}-page2.webm", f"{one}.webm", f"{two}.webm"]
    assert not (feat / "recording.webm").exists() and not (feat / "recording-tmp").exists()
    assert sorted(shot.name for shot in (feat / "shots").iterdir()) == [f"{one}-01-opened.png", f"{two}-01-broke.png"]
    asked = (repo / "given.txt").read_text()
    assert asked.startswith(f"{handover.OWN_SLOW_MO}|")
    assert "test_walk_one[1440x900]" in asked and "test_walk_two[1440x900]" in asked and "1024x768" not in asked and handover.WALK not in asked
    assert "test_walk_it" not in asked
    assert handover.read_recording(feat)["megabytes"] is not None
    text = (feat / "index.html").read_text()
    assert "The walk-through failed" in text and f'src="clips/{two}.webm"' in text and 'src="recording.webm"' not in text
    assert ('<b>Part 1 of 2. The second thing.</b> The list should say two. <span class="soft">Picture 1 of 1 from this part.</span>' in text
            and '<b>Part 1 of 2. The second thing.</b> The list should say two. <span class="soft">This part failed.</span>' in text)
    assert "The build changed 1 other browser test and left it out of this recording." in text
    printed = capsys.readouterr().out.splitlines()
    assert "Recording the walk-through, 2 parts:" in printed
    assert printed[-2] == f"handover: the walk-through failed; what it printed is in {feat / 'walk-output.txt'}"



SETTLED = {"git": GIT, "runs": handover.run_facts(GREEN_RUN, "feature/x"), "recording": WALKED}
LATE = "Fixed after the last review"


def reviews(first, recheck=None) -> dict:
    """The report files of a build whose three reviews were all made; `recheck` None is a build with no re-check report."""
    files = {"walker-a.jsonl": list(first), "review-a.jsonl": [], "early-read-whole.jsonl": []}
    return files if recheck is None else {**files, "walker-a-recheck.jsonl": list(recheck)}


def test_a_fix_for_an_issue_the_re_check_found_is_counted_as_made_after_the_last_review_and_is_not_a_thing_to_look_at():
    files = reviews([finding("A"), finding("B")], [finding("C", round="recheck"), finding("D", round="recheck")])
    late = page(files=files, fates={**{i: fate(i) for i in "ABC"}, "D": fate("D", "left", why="Rare.")}, **SETTLED)
    said = "1 of the 3 fixes is for an issue the re-check found. The re-check is the last review a build gets, so no review read this fix."
    assert chip(late, "", "#finders", f"{LATE}: 1")
    assert said in late[late.index('<section id="finders">'):]
    assert [what for _, _, what, _ in things(late)] == ["The record marks 1 issue as left unfixed"]
    all_fixed = top(page(files=reviews([finding("A")], [finding("B", round="recheck"), finding("C", round="recheck")]),
                         fates={i: fate(i) for i in "ABC"}, **SETTLED))
    assert '<p class="headline green">' in all_fixed
    assert ("2 of the 3 fixes are for issues the re-check found. The re-check is the last review a build gets, so no review read these 2 fixes."
            in all_fixed)


def test_fixes_made_before_a_re_check_that_was_read_are_not_counted_as_made_after_the_last_review():
    early = page(files=reviews([finding("A"), finding("B")], []), fates={i: fate(i) for i in "AB"}, **SETTLED)
    assert LATE not in early and "no review read" not in early
    assert LATE not in page(files=reviews([finding("A")], [finding("B", round="recheck")]),
                            fates={"A": fate("A"), "B": fate("B", "not-a-defect", why="By design.")}, **SETTLED)


def test_with_no_re_check_report_every_fix_is_counted_as_made_after_the_last_review():
    unread = page(files=reviews([finding("A"), finding("B"), finding("C")]),
                  fates={"A": fate("A"), "B": fate("B", check=""), "C": fate("C", "left", why="Rare.")}, **SETTLED)
    assert chip(unread, "", "#finders", f"{LATE}: 2")
    assert ("This page read no re-check report, so nothing on record shows that one was made. "
            "Without one, nothing on record shows that a review read the 2 fixes.") in unread
    assert "a review read the fix." in page(files=reviews([finding("A")]), fates={"A": fate("A")}, **SETTLED)
    assert LATE not in page(files=reviews([finding("A")]), fates={"A": fate("A", "left", why="Rare.")}, **SETTLED)


DURING = {**GIT, "first": "2026-11-17T22:03:23Z", "last": "2026-11-17T23:40:00Z"}
STRAY = {"pid": 11143, "started": "2026-11-17T22:03:50+00:00", "ports": [51234]}
OWNERS = {"pid": 60675, "started": "2026-11-17T09:00:00+00:00", "ports": [8765]}
RUNNING = "Programs of this project still running"


def test_a_program_of_this_project_started_during_the_build_and_still_listening_is_a_thing_to_look_at():
    settled = {**SETTLED, "git": DURING}
    left = page(files=reviews([]), copies=[OWNERS, STRAY], **settled)
    assert things(left) == [("amber", "#facts", "A program the build may have started is still running",
                             "It is running this project&#x27;s code, was started at 17 Nov 2026, 22:03 UTC, after the build&#x27;s first commit, and is "
                             "still listening on port 51234 (process 11143). The build&#x27;s tests start copies of the app and should stop each "
                             "one. This page cannot tell whether the build started this one or you did. "
                             "If you did not start it, stop it: type kill 11143 in a terminal.")]
    assert "1 thing to look at before you accept this build" in top(left)
    assert "1 started during the build (process 11143, port 51234); 1 started before the build" in row(left, RUNNING)
    two = things(page(files=reviews([]), copies=[STRAY, {"pid": 11150, "started": "2026-11-17T22:30:00+00:00", "ports": [8765, 9000]}], **settled))
    assert two[0][2] == "2 programs the build may have started are still running"
    assert "process 11143, started 17 Nov 2026, 22:03 UTC, port 51234; process 11150, started 17 Nov 2026, 22:30 UTC, ports 8765 and 9000" in two[0][3]
    assert two[0][3].endswith("If you did not start them, stop them: type kill 11143 11150 in a terminal.")


def test_a_program_running_since_before_the_build_is_not_a_thing_to_look_at_and_what_was_not_looked_for_is_unknown():
    settled = {**SETTLED, "git": DURING}
    before = page(files=reviews([]), copies=[OWNERS], **settled)
    assert things(before) == [] and "1 started before the build" in row(before, RUNNING)
    assert things(page(files=reviews([]), copies=[], **settled)) == []
    assert row(page(files=reviews([]), copies=[], **settled), RUNNING) == "none"
    unasked = page(files=reviews([]), copies=None, **settled)
    assert things(unasked) == [] and row(unasked, RUNNING) == '<span class="unknown">unknown</span>'
    merged = {**settled, "git": {**DURING, "merged": True, "merged_at": "2026-11-18T08:00:00Z"}}
    later = {"pid": 70000, "started": "2026-11-18T12:25:43+00:00", "ports": [8765]}
    after = page(files=reviews([]), copies=[later, STRAY], **merged)
    assert [what for _, _, what, _ in things(after)] == ["A program the build may have started is still running"]
    assert row(after, RUNNING) == "1 started during the build (process 11143, port 51234); 1 started after the build was merged"
    assert things(page(files=reviews([]), copies=[later], **merged)) == []
    undated = page(files=reviews([]), copies=[STRAY], **SETTLED)
    assert things(undated) == [] and "1 running; this page cannot tell whether before or during the build" in row(undated, RUNNING)


SERVE = "import socket, time; s = socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(); print(s.getsockname()[1], flush=True); time.sleep(120)"


def listening(folder: pathlib.Path, *command: str) -> tuple[subprocess.Popen, int]:
    """A program started in `folder` that listens on a free port of this computer: (the process, the port)."""
    process = subprocess.Popen([sys.executable, *command], cwd=folder, stdout=subprocess.PIPE, text=True)
    return process, int(process.stdout.readline())


def test_this_project_s_programs_still_listening_are_found_on_this_computer_with_their_ports_and_start_times(tmp_path, monkeypatch):
    monkeypatch.setenv("COLUMNS", "80")
    project, elsewhere = tmp_path / ("a-project-whose-folder-has-a-long-name-" * 3), tmp_path / "elsewhere"
    (project / "walks").mkdir(parents=True)
    elsewhere.mkdir()
    for script in (project / "run.py", project / "walks" / "serve.py", elsewhere / "run.py"):
        script.write_text(SERVE, encoding="utf-8")
    app = listening(project, "run.py")
    stray = listening(elsewhere, str(project / "walks" / "serve.py"))
    other = listening(elsewhere, "run.py")
    lodger = listening(project, "-c", SERVE)
    try:
        found = handover.listeners(project)
        assert [(copy["pid"], copy["ports"]) for copy in found] == [(app[0].pid, [app[1]]), (stray[0].pid, [stray[1]])]
        age = time.time() - handover.moment(found[0]["started"]).timestamp()
        assert -2 < age < 120
    finally:
        for process, _ in (app, stray, other, lodger):
            process.terminate()
            process.wait()
    assert handover.listeners(project) == []


def test_a_computer_that_cannot_be_asked_gives_unknown_not_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert handover.listeners(tmp_path) is None


def test_the_script_run_for_real_puts_a_program_started_during_the_build_in_its_headline_count(repo, capsys, monkeypatch):
    write_lines(repo / ".scratch" / "feat" / "findings" / "walker-a.jsonl", [])
    asked = []
    monkeypatch.setattr(handover, "listeners", lambda root: asked.append(root) or [{"pid": 7, "started": "2026-11-02T09:30:00+00:00", "ports": [8765]}])
    assert handover.main(["feat", "--base", "main", "--tip", "feature/x", "--branch", "feature/x", "--no-walk"], root=repo) == 0
    text = (repo / ".scratch" / "feat" / "hand-over" / "index.html").read_text(encoding="utf-8")
    assert asked == [repo] and "A program the build may have started is still running" in top(text)
    assert "type kill 7 in a terminal" in top(text)


def test_git_gives_the_time_a_build_was_merged_and_none_for_a_build_that_is_not(repo):
    start = git(repo, "rev-parse", "main")
    assert handover.git_facts(repo, start, "feature/x")["merged_at"] is None
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature/x", when="2026-11-03T08:00:00+00:00")
    (repo / "later.txt").write_text("later\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "later work on main", when="2026-11-04T08:00:00+00:00")
    assert handover.when(handover.git_facts(repo, start, "feature/x")["merged_at"]) == "3 Nov 2026, 08:00 UTC"


def test_a_build_main_was_moved_forward_to_was_merged_when_its_last_commit_was_made(repo):
    start = git(repo, "rev-parse", "main")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "feature/x")
    assert handover.when(handover.git_facts(repo, start, "feature/x")["merged_at"]) == "2 Nov 2026, 10:30 UTC"



STEADY = {"git": GIT, "runs": handover.run_facts(GREEN_RUN, "feature/x"), "recording": WALKED,
           "files": {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}}
WOBBLY = "walks/test_find_trials_walk.py::test_a_filter_reaches_the_registry[1440x900]"


def flaky_line(*nodeids, at="2026-11-16T10:00:00Z", tip="abc1234"):
    """One line of the walk runner's record, as walks/run_walks.py writes it at the end of a run of the browser tests."""
    return {"at": at, "tip": tip, "flaky": list(nodeids)}


def test_a_browser_test_that_failed_with_the_others_and_passed_alone_is_counted_among_the_things_to_look_at():
    text = page(**STEADY, flaky=[flaky_line(WOBBLY)])
    assert '<p class="headline amber">' in top(text) and "1 thing to look at before you accept this build" in top(text)
    assert [thing[:3] for thing in things(text)] == [
        ("amber", "#facts", "1 browser test failed when run with the others and passed when run alone")]


def test_each_flaky_browser_test_is_named_in_words_under_the_fold_and_no_name_from_the_code_is_in_view():
    other = "walks/test_trial_page_walk.py::test_notes_survive_a_reload[1024x768]"
    runs = handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z"), run("feature/x", "green", "2026-11-16T11:00:00Z")], "feature/x")
    text = page(**{**STEADY, "runs": runs}, flaky=[flaky_line(WOBBLY, at="2026-11-16T09:59:58Z"),
                                                    flaky_line(WOBBLY, other, at="2026-11-16T11:00:00Z")])
    (tone, href, what, shown, folded), = looks(text)
    assert what == "2 browser tests failed when run with the others and passed when run alone"
    assert shown == "Ask for each to be looked into before you accept this build."
    assert folded.startswith(
        f"The tests: A filter reaches the registry, at 1440 by 900 pixels ({WOBBLY}), in the runs of 16 Nov 2026, 10:00 UTC and "
        f"16 Nov 2026, 11:00 UTC; Notes survive a reload, at 1024 by 768 pixels ({other}), in the run of 16 Nov 2026, 11:00 UTC. "
        "Run alone, each passed, so the automated checks counted them as passed.")
    assert "feat/walks/flaky.jsonl" in folded
    in_view = re.sub(r"<details>.*?</details>", "", top(text), flags=re.S)
    assert not handover.CODE_NAME.search(re.sub(r"<[^>]*>", " ", in_view.split('<ol class="look">')[1]).split("</ol>")[0])
    assert handover.walk_said("walks/test_acceptance_walk.py::test_walk_alone[chromium-1440x900]") == "Walk alone, in chromium, at 1440 by 900 pixels"


def test_with_no_flaky_browser_test_recorded_the_page_is_the_page_built_without_the_record():
    unread = page(**STEADY)
    assert page(**STEADY, flaky=[flaky_line()]) == unread
    assert page(**STEADY, flaky=[flaky_line(), flaky_line(WOBBLY, tip="fff9999")]) == unread
    assert page(**STEADY, flaky=[flaky_line(), flaky_line(WOBBLY, at="2026-11-16T11:00:00Z")]) == unread
    no_walks = handover.run_facts([run("feature/x", "green", names=("unit",))], "feature/x")
    assert page(**{**STEADY, "runs": no_walks}, flaky=[]) == page(**{**STEADY, "runs": no_walks})


MISSING = ("The record of which browser tests failed with the others and passed alone is missing for the last run of the "
           "browser tests, so this page cannot say whether any did.")


def test_the_record_is_called_missing_only_when_the_builds_last_run_of_the_browser_tests_has_no_line_in_it():
    assert MISSING in top(page(**STEADY, flaky=[]))
    assert MISSING in top(page(**STEADY, flaky=[flaky_line(at="2026-11-15T10:00:00Z")]))
    assert "0 browser tests" not in page(**STEADY, flaky=[])
    assert things(page(**STEADY, flaky=[])) == []
    earlier = handover.run_facts([run("feature/x", "green", "2026-11-15T10:00:00Z"), run("feature/x", "green")], "feature/x")
    assert MISSING not in page(**{**STEADY, "runs": earlier}, flaky=[flaky_line()])


def test_the_page_reads_the_walk_runners_record_from_the_features_walks_folder(tmp_path):
    import walks.run_walks as run_walks
    assert handover.FLAKY_RECORD == run_walks.FLAKY_RECORD
    assert handover.read_flaky(tmp_path) == []
    write_lines(tmp_path / "walks" / handover.FLAKY_RECORD, [flaky_line(WOBBLY)])
    assert handover.read_flaky(tmp_path) == [flaky_line(WOBBLY)]


def test_the_script_puts_a_flaky_browser_test_from_the_features_record_on_the_page(repo):
    feature = repo / ".scratch" / "feat"
    write_lines(feature / "findings" / "review-a.jsonl", [])
    write_lines(repo / ".checks" / "runs.jsonl", [run("feature/x", "green")])
    handover.main(["feat", "--base", "main", "--tip", "feature/x", "--branch", "feature/x", "--no-walk"], root=repo)
    text = (feature / "hand-over" / "index.html").read_text(encoding="utf-8")
    assert MISSING in text and "failed when run with the others" not in text
    write_lines(feature / "walks" / handover.FLAKY_RECORD, [flaky_line(WOBBLY)])
    handover.main(["feat", "--base", "main", "--tip", "feature/x", "--branch", "feature/x", "--no-walk"], root=repo)
    text = (feature / "hand-over" / "index.html").read_text(encoding="utf-8")
    assert MISSING not in text and "1 browser test failed when run with the others and passed when run alone" in text


def test_a_quick_run_is_a_run_of_the_browser_tests_so_its_record_is_looked_for_and_read():
    runs = handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z"),
                               run("feature/x", "green", "2026-11-16T11:00:00Z", quick=True)], "feature/x")
    assert handover.flaky_facts(runs, [flaky_line(at="2026-11-16T10:00:00Z")])["missing"]
    seen = handover.flaky_facts(runs, [flaky_line(at="2026-11-16T10:00:00Z"), flaky_line(WOBBLY, at="2026-11-16T11:00:00Z")])
    assert seen == {"walks": {WOBBLY: ["2026-11-16T11:00:00Z"]}, "missing": False}


def test_a_quick_run_and_the_full_run_straight_after_it_on_the_same_commit_each_get_only_their_own_record_line():
    quick = run("feature/x", "green", "2026-11-16T10:00:00Z", quick=True, minutes=2.6)
    full = run("feature/x", "green", "2026-11-16T10:04:02Z", minutes=3.7)
    runs = handover.run_facts([quick, full], "feature/x")
    seen = handover.flaky_facts(runs, [flaky_line(WOBBLY, at="2026-11-16T09:59:58Z"), flaky_line(at="2026-11-16T10:04:00Z")])
    assert seen == {"walks": {WOBBLY: ["2026-11-16T10:00:00Z"]}, "missing": False}
    assert handover.flaky_facts(runs, [flaky_line(at="2026-11-16T09:59:58Z")])["missing"]


def test_the_example_in_walk_saids_docstring_names_nothing_of_this_product():
    assert not re.search(r"trial|registry|watchlist|clinical|filter", handover.walk_said.__doc__, re.I), handover.walk_said.__doc__


def test_nothing_in_handover_py_names_this_product():
    text = pathlib.Path(handover.__file__).read_text()
    named = [line for line in text.splitlines() if re.search(r"trial|registry|watchlist|clinical|filter", line, re.I)]
    assert not named, named



def test_a_page_from_a_run_that_lists_lint_names_it_in_the_owner_s_words_never_bare():
    line = run("feature/x", "red")
    for check in line["checks"][1:]:
        check.update(result="not run", minutes=0.0)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(style|script)\b.*?</\1>", "", page(runs=handover.run_facts([line], "feature/x"), git=GIT))))
    assert "check of the code for common mistakes (lint)" in text
    named = [m.start() for m in re.finditer(r"\blint\b", text) if not text[m.end():].startswith(".txt")]
    bare = [i for i in named if not text[:i].endswith("check of the code for common mistakes (")]
    assert named and bare == [], [text[max(i - 60, 0):i + 20] for i in bare]



@pytest.fixture(autouse=True)
def no_github(monkeypatch, tmp_path):
    """No test talks to GitHub: the page asks a `gh` that is not there unless a test puts its own stand-in in its place."""
    monkeypatch.setattr(handover, "GH", str(tmp_path / "no-gh-here"))


def gh(repo: pathlib.Path, runs=(), jobs=(), pr=None, code=0, said="", wait=0) -> pathlib.Path:
    """A `gh` that answers as GitHub would: the runs of a workflow, a run's jobs, the branch's pull request (none: it ends 1)."""
    script = repo.parent / "gh"
    pr_said = f"printf '%s' '{json.dumps(pr)}'" if pr else "echo 'no pull requests found' >&2; exit 1"
    script.write_text("\n".join([
        "#!/bin/sh", f"[ {wait} -gt 0 ] && exec sleep {wait}", f'echo "$*" >> "{repo.parent / "gh-asked.txt"}"',
        f"[ {code} -ne 0 ] && {{ printf '%s' '{said}' >&2; exit {code}; }}",
        'case "$1 $2" in',
        f"  'run list') printf '%s' '{json.dumps(list(runs))}' ;;",
        f"  'run view') printf '%s' '{json.dumps({'jobs': list(jobs)})}' ;;",
        f"  'pr view') {pr_said} ;;",
        "esac", ""]))
    script.chmod(0o755)
    return script


def gh_run(repo, ref="feature/x", status="completed", conclusion="success", number=57, at="2026-11-02T11:00:00Z", **more):
    return {"databaseId": 900 + number, "number": number, "status": status, "conclusion": conclusion, "headSha": git(repo, "rev-parse", ref),
            "url": f"https://github.com/o/r/actions/runs/{900 + number}", "createdAt": at, "startedAt": at,
            "updatedAt": "2026-11-02T11:07:00Z", **more}


def built_with(repo, monkeypatch, stand_in=None) -> str:
    """The page main() builds of feature/x, with `gh` played by the stand-in (None: no gh on this computer)."""
    if stand_in:
        monkeypatch.setattr(handover, "GH", str(stand_in))
    write_lines(repo / ".scratch" / "feat" / "findings" / "walker-a.jsonl", [])
    assert handover.main(["feat", "--base", "main", "--tip", "feature/x", "--branch", "feature/x", "--no-walk"], root=repo) == 0
    return (repo / ".scratch" / "feat" / "hand-over" / "index.html").read_text(encoding="utf-8")


def github_thing(text: str) -> tuple[str, str, str, str] | None:
    """The one thing to look at that is about GitHub's run of the checks, if the list has one."""
    return next((thing for thing in things(text) if "GitHub" in thing[2]), None)


def test_a_run_on_github_that_passed_says_so_with_its_number_and_minutes_and_adds_nothing_to_look_at(repo, monkeypatch):
    text = built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)]))
    assert github_thing(text) is None
    assert "GitHub&#x27;s run of the automated checks passed on the build&#x27;s last commit: run 57, which took 7 minutes." in top(text)


def count_of(text: str) -> int:
    return len(things(text))


def test_a_run_on_github_that_failed_gives_its_address_and_failed_step_and_is_one_more_thing_to_look_at(repo, monkeypatch):
    passed = count_of(built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)])))
    jobs = [{"name": "checks", "steps": [{"name": "Set up", "conclusion": "success"}, {"name": "Run every check", "conclusion": "failure"}]}]
    text = built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo, conclusion="failure")], jobs=jobs))
    assert count_of(text) == passed + 1
    tone, href, what, why = github_thing(text)
    assert (tone, what) == ("amber", "GitHub&#x27;s run of the automated checks failed on the build&#x27;s last commit")
    assert "Run 57 (https://github.com/o/r/actions/runs/957) failed at the step “Run every check”." in why
    assert "its own computer, which runs Linux" in why and "Ask for the failure to be fixed before you accept this build." in why


def test_a_run_on_github_still_going_says_to_wait_and_build_the_page_again(repo, monkeypatch):
    passed = count_of(built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)])))
    text = built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo, status="in_progress", conclusion="")]))
    assert count_of(text) == passed + 1
    tone, href, what, why = github_thing(text)
    assert what == "GitHub&#x27;s run of the automated checks had not finished when this page was built"
    assert "was still running, so this page cannot say whether it passes" in why
    assert "Wait for it to end, then ask for this page to be built again." in why


def test_no_run_on_github_for_this_commit_says_so_and_how_to_start_one(repo, monkeypatch):
    passed = count_of(built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)])))
    text = built_with(repo, monkeypatch, gh(repo, runs=[]))
    assert count_of(text) == passed + 1
    tone, href, what, why = github_thing(text)
    tip = git(repo, "rev-parse", "--short", "feature/x")
    assert what == "GitHub has not run the automated checks on the build&#x27;s last commit"
    assert f"No run was made for commit {tip} of branch feature/x." in why and "earlier commit" not in why
    assert "pushing the branch to GitHub with a pull request open for it starts one" in why


@pytest.mark.parametrize("stand_in, why, fix", [
    (None, "The gh command, through which this page asks GitHub, is not installed on this computer.", "Install the gh command"),
    (dict(code=4, said="To get started with GitHub CLI, please run:  gh auth login"), "The gh command is not signed in to GitHub.",
     "Sign in: type gh auth login in a terminal, then ask for this page to be built again."),
    (dict(code=1, said="HTTP 502: Bad gateway"), "The gh command ended with an error: “HTTP 502: Bad gateway”.", "built again in a few minutes"),
    (dict(wait=30), "GitHub did not answer within 1 seconds.", "built again in a few minutes"),
])
def test_when_github_cannot_be_asked_the_page_is_still_built_and_says_why(repo, monkeypatch, stand_in, why, fix):
    passed = count_of(built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)])))
    monkeypatch.setattr(handover, "GITHUB_SECONDS", 1)
    started = time.monotonic()
    text = built_with(repo, monkeypatch, stand_in and gh(repo, **stand_in))
    if stand_in is None:
        monkeypatch.setattr(handover, "GH", str(repo.parent / "no-gh-here"))
        text = built_with(repo, monkeypatch)
    assert time.monotonic() - started < 10
    assert count_of(text) == passed + 1
    tone, href, what, said = github_thing(text)
    assert what == "This page could not ask GitHub how its run of the automated checks went"
    assert why in said and fix in said and "nothing on this page says whether the checks pass on GitHub&#x27;s computer" in said


def test_a_run_of_an_earlier_commit_is_never_this_commit_s_and_of_two_runs_of_this_commit_the_newer_decides(repo, monkeypatch):
    earlier = gh_run(repo, ref="feature/x~1", number=56)
    text = built_with(repo, monkeypatch, gh(repo, runs=[earlier]))
    tone, href, what, why = github_thing(text)
    assert what == "GitHub has not run the automated checks on the build&#x27;s last commit"
    assert "GitHub has a run of an earlier commit of the branch; it says nothing of this one." in why and "Run 56" not in text
    newer_red = [gh_run(repo, number=58, conclusion="failure", at="2026-11-02T12:00:00Z"), gh_run(repo, number=57), earlier]
    assert "Run 58 " in github_thing(built_with(repo, monkeypatch, gh(repo, runs=newer_red)))[3]
    newer_green = [gh_run(repo, number=57, conclusion="failure"), gh_run(repo, number=58, at="2026-11-02T12:00:00Z")]
    text = built_with(repo, monkeypatch, gh(repo, runs=newer_green))
    assert github_thing(text) is None and "passed on the build&#x27;s last commit: run 58," in top(text)


def test_a_draft_pull_request_is_given_with_its_address_and_said_not_yet_accepted_and_none_is_not_mentioned(repo, monkeypatch):
    draft = {"url": "https://github.com/o/r/pull/12", "isDraft": True}
    text = built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)], pr=draft))
    assert ("The pull request is at https://github.com/o/r/pull/12. It is still a draft: not yet accepted, so it cannot be merged."
            in top(text))
    text = built_with(repo, monkeypatch, gh(repo, runs=[], pr=draft))
    assert "https://github.com/o/r/pull/12. It is still a draft" in github_thing(text)[3]
    merged = built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)], pr={"url": "https://github.com/o/r/pull/9", "isDraft": False, "state": "MERGED"}))
    assert "The pull request is at https://github.com/o/r/pull/9. It is already merged." in top(merged)
    text = built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)]))
    assert "The pull request is at" not in text


def test_github_is_asked_about_the_checks_workflow_on_the_branch_asked_for(repo, monkeypatch):
    built_with(repo, monkeypatch, gh(repo, runs=[gh_run(repo)]))
    asked = (repo.parent / "gh-asked.txt").read_text().splitlines()
    assert asked[0].startswith("run list --workflow checks.yml --branch feature/x ") and asked[1] == "pr view feature/x --json url,isDraft,state"


def test_a_page_built_without_asking_github_says_github_was_not_asked_and_lists_nothing_for_it():
    text = page(git=GIT)
    assert github_thing(text) is None and "GitHub was not asked" in text
