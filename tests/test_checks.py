"""The checks command: what it calls red, what it writes down, and the two small checks it holds itself.

The real pattern and defect-log checks run as their own checks, not from here.

Every run here is a real run of real commands in a temporary folder. Nothing runs the real suites.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import checks

PY = sys.executable


def passing(name="ok"):
    return (name, [PY, "-c", "print('fine')"], 1)


def failing(name="bad"):
    return (name, [PY, "-c", "import sys; sys.stderr.write('noise\\n' * 30 + 'the reason it failed\\n'); sys.exit(3)"], 1)


def run(tmp_path, check_list, names=()):
    printed = []
    code = checks.run(names, checks=check_list, root=tmp_path, out=printed.append)
    lines = (tmp_path / ".checks" / "runs.jsonl").read_text().splitlines() if (tmp_path / ".checks" / "runs.jsonl").is_file() else []
    return code, printed, [json.loads(line) for line in lines]


def test_a_run_where_every_check_passes_is_green_and_exits_zero(tmp_path):
    code, printed, runs = run(tmp_path, [passing("one"), passing("two")])
    assert code == 0
    assert printed[-1].startswith("checks: green")
    assert [c["result"] for c in runs[-1]["checks"]] == ["green", "green"]
    assert runs[-1]["result"] == "green"


def test_a_check_that_exits_non_zero_is_red_and_the_run_exits_one(tmp_path):
    code, printed, runs = run(tmp_path, [failing()])
    assert code == 1
    assert runs[-1]["result"] == "red"
    assert printed[-1].startswith("checks: red (bad)")


def test_red_is_decided_by_the_exit_code_not_by_what_the_check_printed(tmp_path):
    says_failed_but_passes = ("liar", [PY, "-c", "print('FAILED 3 failed ERROR')"], 1)
    says_passed_but_fails = ("quiet", [PY, "-c", "import sys; print('472 passed'); sys.exit(1)"], 1)
    assert run(tmp_path, [says_failed_but_passes])[0] == 0
    assert run(tmp_path, [says_passed_but_fails])[0] == 1


def test_a_check_that_runs_past_its_time_is_stopped_and_red(tmp_path):
    child = "import os, time; open('child.pid', 'w').write(str(os.getpid())); time.sleep(30)"
    slow = ("slow", [PY, "-c", f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(30)"], 0.01)
    code, _, runs = run(tmp_path, [slow])
    pid = int((tmp_path / "child.pid").read_text())  # also shows the check ran in the root
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        raise AssertionError("the check's own child outlived the timeout")
    assert code == 1
    assert runs[-1]["checks"][0]["result"] == "red"
    assert runs[-1]["minutes"] < 0.3
    assert "stopped after 0.01 minutes" in (tmp_path / ".checks" / "slow.txt").read_text()


def test_a_check_whose_command_cannot_start_is_red_not_a_crash(tmp_path):
    code, _, runs = run(tmp_path, [("gone", [str(tmp_path / "no-such-program")], 1)])
    assert code == 1
    assert runs[-1]["checks"][0]["result"] == "red"


def test_each_check_writes_its_output_to_its_own_file(tmp_path):
    run(tmp_path, [passing("one"), failing("two")])
    assert (tmp_path / ".checks" / "one.txt").read_text() == "fine\n"
    assert "the reason it failed" in (tmp_path / ".checks" / "two.txt").read_text()


def test_the_end_of_a_red_checks_output_is_printed_so_the_reason_is_in_view(tmp_path):
    _, printed, _ = run(tmp_path, [failing()])
    assert any("the reason it failed" in line for line in printed)


def test_checks_after_a_red_one_are_not_run_and_are_recorded_as_not_run(tmp_path):
    marker = tmp_path / "ran"
    later = ("later", [PY, "-c", f"open({str(marker)!r}, 'w').close()"], 1)
    _, printed, runs = run(tmp_path, [failing("first"), later])
    assert not marker.exists()
    assert runs[-1]["checks"][1] == {"name": "later", "result": "not run", "minutes": 0.0, "output": ".checks/later.txt"}
    assert "later     not run (first was red)" in printed


def test_every_run_appends_one_line_and_never_rewrites_the_earlier_ones(tmp_path):
    run(tmp_path, [passing()])
    run(tmp_path, [failing()])
    _, _, runs = run(tmp_path, [passing()])
    assert [r["result"] for r in runs] == ["green", "red", "green"]


def test_a_run_line_says_when_and_where_and_names_only_the_checks_asked_for(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "feature/thing"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "start"],
                   cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text(".checks/\n")
    _, _, runs = run(tmp_path, [passing("one"), passing("two")], names=["one"])
    line = runs[-1]
    assert line["branch"] == "feature/thing"
    assert len(line["tip"]) >= 7
    assert line["dirty"] is True  # the untracked .gitignore
    assert [c["name"] for c in line["checks"]] == ["one"]
    assert line["at"].endswith("Z") and "T" in line["at"]


def test_naming_a_check_that_does_not_exist_runs_nothing_and_says_which_exist(tmp_path):
    code, printed, runs = run(tmp_path, [passing("one")], names=["oen"])
    assert code == 2
    assert runs == []
    assert "no check named oen" in printed[0] and "one" in printed[0]


def test_the_walks_write_to_the_branchs_feature_folder_when_there_is_one(tmp_path):
    (tmp_path / ".scratch" / "saved-searches").mkdir(parents=True)
    assert checks.walk_feature("feature/saved-searches", tmp_path) == "saved-searches"
    assert checks.walk_feature("main", tmp_path) is None


def test_a_check_is_told_the_feature_folder_unless_the_caller_already_named_one(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", "-b", "feature/saved-searches"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "start"],
                   cwd=tmp_path, check=True)
    (tmp_path / ".scratch" / "saved-searches").mkdir(parents=True)
    says = ("says", [PY, "-c", "import os; print(os.environ.get('WALK_FEATURE'))"], 1)
    monkeypatch.delenv("WALK_FEATURE", raising=False)  # checks.py sets it for the unit check on a feature branch
    run(tmp_path, [says])
    assert (tmp_path / ".checks" / "says.txt").read_text() == "saved-searches\n"
    monkeypatch.setenv("WALK_FEATURE", "other")
    run(tmp_path, [says])
    assert (tmp_path / ".checks" / "says.txt").read_text() == "other\n"


SELF = "assert (a, ident) == " + "(b, ident)\n"  # in two halves, so this file does not match the pattern itself

SELF_COMPARE = [{"rule": "R-005", "why": "compares a value with itself", "globs": ["tests/**/*.py"],
                 "pattern": checks.PATTERNS[0]["pattern"]}]


def test_a_line_matching_a_forbidden_pattern_is_named_with_its_file_line_and_rule(tmp_path):
    (tmp_path / "tests" / "deep").mkdir(parents=True)
    (tmp_path / "tests" / "deep" / "test_x.py").write_text("x = 1\n" + SELF)
    (tmp_path / "tests" / "test_fine.py").write_text("assert (a, got) == (b, wanted)\n")
    assert checks.pattern_hits(SELF_COMPARE, tmp_path) == ["tests/deep/test_x.py:2: R-005: compares a value with itself"]


def test_a_pattern_only_looks_at_the_files_its_globs_name(tmp_path):
    (tmp_path / "webapp").mkdir()
    (tmp_path / "webapp" / "x.py").write_text(SELF)
    assert checks.pattern_hits(SELF_COMPARE, tmp_path) == []


def test_the_patterns_check_is_red_on_a_hit_and_prints_it(tmp_path, monkeypatch, capsys):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(SELF)
    real = checks.pattern_hits
    monkeypatch.setattr(checks, "pattern_hits", lambda: real(SELF_COMPARE, tmp_path))
    assert checks.main(["--patterns"]) == 1
    assert "tests/test_x.py:1: R-005" in capsys.readouterr().out
    (tmp_path / "tests" / "test_x.py").write_text("x = 1\n")
    assert checks.main(["--patterns"]) == 0


def escapes(tmp_path, *rows):
    (tmp_path / "log.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    return checks.escape_problems("log.jsonl", tmp_path, required_from="2026-11-17")


def test_a_new_defect_line_must_name_a_check_file_that_exists(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_real.py").write_text("")
    assert escapes(tmp_path, {"id": "E-1", "date": "2026-11-17", "check": "tests/test_real.py::test_it"}) == []
    assert escapes(tmp_path, {"id": "E-1", "date": "2026-11-17", "check": "tests/test_real.py"}) == []
    assert len(escapes(tmp_path, {"id": "E-1", "date": "2026-11-17", "check": "tests/test_gone.py::test_it"})) == 1
    assert len(escapes(tmp_path, {"id": "E-1", "date": "2026-11-17"})) == 1
    assert len(escapes(tmp_path, {"id": "E-1", "date": "2026-12-01", "check": ""})) == 1


def test_defect_lines_from_before_the_rule_need_no_check(tmp_path):
    assert escapes(tmp_path, {"id": "E-1", "date": "2026-11-09"}) == []


def test_a_defect_line_that_is_not_json_or_repeats_an_id_is_a_problem(tmp_path):
    (tmp_path / "log.jsonl").write_text('{"id": "E-1", "date": "2026-11-09"}\nnot json\n{"id": "E-1", "date": "2026-11-09"}\n{"date": "2026-11-09"}\n')
    problems = checks.escape_problems("log.jsonl", tmp_path)
    assert [line.split(": ")[0] for line in problems] == ["log.jsonl:2", "log.jsonl:3", "log.jsonl:4"]


def test_a_missing_defect_log_is_a_problem_not_a_pass(tmp_path):
    assert checks.escape_problems("log.jsonl", tmp_path) == ["log.jsonl: missing"]


def test_a_defect_line_with_no_date_or_a_date_in_another_shape_is_a_problem(tmp_path):
    assert len(escapes(tmp_path, {"id": "E-1"})) == 1
    assert len(escapes(tmp_path, {"id": "E-1", "date": "17/11/2026", "check": ""})) == 1
    assert len(escapes(tmp_path, {"id": "E-1", "date": "2026-11-17T09:00:00Z"})) == 1


def test_the_escapes_check_is_red_on_a_problem_and_prints_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checks, "escape_problems", lambda: ["log.jsonl:2: not JSON"])
    assert checks.main(["--escapes"]) == 1
    assert "log.jsonl:2: not JSON" in capsys.readouterr().out
    monkeypatch.setattr(checks, "escape_problems", lambda: [])
    assert checks.main(["--escapes"]) == 0


def test_every_check_this_repo_lists_has_a_name_a_command_and_a_time_limit():
    names = [name for name, _, _ in checks.CHECKS]
    assert names == ["patterns", "escapes", "unit", "walks"]
    assert all(command and minutes > 0 for _, command, minutes in checks.CHECKS)
