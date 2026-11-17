"""handover.py: the one page a build ends with.

These test the parts that read and compute, what the page draws for each state of the
records, and that the page escapes what it is given. Git facts come from a small real
repository made in a temporary folder; the walk is run through a stand-in for
.venv/bin/python. Lacks: the real browser run (`handover.py` is run for real for that),
and so the page's script, which only steps through pictures the page already shows.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
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


def things(text: str) -> list[tuple[str, str, str, str]]:
    """(colour, what, why, link) of each thing the list under the headline tells the owner to look at, in order."""
    listed = re.search(r'<ol class="look">(.*?)</ol>', top(text), re.S)
    return re.findall(r'<li class="(\w+)"><span class="mark"[^>]*>[^<]*</span><a href="([^"]*)"><strong>(.*?)</strong><span class="sub">(.*?)</span></a></li>',
                      listed.group(1)) if listed else []


def drawn_green(text: str) -> list[str]:
    """Everything the page draws as passed: a tile, a label, a check or the headline. (A square of the run history is
    drawn blue or red, never in the passed green: an old run is not a verdict.)"""
    return re.findall(r'class="[^"]*(?<![\w-])green(?![\w-])[^"]*"', text)


# Joining findings to fates.

def test_a_finding_with_no_fate_line_is_grouped_first_under_no_fate_recorded():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C"), finding("D")],
        {"A": fate("A"), "C": fate("C", "left", check=""), "D": fate("D", "")},
    )
    groups = handover.group_by_state(joined)
    assert [state for state, _ in groups][0] == "no-fate"
    assert [f["id"] for f in groups[0][1]] == ["B", "D"]  # a fate line that names no fate is no fate either
    assert handover.STATES["no-fate"][0] == "No fate recorded"
    assert "names no fate" in handover.STATES["no-fate"][3]  # true of both


def test_a_fixed_fate_that_names_no_check_is_marked_fixed_no_check_named():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C")],
        {"A": fate("A"), "B": fate("B", check=""), "C": fate("C", check="   ")},
    )
    assert {f["id"]: f["state"] for f in joined} == {"A": "fixed", "B": "fixed-no-check", "C": "fixed-no-check"}
    assert handover.STATES["fixed-no-check"][0] == "Fixed, no check named"


def test_a_fixed_fate_whose_check_or_commit_was_not_found_is_not_fixed():
    joined = handover.join([finding("A"), finding("B")], {"A": fate("A"), "B": fate("B")}, {"B": "commit abc1234 is not in the repository"})
    assert {f["id"]: f["state"] for f in joined} == {"A": "fixed", "B": "fixed-not-found"}
    text = page([finding("A"), finding("B")], fates={"A": fate("A"), "B": fate("B")}, missing={"B": "commit abc1234 is not in the repository"})
    assert "Not found: commit abc1234 is not in the repository." in text
    assert "handover.py found each check" in text  # said of the Fixed group, because it looked
    assert "handover.py found each check" not in page([finding("A")], fates={"A": fate("A")})  # nobody looked: not claimed


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


# Counting by finder and pass.

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
    assert "Pass not recognised" in text
    walker = re.search(r"<tr><th>Walker</th>(.*?)</tr>", text).group(1)
    assert sum(int(n) for n in re.findall(r">(\d+)<", walker)) == 4  # the row adds up to the walker's findings
    assert "Pass not recognised" not in page([finding("1"), finding("2", round="recheck")])


# Reading the record files.

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
    assert list(fates) == ["W-1"] and fates["W-1"]["fate"] == "fixed"  # a later line replaces an earlier one


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
    fits = {"what": most, "so_what": [longest], "now_what": most + most}  # what is left is as long as its list needs
    (tmp_path / "hand-over.json").write_text(json.dumps(fits), encoding="utf-8")
    assert handover.read_summary(tmp_path) == fits
    for wrong, said in (({"what": most + ["One more."]}, "what has 6 lines"), ({"so_what": most + ["One more."]}, "so_what has 6 lines"),
                        ({"now_what": ["Short.", longest + "x"]}, f"now_what line 2 is {handover.LINE_LENGTH + 1} characters")):
        (tmp_path / "hand-over.json").write_text(json.dumps(wrong), encoding="utf-8")
        with pytest.raises(SystemExit) as stopped:
            handover.read_summary(tmp_path)
        assert said in str(stopped.value) and "hand-over.json" in str(stopped.value) and "\n" not in str(stopped.value)


# The checks run log.

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
    assert facts["later"] is None and facts["why_unknown"] == ""
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
    for label in ("Last checks run", "Red check runs", "Commits", "Files changed", "Lines added", "Tests",
                  "Findings recorded", "Findings with no fate"):
        assert re.fullmatch(r'<span class="unknown">[a-z ]+</span>', row(text, label)), label
    assert "does not exist" in text
    assert not drawn_green(text) and tile(text, "#facts") == ("amber", "Checks: unknown")
    one_empty_file = page(files={"walker-find-trials.jsonl": []})
    assert row(one_empty_file, "Findings recorded") == "0" and row(one_empty_file, "Findings with no fate") == "0"  # looked: a true zero


def test_a_run_of_one_named_check_is_never_the_last_checks_run_and_never_turns_the_pill_green():
    runs = handover.run_facts([run("feature/x", "red", "2026-11-16T10:00:00Z"),
                               run("feature/x", "green", "2026-11-16T10:20:00Z", names=("unit",))], "feature/x")
    assert runs["full"]["result"] == "red" and runs["later"]["at"] == "2026-11-16T10:20:00Z"
    text = page(runs=runs, git=GIT)
    last = row(text, "Last checks run")
    assert 'pill red">red<' in last and not drawn_green(text)
    assert "A later run of unit only was green at 16 Nov 2026, 10:20 UTC; it did not run patterns, escapes, walks." in last
    assert tile(text, "#facts") == ("red", "Checks RED")
    assert re.findall(r'<span class="(r-\w+)( part)?" title', text) == [("r-red", ""), ("r-green", " part")]  # every run, oldest first
    assert "1 of 2 runs" in row(text, "Red check runs") and "a run of one named check too" in text


def test_with_no_run_of_every_check_the_last_checks_run_is_unknown_and_says_why():
    old_line = run("feature/x", "green", names=("patterns", "escapes"), all=True)  # an old line's "all" decides nothing
    runs = handover.run_facts([old_line], "feature/x")
    assert runs["full"] is None and runs["later"] == old_line
    text = page(runs=runs, git=GIT)
    assert row(text, "Last checks run").startswith('<span class="unknown">unknown</span>')
    assert "The last run of patterns, escapes only was green" in text and "it did not run unit, walks" in text
    assert "none of them is a run of every check (patterns, escapes, unit, walks)" in text
    assert not drawn_green(text) and tile(text, "#facts") == ("amber", "Checks: unknown")


def test_a_green_run_is_drawn_green_only_on_the_build_s_last_commit_as_committed():
    green = lambda **more: page(runs=handover.run_facts([run("feature/x", "green", **more)], "feature/x"), git=GIT)  # noqa: E731
    assert 'pill green">green<' in row(green(), "Last checks run") and tile(green(), "#facts") == ("green", "Checks green")
    assert top(green()).count('<span class="chk green">') == 4  # each check of that run, on the tile
    for text in (green(tip="fff9999"), green(dirty=True)):
        assert not drawn_green(text) and top(text).count('<span class="chk ">') == 4
        assert tile(text, "#facts") == ("amber", "Checks green, on code that is not the build&#x27;s last commit")
    assert "on commit fff9999, not the build&#x27;s last commit (abc1234)" in green(tip="fff9999")
    assert "with uncommitted changes in the folder" in green(dirty=True)


def test_a_later_run_of_one_check_that_was_not_green_is_on_the_board_not_only_in_the_folded_list():
    walked = {"git": GIT, "recording": {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0},
              "files": {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}}
    then = lambda result: handover.run_facts([run("feature/x", "green", "2026-11-16T10:00:00Z"),  # noqa: E731
                                              run("feature/x", result, "2026-11-16T10:20:00Z", names=("unit",))], "feature/x")
    red = page(runs=then("red"), **walked)
    assert tile(red, "#facts") == ("red", "Checks green, then a later run of some was RED")
    assert '<p class="headline red">' in top(red) and "1 thing to look at" in top(red) and "Nothing on record" not in red
    assert "A later run of unit only was red at 16 Nov 2026, 10:20 UTC; it did not run patterns, escapes, walks." in top(red)
    assert '<span class="chk green">' not in red and top(red).count('<span class="chk ">') == 4  # the earlier green run is not drawn as passed
    odd = page(runs=then("stopped"), **walked)
    assert tile(odd, "#facts") == ("amber", "Checks green, then a later run of some was not green") and '<p class="headline amber">' in top(odd)
    green = page(runs=then("green"), **walked)  # a later green run of one check changes nothing, and is not said on the board
    assert tile(green, "#facts") == ("green", "Checks green") and "A later run" not in top(green) and '<p class="headline green">' in top(green)
    only_red = page(runs=handover.run_facts([run("feature/x", "red", names=("unit",))], "feature/x"), **walked)  # no run of every check at all
    assert tile(only_red, "#facts") == ("red", "Checks: the last run was RED") and "The last run of unit only was red" in top(only_red)


def test_why_a_green_run_is_not_counted_is_said_on_the_tile_itself():
    green = lambda **more: top(page(runs=handover.run_facts([run("feature/x", "green", **more)], "feature/x"), git=GIT))  # noqa: E731
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
    assert "Blue was green when it ran, red was red" in page(runs=handover.run_facts([run("feature/x", "green")], "feature/x"))


def test_a_check_that_was_not_run_has_no_duration_and_a_very_short_one_is_not_zero_minutes():
    line = run("feature/x", "red")
    line["checks"][0].update(minutes=0.0)
    line["checks"][3].update(result="not run", minutes=0.0)
    last = row(page(runs=handover.run_facts([line], "feature/x")), "Last checks run")
    assert "patterns: " in last and "under 0.1 minutes" in last
    assert re.search(r'walks: <span class="pill ">not run</span> output', last)
    assert "0 minutes" not in last


# Git facts, from a real repository.

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
    assert facts["files"] == 7  # app.py, tests/test_new.py, walks/test_walk.py, notes.py, walks/helper.py, tests/test_old.py, .claude/notes.md
    assert facts["added_by"] == {"product": 2 + 2, "tests and walks": 6 + 2 + 2, "build records and kit (.scratch/, .claude/)": 3}
    assert facts["added"] == 17
    assert facts["removed"] == 1 + 2
    assert facts["tests_added"] == 3  # test_a, test_b, test_walk_it; not notes.py, not the string
    assert facts["tests_removed"] == 1  # test_old
    assert facts["base"] == git(repo, "rev-parse", "--short", "main")
    assert facts["tip"] == git(repo, "rev-parse", "--short", "feature/x")
    text = page(git=facts)
    assert row(text, "Tests") == "3 added, 1 removed"
    assert [text.count(f'title="{kind}: {count}"') for kind, count in (("product", 4), ("tests and walks", 10))] == [1, 1]  # the lines bar
    assert "of them 4 product, 10 tests and walks, 3 build records and kit (.scratch/, .claude/)" in text


def test_git_facts_of_an_empty_range_leave_the_times_unknown(repo):
    facts = handover.git_facts(repo, "feature/x", "feature/x")
    assert facts["commits"] == 0
    assert facts["first"] is None and facts["last"] is None and facts["minutes"] is None


def test_a_fixed_fate_needs_its_check_s_file_in_the_last_commit_and_its_commit_in_the_repository(repo):
    tip = git(repo, "rev-parse", "--short", "feature/x")
    fates = {
        "ok": fate("ok", check="walks/test_walk.py::test_walk_it[chromium-1440x900]", commit=tip),
        "whole-file": fate("whole-file", check="tests/test_new.py", commit=tip),
        "gone": fate("gone", check="tests/test_old.py::test_old", commit=tip),  # the build deleted it
        "no-commit": fate("no-commit", check="tests/test_new.py::test_a", commit=""),
        "bad-commit": fate("bad-commit", check="tests/test_new.py::test_a", commit="0123abc"),
        "both": fate("both", check="nowhere.py::test_x", commit="--help"),
        "left": fate("left", "left", check="nowhere.py", commit=""),  # only fixed fates are looked up
        "no-check": fate("no-check", check="", commit=""),
    }
    missing = handover.missing_proof(repo, tip, fates)
    assert set(missing) == {"gone", "no-commit", "bad-commit", "both"}
    assert missing["gone"] == f"the check's file tests/test_old.py is not in the build's last commit ({tip})"
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
    assert capsys.readouterr().out.splitlines()[-1] == f"open {page_file}"
    text = page_file.read_text(encoding="utf-8")
    assert "No recording" in text and "<video" not in text  # --no-walk and no earlier recording
    assert "1 of 2 runs" in text  # the red runs of feature/x
    assert "No fate recorded" in text and text.index("what W-2") < text.index("what W-4") < text.index("what W-3") < text.index("what W-1")
    assert "Not found: the check&#x27;s file walks/test_gone.py is not in the build&#x27;s last commit" in text
    assert "hand-over.json is missing" in text
    assert "<code>review-a.jsonl</code>: looked, found nothing" in text and "<code>walker-a.jsonl</code>: 4" in text
    assert "<th>Early read</th><td colspan=\"2\"><span class=\"unknown\">no findings file: did not run</span>" in text
    assert "<th>Review</th><td class=\"n soft\">none recorded</td>" in text  # it has a file: it looked


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


# The page.

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
        assert text.count("<script") == 1  # the page's own
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
    assert 'class="group note"' in tags["NOCHECK"] and "open" not in tags["NOCHECK"]  # marked, but folded
    assert 'class="group "' in tags["FIXED"] and "open" not in tags["FIXED"]
    assert "No fate recorded" in text and "Fixed, no check named" in text and "Fate: fixed" in text
    assert row(text, "Findings with no fate") == '<span class="badly">1</span>'


def test_the_board_under_the_title_says_what_needs_the_owner_before_anything_else():
    green_run, every = handover.run_facts([run("feature/x", "green")], "feature/x"), {"walker-a.jsonl": [finding("A")], "review-a.jsonl": [], "early-read-whole.jsonl": []}
    settled = {"fates": {"A": fate("A")}, "git": GIT, "runs": green_run, "recording": {"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0}}
    clean = page(files=every, **settled)
    assert '<p class="headline green">' in top(clean) and "Nothing on record needs a second look" in top(clean)
    assert tile(clean, "#recording") == ("green", "The walk passed") and tile(clean, "#facts") == ("green", "Checks green")
    assert chip(clean, "", "#group-0", "Fixed: 1") and "1 found" in top(clean)
    assert "settled" not in top(clean) and "What became of a finding is the agents' record: the script did not test it." in top(clean)
    assert '<a href="#summary">There is no builder&#x27;s summary: hand-over.json is missing.</a>' in top(clean)
    left = lambda lines: top(page(files=every, summary={"what": [], "so_what": [], "now_what": lines}, **settled))  # noqa: E731
    assert '<a href="#summary">The builder lists 2 things as left for you, further down.</a>' in left(["Ticket 07 was not built.", "Try it in Safari."])
    assert "The builder lists 1 thing as left for you" in left(["One."]) and "The builder wrote nothing as left for you." in left([])
    no_findings = top(page(files={name: [] for name in every}, **{**settled, "fates": {}}))
    assert '<p class="headline green">' in no_findings and "the findings files hold no findings" in no_findings and "agents" not in no_findings
    odd_pass = page(files={**every, "walker-a.jsonl": [finding("A", round="third")]}, **settled)
    assert '<p class="headline amber">' in top(odd_pass) and "1 thing to look at" in top(odd_pass)
    assert chip(odd_pass, "amber", "#finders", "Pass not recognised: 1")
    two_did_not_look = top(page([finding("A")], **settled))  # the walker's file only
    assert '<p class="headline amber">' in two_did_not_look and "2 things to look at before you decide" in two_did_not_look
    assert "Nothing on record" not in two_did_not_look
    red = page(files=every, fates={"A": fate("A")}, git=GIT, runs=handover.run_facts([run("feature/x", "red")], "feature/x"))
    assert tile(red, "#facts") == ("red", "Checks RED") and not drawn_green(red)
    assert '<p class="headline red">' in top(red) and "2 things to look at" in top(red)  # the checks, and no walk
    no_fate = page([finding("A"), finding("B"), finding("C"), finding("D")],
                   fates={"A": fate("A"), "C": fate("C", "left"), "D": fate("D", check=""), "Z": fate("Z")})
    for look, href, words in (("bad", "#group-0", "No fate recorded: 1"), ("warn", "#group-1", "Left as it is: 1"),
                              ("note", "#group-2", "Fixed, no check named: 1"), ("", "#group-3", "Fixed: 1"),
                              ("amber", "#findings", "Fate lines matching no finding: 1"), ("amber", "#finders", "Review: no findings file")):
        assert chip(no_fate, look, href, words), words
    assert tile(no_fate, "#recording") == ("amber", "The walk was not run for this page")
    assert re.findall(r'<span class="(s-\w+)" style="flex-grow: 1"', top(no_fate)) == ["s-bad", "s-left", "s-nocheck", "s-fixed"]  # the bar
    assert '<p class="headline red">' in top(no_fate) and "8 things to look at" in top(no_fate) and "4 found" in top(no_fate)
    assert 'id="group-0" class="group bad"' in no_fate
    nothing = top(page())
    nothing = nothing[nothing.index("<header>"):]
    assert "No findings file was read" in nothing and "Nobody looked" in nothing
    assert not re.search(r">[^<]*\b0\b[^<]*<", nothing)  # none recorded is never drawn as 0


def test_a_reason_every_finding_of_a_group_shares_is_said_once_above_the_cards():
    why = "Out of scope for this build."
    same = page([finding("A"), finding("B"), finding("C")], fates={i: fate(i, "left", why=why) for i in "ABC"})
    assert same.count(why) == 1 and f"The record gives the same reason for all 3: {why}" in same
    mixed = page([finding("A"), finding("B")], fates={"A": fate("A", "left", why=why), "B": fate("B", "left", why="Another reason.")})
    assert mixed.count(why) == 1 and "Another reason." in mixed and "the same reason" not in mixed
    alone = page([finding("A")], fates={"A": fate("A", "left", why=why)})
    assert alone.count(why) == 1 and "the same reason" not in alone
    assert "the same reason" not in page([finding("A"), finding("B")], fates={i: fate(i) for i in "AB"})  # no reason given is not a shared reason
    folded = same[same.index('<section id="findings">'):]
    assert "those whose record is missing or does not hold up" in folded and "settled" not in folded


def test_the_headline_s_count_is_a_list_that_names_each_thing_says_why_and_links_to_it():
    green_run = handover.run_facts([run("feature/x", "green", tip="fff9999")], "feature/x")
    text = page([finding("A"), finding("B"), finding("C"), finding("D")], git=GIT, runs=green_run,
                fates={"A": fate("A"), "C": fate("C", "left"), "D": fate("D", check=""), "Z": fate("Z")},
                recording={"commit": "abc1234", "dirty": True, "result": "passed", "megabytes": 1.0})
    listed = things(text)
    assert [(colour, link, what) for colour, link, what, _ in listed] == [
        ("amber", "#recording", "The walk passed, on code that is not the build&#x27;s last commit"),
        ("amber", "#facts", "Checks green, on code that is not the build&#x27;s last commit"),
        ("red", "#group-0", "No fate recorded: 1 finding"), ("amber", "#group-1", "Left as it is: 1 finding"),
        ("amber", "#group-2", "Fixed, no check named: 1 finding"),
        ("amber", "#finders", "Review: no findings file"), ("amber", "#finders", "Early read: no findings file"),
        ("amber", "#findings", "Fate lines matching no finding: 1")]
    assert f"{len(listed)} things to look at before you decide" in top(text)  # the count is the list's length
    whys = [why for *_, why in listed]
    assert whys[0] == "It ran with uncommitted changes in the folder, so it does not show that the last commit, as committed, passes."
    assert whys[1] == "That run was on commit fff9999, not the build&#x27;s last commit (abc1234)."
    assert whys[2].startswith("fates.jsonl names no fate") and whys[3] == "Recorded as known and left."
    assert whys[5] == "A finder writes its file even when it finds nothing, so this one did not run."
    assert all(why for why in whys) and "Fixed: 1" not in "".join(what for _, _, what, _ in listed)  # what is fixed with its check is not listed
    red = page(runs=handover.run_facts([run("feature/x", "red")], "feature/x"), git=GIT, recording={**RECORDING, "result": "failed", "reason": "It was stopped after 15 minutes"})
    assert things(red)[:2] == [("red", "#recording", "The walk FAILED", "It was stopped after 15 minutes."),
                               ("red", "#facts", "Checks RED", "Red in the last run of every check: patterns, escapes, unit, walks.")]
    assert things(page())[0] == ("amber", "#recording", "The walk was not run for this page", "So there is no recording and there are no pictures.")
    every = {"walker-a.jsonl": [], "review-a.jsonl": [], "early-read-whole.jsonl": []}
    clean = page(files=every, git=GIT, runs=handover.run_facts([run("feature/x", "green")], "feature/x"),
                 recording={"commit": "abc1234", "dirty": False, "result": "passed", "megabytes": 1.0})
    assert things(clean) == [] and '<ol class="look">' not in clean  # nothing to look at: no list


def test_the_page_labels_what_an_agent_wrote_and_what_the_script_computed():
    text = page([finding("A", what="The finder saw this.")], fates={"A": fate("A", "left", why="The fixer gave this reason.")},
                summary={"what": ["Built the thing."], "so_what": ["It matters."], "now_what": ["Decide."]})
    assert "Written by the build agent" in text
    assert "Computed by handover.py" in text
    assert text.index("Written by the build agent") < text.index("Computed by handover.py")
    sections = {match.group(1): match.group(2) for match in re.finditer(r'<section id="(\w+)">(.*?)</section>', text, re.S)}
    agent_words = ("Built the thing.", "It matters.", "Decide.", "The finder saw this.", "The fixer gave this reason.")
    for name, body in sections.items():  # an agent's words are drawn only in the two sections that say whose they are
        assert any(words in body for words in agent_words) == (name in ("summary", "findings")), name
    assert all(words not in top(text) for words in agent_words)
    assert "the script did not check them" in sections["summary"] and "the script did not check them" in sections["findings"]
    assert "copied from the findings files" in sections["findings"]


def test_what_is_left_shows_its_first_lines_and_folds_the_rest_under_their_count():
    lines = [f"Left {n}." for n in range(1, 8)]
    text = page(summary={"what": ["Built."], "so_what": ["It matters."], "now_what": lines})
    card = text[text.index("What is left for you"):text.index("</section>", text.index("What is left for you"))]
    shown, folded = card.split("<details>")
    assert [line in shown for line in lines] == [True] * 5 + [False] * 2
    assert "<summary>2 more</summary>" in folded and all(line in folded for line in lines[5:])
    assert "<details>" not in page(summary={"what": ["Built."], "so_what": ["It matters."], "now_what": lines[:5]}).split('id="summary"')[1].split("</section>")[0]


def test_the_page_says_so_when_there_is_no_summary_no_recording_and_no_findings_file():
    text = page()
    assert "<video" not in text
    assert "No recording: the walk was not run for this page." in text
    assert "No screenshots: the walk was not run for this page." in text
    assert "hand-over.json" in text  # names the missing summary file
    assert "No findings file was read" in text
    assert text.count("no findings file: did not run") == 3  # the walker, the review and the early read


def test_a_finder_that_looked_and_found_nothing_is_told_apart_from_one_that_never_ran():
    looked = page(files={"walker-find-trials.jsonl": [], "early-read-whole.jsonl": []})
    assert looked.count("looked, found nothing") == 2
    assert looked.count("no findings file: did not run") == 1 and "<th>Review</th><td colspan" in looked
    assert "<th>Walker</th><td class=\"n soft\">none recorded</td>" in looked
    assert "The findings files read hold no findings." in looked
    assert "No findings in the 2 findings files read" in top(looked) and "Review: no findings file" in top(looked)
    named_by_its_rows = page(files={"1-anything.jsonl": [finding("A", "review")]})
    assert "<th>Review</th><td class=\"n\">1</td>" in named_by_its_rows and "<th>Walker</th><td colspan" in named_by_its_rows
    assert looked != page()


def test_fate_lines_that_match_no_finding_are_drawn_first_and_marked_with_or_without_findings():
    fates = {"Z1": fate("Z1"), "Z2": fate("Z2", "left", why="left on purpose")}
    alone = page(fates=fates)
    assert "2 fate lines name a finding the page did not read." in alone
    assert "<code>Z1</code>: fixed." in alone and "<code>Z2</code>: left. left on purpose" in alone
    assert "nothing to list" not in alone and "hold no findings" not in alone
    assert row(alone, "Fate lines matching no finding") == '<span class="warned">2</span>'
    beside = page([finding("A")], fates={**fates, "A": fate("A")})
    assert beside.index('<div class="orphans">') < beside.index("<details")
    assert row(page([finding("A")], fates={"A": fate("A")}), "Fate lines matching no finding") == "0"


def test_every_finding_read_is_drawn_once_as_a_card_and_counted_once_in_each_count():
    findings = [finding("A"), finding("B", round="recheck"), finding("C", "review"), finding("D", "stranger", "re-check"),
                finding("E", round=None), finding("F", ""), finding("G"), finding("H")]
    del findings[6]["finder"]
    fates = {"A": fate("A"), "B": fate("B", check=""), "C": fate("C", "left"), "D": fate("D", "not-a-defect"),
             "F": fate("F", "Fixed"), "G": fate("G", ""), "H": fate("H")}
    text = page(files={"walker-a.jsonl": findings[:4], "other.jsonl": findings[4:]}, fates=fates, missing={"H": "no commit is named"})
    cards = text.split('<li class="finding">')[1:]
    assert len(cards) == 8
    for f in findings:
        assert sum(f'<p class="what">what {f["id"]} looks like</p>' in card for card in cards) == 1, f["id"]
    assert sum(int(n) for n in re.findall(r'<span class="count">(\d+)</span>', text)) == 8  # the groups
    table = re.search(r"<tbody>(.*?)</tbody>", text, re.S).group(1)
    assert sum(int(n) for n in re.findall(r">(\d+)</(?:td|span)>", table)) == 8  # the finders table
    assert sum(int(n) for n in re.findall(r'href="#group-\d+"><i[^>]*></i>[^<]*: (\d+)<', top(text))) == 8  # the board's labels
    assert sum(int(n) for n in re.findall(r'style="flex-grow: (\d+)" title', top(text))) == 8 and "8 found" in top(text)  # its bar
    assert row(text, "Findings recorded") == "8"
    assert "<code>walker-a.jsonl</code>: 4" in text and "<code>other.jsonl</code>: 4" in text


RECORDING = {"walk": "walks/test_acceptance_walk.py::test_x", "at": "2026-11-16T21:00:00+00:00",
             "commit": "dd4ea9d", "dirty": True, "result": "passed", "minutes": 1.5, "megabytes": 11.2}


def test_the_page_names_the_commit_the_recording_was_made_on_and_shows_the_video():
    text = page(recording=RECORDING, shots=["a-01-created.png"])
    assert '<video controls' in text and 'src="recording.webm"' in text
    assert "dd4ea9d" in text and "uncommitted changes" in text and "21:00 UTC" in text
    assert '<img src="shots/a-01-created.png" alt="Step 1: created">' in text and "<figcaption>Step 1: created</figcaption>" in text
    assert "walk-output.txt" not in text  # a walk that passed has nothing to chase


def test_a_walk_is_drawn_as_passed_only_when_it_passed_on_the_build_s_last_commit_as_committed():
    on_tip = page(recording={**RECORDING, "commit": "abc1234", "dirty": False}, git=GIT)
    assert 'pill green">The walk passed<' in on_tip and "not the last commit" not in on_tip
    elsewhere = page(recording={**RECORDING, "dirty": False}, git=GIT)
    assert "That is not the last commit of the build (abc1234)" in elsewhere
    for text in (elsewhere, page(recording={**RECORDING, "commit": "abc1234"}, git=GIT)):
        assert not drawn_green(text)
        assert text.count("The walk passed, on code that is not the build&#x27;s last commit") == 3  # the list, the tile and the section


@pytest.mark.parametrize("result, words", [("failed", "The walk FAILED"), ("did not run", "The walk did not run"),
                                           ("did not finish", "The walk did not finish"), (None, "The walk&#x27;s result is unknown")])
def test_a_walk_that_did_not_pass_is_never_drawn_as_passed_with_or_without_a_video(result, words):
    for megabytes in (11.2, None):
        text = page(recording={**RECORDING, "result": result, "megabytes": megabytes, "reason": "It was stopped after 15 minutes"})
        assert text.count(words) == 3 and "The walk passed" not in text and not drawn_green(text)  # the list, the tile and the section
        assert tile(text, "#recording") == ("red" if result else "amber", words)
        assert '<a href="walk-output.txt">' in text and "It was stopped after 15 minutes." in text
        assert ("<video" in text) == (megabytes is not None)
        assert ("It left no video file." in text) == (megabytes is None)
        assert "dd4ea9d" in text and "No recording" not in text
        assert "No screenshots: the walk left none." in text


def test_a_walk_that_passed_but_left_no_video_says_so():
    text = page(recording={**RECORDING, "megabytes": None})
    assert "<video" not in text and "It left no video file." in text and "MB" not in text


def test_the_walk_s_own_sentence_promises_only_what_the_walk_left():
    two, one = ["a-01-created.png", "a-02-fresh.png"], ["a-01-created.png"]
    passed = page(recording=RECORDING, shots=two)
    assert "2 moments from the acceptance walk, the whole journey by keyboard alone. Step through them, or watch the recording of all of it." in passed
    assert "Ran for 1.5 minutes" in top(passed)
    no_film = page(recording={**RECORDING, "megabytes": None}, shots=two)
    assert "Step through them." in no_film and "watch the recording" not in no_film
    failed = page(recording={**RECORDING, "result": "failed"}, shots=two)
    assert "2 moments from the acceptance walk, up to where it stopped. Step through them, or watch the recording." in failed
    assert "whole journey" not in failed and "all of it" not in failed
    assert "Ended after 1.5 minutes" in top(failed) and "Ran for" not in top(failed)
    single = page(recording={**RECORDING, "result": "failed"}, shots=one)
    assert "1 moment from the acceptance walk, up to where it stopped. The recording shows the rest." in single and "Step through them" not in single
    assert "The acceptance walk, up to where it stopped." in page(recording={**RECORDING, "result": "did not run", "megabytes": None})
    inside = page(recording=RECORDING, shots=[{"name": "a-01-created.png", "src": "data:image/png;base64,cG5n"}, {"name": "a-02-fresh.png", "src": "data:image/png;base64,cG5n"},
                                               {"name": "a-03-big.png", "src": "shots/a-03-big.png"}])
    assert inside.count('loading="lazy"') == 1 and '<img src="shots/a-03-big.png" alt="Step 3: big" loading="lazy">' in inside  # only a picture that is a file can wait


def test_the_page_loads_nothing_from_outside_and_its_one_script_is_its_own():
    text = page([finding("A"), finding("B")], fates={"A": fate("A"), "Z": fate("Z")}, git=GIT, recording={**RECORDING, "result": "failed"},
                runs=handover.run_facts([run("feature/x", "green")], "feature/x"), shots=["a-01-created.png"],
                summary={"what": ["w"], "so_what": ["s"], "now_what": ["n"]}, built={"at": "2026-11-16T21:00:00+00:00", "commit": "abc1234"})
    assert text.count("<script") == 1 and f"<script>{handover.SCRIPT}</script>" in text and "javascript:" not in text
    assert not re.search(r"fetch|XMLHttp|WebSocket|import|http|location|cookie|eval|innerHTML", handover.SCRIPT)  # it only shows and hides
    for part in ('a[href^="#group-"]', "g.open = true", "if (video.error)", "reel.scrollLeft", "ev.preventDefault()", "frames.length < 2"):
        assert part in handover.SCRIPT, part  # the script is not run here: these pin what a browser look found missing
    assert '[data-theme="dark"]' in text and ':root:not([data-theme="light"])' in text
    assert "http://" not in text and "https://" not in text and "//" not in text.replace("</", "")
    assert set(re.findall(r'(?:href|src)="([^"]*)"', text)) == {
        "#recording", "#facts", "#findings", "#finders", "#summary", "#group-0", "#group-1", "walk-output.txt", "recording.webm",
        "shots/a-01-created.png"}
    assert "prefers-color-scheme: dark" in text
    assert 'name="viewport"' in text
    assert "only you know" not in text  # blanks nobody can type in are gone


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
    assert handover.minutes(0) == "0 minutes"  # a whole number of minutes between two commits can be none
    assert handover.minutes(None) == "unknown"


# Recording the walk, with a stand-in for .venv/bin/python.

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


def test_a_walk_that_passes_leaves_its_own_video_this_run_s_screenshots_and_its_record(repo, feat, capsys):
    stand_in(repo, 0, video=True)
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == "passed" and record["returncode"] == 0 and record["walk"] == handover.WALK
    assert record["commit"] == git(repo, "rev-parse", "--short", "HEAD")
    assert (feat / "recording.webm").read_text() == "named"  # not the stray that sorts first, not the earlier one
    assert [shot.name for shot in (feat / "shots").iterdir()] == [f"{PREFIX}-02-fresh.png"]
    scratch, feature, asked = (repo / "given.txt").read_text().strip().split("|")
    assert scratch == str(feat / "recording-tmp") and feature == "feat" and handover.WALK in asked
    assert not (feat / "recording-tmp").exists()
    assert (feat / "walk-output.txt").read_text() == "what the walk printed\n"
    text = (feat / "index.html").read_text()
    assert "<video" in text and "The walk passed" in text
    assert '<img src="data:image/png;base64,cG5n" alt="Step 2: fresh">' in text and "stale" not in text  # the picture is inside the page
    assert "handover:" not in capsys.readouterr().out


@pytest.mark.parametrize("exit_code, result, words", [(1, "failed", "FAILED"), (4, "did not run", "did not run")])
def test_a_walk_that_fails_is_said_on_the_page_and_in_one_printed_line_and_the_page_is_still_built(repo, feat, capsys, exit_code, result, words):
    stand_in(repo, exit_code, video=False)
    assert handover.main(["feat"], root=repo) == 0
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == result and record["returncode"] == exit_code
    assert not (feat / "recording.webm").exists()  # the earlier run's video is gone, and the stray is not taken
    assert handover.read_recording(feat)["megabytes"] is None
    text = (feat / "index.html").read_text()
    assert f"The walk {words}" in text and "The walk passed" not in text and "<video" not in text and "0ld0ld0" not in text
    printed = capsys.readouterr().out.splitlines()
    assert printed[-2] == f"handover: the acceptance walk {words}; what it printed is in {feat / 'walk-output.txt'}"
    assert printed[-1] == f"open {feat / 'index.html'}"


def test_a_walk_that_cannot_start_or_is_stopped_leaves_no_earlier_pass_standing(repo, feat, capsys, monkeypatch):
    assert handover.main(["feat"], root=repo) == 0  # this repository has no .venv/bin/python
    record = json.loads((feat / "recording.json").read_text())
    assert record["result"] == "did not finish" and "could not start" in record["reason"]
    assert "The walk did not finish" in (feat / "index.html").read_text() and not (feat / "recording.webm").exists()
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
    assert (feat / "recording.webm").read_text() == "an earlier video"  # nothing was wiped


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
    assert handover.main(["feat", "--no-walk"], root=repo, show=opened.append) == 0
    page_file = repo / ".scratch" / "feat" / "hand-over" / "index.html"
    assert opened == [page_file.resolve().as_uri()] and opened[0].startswith("file:///")
    assert capsys.readouterr().out.splitlines()[-1] == f"open {page_file}"  # still printed, for a session that cannot open it
    assert handover.main(["feat", "--no-walk", "--no-open"], root=repo, show=opened.append) == 0 and len(opened) == 1
    capsys.readouterr()

    def broken(address):
        raise OSError("no browser")
    with pytest.raises(OSError):
        handover.main(["feat", "--no-walk"], root=repo, show=broken)
    assert capsys.readouterr().out.splitlines()[-1] == f"open {page_file}"  # printed before the browser is asked, so it is never lost


def test_the_walk_helper_records_nothing_unless_it_is_asked_to(monkeypatch):
    from walks import helper
    for value in (None, ""):
        monkeypatch.delenv("WALK_RECORD", raising=False) if value is None else monkeypatch.setenv("WALK_RECORD", value)
        assert helper.launch_options() == {} and helper.context_options(1440, 900) == {}
        assert helper.keep_video(object(), "a-walk") is None  # it never asks the page for a video
