"""handover.py: the one page a build ends with.

These test the parts that read and compute, and that the page escapes what it is
given. Git facts come from a small real repository made in a temporary folder.
Lacks: the recorded walk itself (a browser run; `handover.py` is run for real for that).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess

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


# Joining findings to fates.

def test_a_finding_with_no_fate_line_is_grouped_first_under_no_fate_recorded():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C")],
        {"A": fate("A"), "C": fate("C", "left", check="")},
    )
    groups = handover.group_by_state(joined)
    assert [state for state, _ in groups][0] == "no-fate"
    assert [f["id"] for f in groups[0][1]] == ["B"]
    assert handover.STATES["no-fate"] == "No fate recorded"


def test_a_fixed_fate_that_names_no_check_is_marked_fixed_no_check_named():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C")],
        {"A": fate("A"), "B": fate("B", check=""), "C": fate("C", check="   ")},
    )
    assert {f["id"]: f["state"] for f in joined} == {"A": "fixed", "B": "fixed-no-check", "C": "fixed-no-check"}
    assert handover.STATES["fixed-no-check"] == "Fixed, no check named"


def test_left_and_not_a_defect_keep_their_own_groups_after_the_unresolved_ones():
    joined = handover.join(
        [finding("A"), finding("B"), finding("C"), finding("D"), finding("E")],
        {"A": fate("A"), "B": fate("B", "not-a-defect"), "C": fate("C", "left"), "D": fate("D", check="")},
    )
    assert [(state, [f["id"] for f in rows]) for state, rows in handover.group_by_state(joined)] == [
        ("no-fate", ["E"]), ("left", ["C"]), ("fixed-no-check", ["D"]), ("fixed", ["A"]), ("not-a-defect", ["B"])]


def test_a_fate_whose_id_matches_no_finding_is_reported_not_dropped():
    assert handover.orphan_fates([finding("A")], {"A": fate("A"), "Z": fate("Z")}) == ["Z"]


# Counting by finder and pass.

def test_findings_are_counted_by_finder_with_first_pass_and_recheck_apart():
    rows = [finding("1"), finding("2"), finding("3", round="recheck"),
            finding("4", "review"), finding("5", "you", "recheck")]
    counts = handover.count_by_finder(rows)
    assert counts["walker"] == {"first": 2, "recheck": 1}
    assert counts["review"] == {"first": 1, "recheck": 0}
    assert counts["you"] == {"first": 0, "recheck": 1}
    assert counts["early-read"] == {"first": 0, "recheck": 0}
    assert list(counts)[:4] == ["walker", "review", "early-read", "you"]


def test_a_finder_the_contract_does_not_name_is_still_counted():
    counts = handover.count_by_finder([finding("1", "a-stranger")])
    assert counts["a-stranger"] == {"first": 1, "recheck": 0}


# Reading the record files.

def test_findings_are_read_from_every_jsonl_file_in_the_folder_and_fates_by_id(tmp_path):
    feature = tmp_path / ".scratch" / "feat"
    write_lines(feature / "findings" / "walker.jsonl", [finding("W-1"), finding("W-2")])
    write_lines(feature / "findings" / "review.jsonl", [finding("R-1", "review")])
    write_lines(feature / "fates.jsonl", [fate("W-1")])
    assert [f["id"] for f in handover.read_findings(feature)] == ["R-1", "W-1", "W-2"]
    assert list(handover.read_fates(feature)) == ["W-1"]


def test_missing_record_files_read_as_nothing_and_a_broken_line_names_its_file_and_line(tmp_path):
    feature = tmp_path / ".scratch" / "feat"
    assert handover.read_findings(feature) == []
    assert handover.read_fates(feature) == {}
    assert handover.read_summary(feature) is None
    bad = feature / "fates.jsonl"
    bad.parent.mkdir(parents=True)
    bad.write_text('{"id": "A", "fate": "fixed"}\n\nnot json\n', encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        handover.read_fates(feature)
    assert "fates.jsonl" in str(stopped.value) and "line 3" in str(stopped.value)


# The checks run log.

def run(branch, result, at="2026-11-16T10:00:00Z", **more):
    return {"at": at, "branch": branch, "tip": "abc1234", "dirty": False, "result": result, "minutes": 2.5,
            "checks": [{"name": "unit", "result": result, "minutes": 0.5, "output": ".checks/unit.txt"}], **more}


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
    assert facts["last"]["at"] == "2026-11-16T10:20:00Z" and facts["last"]["result"] == "green"
    assert facts["why_unknown"] == ""


def test_an_absent_run_log_is_unknown_never_zero(tmp_path):
    runs = handover.read_runs(tmp_path / ".checks" / "runs.jsonl")
    assert runs is None
    facts = handover.run_facts(runs, "feature/x")
    assert facts["red"] is None and facts["runs"] is None and facts["last"] is None
    assert "does not exist" in facts["why_unknown"]


def test_a_run_log_with_no_line_for_this_branch_is_unknown_never_zero(tmp_path):
    log = write_lines(tmp_path / "runs.jsonl", [run("feature/other", "red")])
    facts = handover.run_facts(handover.read_runs(log), "feature/x")
    assert facts["red"] is None and facts["last"] is None
    assert "feature/x" in facts["why_unknown"]


def test_unknown_run_facts_are_written_as_unknown_on_the_page():
    page = handover.render(handover.page_data("feat", runs=handover.run_facts(None, "feature/x")))
    assert "Red check runs" in page
    assert "unknown" in page.lower()
    assert "does not exist" in page


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
    """main: one commit. feature: three commits over 90 minutes, adding 3 tests and removing 1 line."""
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
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "third", when="2026-11-02T10:30:00+00:00")
    return root


def test_git_facts_count_commits_time_files_lines_and_tests_added(repo):
    facts = handover.git_facts(repo, "main", "feature/x")
    assert facts["commits"] == 3
    assert handover.when(facts["first"]) == "2 Nov 2026, 09:00 UTC"
    assert handover.when(facts["last"]) == "2 Nov 2026, 10:30 UTC"
    assert facts["minutes"] == 90
    assert facts["files"] == 5  # app.py, tests/test_new.py, walks/test_walk.py, notes.py, walks/helper.py
    assert facts["added"] == 2 + 6 + 2 + 2 + 2
    assert facts["removed"] == 1
    assert facts["tests_added"] == 3  # test_a, test_b, test_walk_it; not notes.py, not the string
    assert facts["base"] == git(repo, "rev-parse", "--short", "main")
    assert facts["tip"] == git(repo, "rev-parse", "--short", "feature/x")


def test_git_facts_of_an_empty_range_leave_the_times_unknown(repo):
    facts = handover.git_facts(repo, "feature/x", "feature/x")
    assert facts["commits"] == 0
    assert facts["first"] is None and facts["last"] is None and facts["minutes"] is None


def test_the_script_run_on_a_real_repository_writes_the_page_and_ends_with_the_open_command(repo, capsys):
    feature = repo / ".scratch" / "feat"
    write_lines(feature / "findings" / "walker.jsonl", [finding("W-1"), finding("W-2")])
    write_lines(feature / "fates.jsonl", [fate("W-1")])
    write_lines(repo / ".checks" / "runs.jsonl", [run("feature/x", "red"), run("feature/x", "green"), run("main", "red")])
    assert handover.main(["feat", "--base", "main", "--tip", "feature/x", "--no-walk"], root=repo) == 0
    page = feature / "hand-over" / "index.html"
    assert capsys.readouterr().out.splitlines()[-1] == f"open {page}"
    text = page.read_text(encoding="utf-8")
    assert "No recording" in text and "<video" not in text  # --no-walk and no earlier recording
    assert "1 of 2 runs" in text  # the red runs of feature/x, the branch the repository is on
    assert "No fate recorded" in text and text.index("W-2") < text.index("W-1")
    assert "hand-over.json is missing" in text


def test_a_feature_with_no_folder_stops_the_run(repo):
    with pytest.raises(SystemExit) as stopped:
        handover.main(["nothing-here", "--no-walk"], root=repo)
    assert "no feature folder" in str(stopped.value)


def test_tests_added_counts_only_added_def_test_lines():
    diff = "\n".join([
        "+++ b/tests/test_a.py",
        "+def test_one():",
        "+    async def test_two(self):",
        "-def test_removed():",
        " def test_context():",
        "+    x = 'def test_three'",
        "+def testing():",
    ])
    assert handover.tests_added(diff) == 2


# The page.

HOSTILE = '<script>alert("x")</script> & <img src=x onerror=1>'


def test_a_hostile_string_in_a_finding_is_escaped_everywhere_it_is_drawn():
    findings = [finding(HOSTILE, finder=HOSTILE, area=HOSTILE, severity=HOSTILE, what=HOSTILE, where=HOSTILE, check=HOSTILE)]
    fates = {HOSTILE: fate(HOSTILE, commit=HOSTILE, check=HOSTILE, why=HOSTILE)}
    page = handover.render(handover.page_data(
        "feat", findings=findings, fates=fates,
        summary={"what": [HOSTILE], "so_what": [HOSTILE], "now_what": [HOSTILE]},
        shots=[HOSTILE + ".png"],
    ))
    assert "<script>" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &lt;img src=x onerror=1&gt;" in page


def test_the_page_puts_no_fate_recorded_before_every_other_group_and_marks_an_unchecked_fix():
    findings = [finding("FIXED-1"), finding("NOFATE-1"), finding("NOCHECK-1")]
    fates = {"FIXED-1": fate("FIXED-1"), "NOCHECK-1": fate("NOCHECK-1", check="")}
    page = handover.render(handover.page_data("feat", findings=findings, fates=fates))
    assert "No fate recorded" in page and "Fixed, no check named" in page
    assert page.index("NOFATE-1") < page.index("NOCHECK-1") < page.index("FIXED-1")


def test_the_page_labels_what_an_agent_wrote_and_what_the_script_computed():
    page = handover.render(handover.page_data(
        "feat", summary={"what": ["Built the thing."], "so_what": ["It matters."], "now_what": ["Decide."]}))
    assert "Written by the build agent" in page
    assert "Computed by handover.py" in page
    assert page.index("Written by the build agent") < page.index("Computed by handover.py")
    assert "Built the thing." in page and "It matters." in page and "Decide." in page


def test_the_page_says_so_when_there_is_no_summary_no_recording_and_no_findings():
    page = handover.render(handover.page_data("feat"))
    assert "<video" not in page
    assert "No recording" in page
    assert "hand-over.json" in page  # names the missing summary file
    assert "No findings were recorded" in page


def test_the_page_names_the_commit_the_recording_was_made_on_and_shows_the_video():
    recording = {"walk": "walks/test_acceptance_walk.py::test_x", "at": "2026-11-16T21:00:00+00:00",
                 "commit": "dd4ea9d", "dirty": True, "result": "passed", "minutes": 1.5, "megabytes": 11.2}
    page = handover.render(handover.page_data("feat", recording=recording, shots=["a-01-created.png"]))
    assert '<video controls' in page and 'src="recording.webm"' in page
    assert "dd4ea9d" in page and "uncommitted changes" in page
    assert 'src="shots/a-01-created.png"' in page


def test_the_page_needs_nothing_from_outside_and_no_script():
    page = handover.render(handover.page_data(
        "feat", findings=[finding("A")], fates={"A": fate("A")},
        summary={"what": ["w"], "so_what": ["s"], "now_what": ["n"]}))
    assert "<script" not in page
    assert "http://" not in page and "https://" not in page
    assert "prefers-color-scheme: dark" in page
    assert 'name="viewport"' in page
    assert "Messages I typed during the run" in page and "Minutes I spent on this page" in page


def test_times_are_written_in_utc_whatever_zone_they_were_recorded_in():
    assert handover.when("2026-11-08T16:20:11Z") == "8 Nov 2026, 16:20 UTC"
    assert handover.when("2026-10-01T19:32:28+01:00") == "1 Oct 2026, 18:32 UTC"
    assert handover.when(None) == "unknown"
    assert handover.when("last Tuesday") == "last Tuesday"


def test_durations_are_written_in_minutes():
    assert handover.minutes(851) == "851 minutes"
    assert handover.minutes(1) == "1 minute"
    assert handover.minutes(2.5) == "2.5 minutes"
    assert handover.minutes(None) == "unknown"
