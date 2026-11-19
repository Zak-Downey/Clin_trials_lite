"""The checks command: what it calls red, what it writes down, and the two small checks it holds itself.

The real pattern and defect-log checks run as their own checks, not from here.

Every run here is a real run of real commands in a temporary folder. Nothing runs the real suites.
"""

from __future__ import annotations

import json
import re
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


def run(tmp_path, check_list, names=(), **options):
    printed = []
    code = checks.run(names, checks=check_list, root=tmp_path, out=printed.append, **options)
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
    pid = int((tmp_path / "child.pid").read_text())
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
    assert line["dirty"] is True
    assert [c["name"] for c in line["checks"]] == ["one"]
    assert line["at"].endswith("Z") and "T" in line["at"]


def test_a_run_line_says_whether_the_run_asked_for_every_check(tmp_path):
    both = [passing("one"), passing("two")]
    _, _, runs = run(tmp_path, both)
    run(tmp_path, both, names=["one"])
    _, _, runs = run(tmp_path, both, names=["two", "one"])
    assert [line["every"] for line in runs] == [True, False, True]


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
    monkeypatch.delenv("WALK_FEATURE", raising=False)
    run(tmp_path, [says])
    assert (tmp_path / ".checks" / "says.txt").read_text() == "saved-searches\n"
    monkeypatch.setenv("WALK_FEATURE", "other")
    run(tmp_path, [says])
    assert (tmp_path / ".checks" / "says.txt").read_text() == "other\n"


def test_a_quick_run_tells_the_walks_to_use_one_window_size_and_a_plain_run_does_not(tmp_path, monkeypatch):
    says = ("says", [PY, "-c", "import os; print(os.environ.get('WALK_QUICK'))"], 1)
    monkeypatch.setenv("WALK_QUICK", "1")
    run(tmp_path, [says])
    assert (tmp_path / ".checks" / "says.txt").read_text() == "None\n"
    monkeypatch.delenv("WALK_QUICK")
    run(tmp_path, [says], quick=True)
    assert (tmp_path / ".checks" / "says.txt").read_text() == "1\n"


def test_a_quick_runs_line_says_it_was_quick_and_a_plain_runs_line_says_it_was_not(tmp_path):
    run(tmp_path, [passing()])
    _, printed, runs = run(tmp_path, [passing()], quick=True)
    assert [r["quick"] for r in runs] == [False, True]
    assert printed[-1].startswith("checks: green") and "quick" in printed[-1]


def test_quick_is_an_option_that_can_be_given_with_the_names_of_checks(monkeypatch):
    calls = []
    monkeypatch.setattr(checks, "run", lambda names=(), quick=False, pick=False: calls.append((list(names), quick)) or 0)
    checks.main(["--quick", "unit"])
    checks.main(["unit", "walks"])
    checks.main(["--quick"])
    assert calls == [(["unit"], True), (["unit", "walks"], False), ([], True)]


def git_repo(tmp_path):
    """A repo whose main holds a map of two areas and three walk files, on a branch that changed one area's file."""
    def git(*args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=tmp_path, check=True,
                       capture_output=True)
    files = {"app/a.js": "a", "app/b.js": "b", "walks/test_a.py": "", "walks/test_b.py": "", "walks/test_guards.py": "",
             ".gitignore": ".checks/\n",
             "docs/agents/local/walk-map.json": json.dumps({
                 "shared": [], "always": ["walks/test_guards.py"], "none": ["docs/*", ".gitignore"],
                 "areas": [{"name": "Page A", "files": ["app/a.js"], "walks": ["walks/test_a.py"]},
                           {"name": "Page B", "files": ["app/b.js"], "walks": ["walks/test_b.py"]}]})}
    for name, body in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(body)
    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-q", "-m", "start")
    git("checkout", "-q", "-b", "feature/thing")
    (tmp_path / "app/a.js").write_text("a changed")


def args_of(name):
    """A stand-in check that writes the arguments it was given, one a line."""
    return (name, [PY, "-c", "import sys; print('\\n'.join(sys.argv[1:]))"], 1)


def test_a_picked_run_passes_the_picked_walk_files_to_the_walk_check_and_says_how_many_of_how_many_and_why(tmp_path):
    git_repo(tmp_path)
    code, printed, runs = run(tmp_path, [args_of("unit"), args_of("walks")], pick=True)
    assert code == 0
    assert (tmp_path / ".checks" / "walks.txt").read_text().split() == ["walks/test_a.py", "walks/test_guards.py"]
    assert (tmp_path / ".checks" / "unit.txt").read_text().split() == ["--testmon-noselect"]
    said = next(line for line in printed if line.startswith("walks") and "picked" in line)
    assert "2 of 3 walk files" in said and "Page A" in said and "`app/a.js`" in said
    line = runs[-1]
    assert line["picked"] is True
    assert "where the branch left main" in line["base"]
    assert line["picks"][1:] == [{"check": "walks", "ran": 2, "of": 3, "why": said.split(": ", 1)[1]}]
    assert line["picks"][0]["check"] == "unit" and line["picks"][0]["ran"] is None
    assert "picked" in printed[-1]


def test_a_picked_run_that_reaches_every_walk_gives_the_walk_check_no_files_so_it_runs_them_all(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "lib.py").write_text("")
    _, printed, runs = run(tmp_path, [args_of("walks")], pick=True)
    assert (tmp_path / ".checks" / "walks.txt").read_text() == "\n"
    assert runs[-1]["picks"][0]["ran"] == 3 and "`lib.py`" in runs[-1]["picks"][0]["why"]


def test_a_picked_run_with_no_map_of_the_pages_runs_every_walk_and_says_so(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "docs/agents/local/walk-map.json").unlink()
    _, _, runs = run(tmp_path, [args_of("walks")], pick=True)
    assert (tmp_path / ".checks" / "walks.txt").read_text() == "\n"
    assert runs[-1]["picks"][0]["ran"] == 3 and "no map" in runs[-1]["picks"][0]["why"]


def test_a_plain_run_and_a_quick_run_are_not_picked_and_give_the_walk_check_what_they_gave_it_before(tmp_path):
    git_repo(tmp_path)
    run(tmp_path, [args_of("walks")])
    assert (tmp_path / ".checks" / "walks.txt").read_text() == "\n"
    _, printed, runs = run(tmp_path, [args_of("walks")], quick=True)
    assert (tmp_path / ".checks" / "walks.txt").read_text() == "\n"
    assert [r["picked"] for r in runs] == [False, False]
    assert not any("picked" in line for line in printed)


def counted(name, summary, there_are=12):
    """A stand-in unit check: asked to collect only, it says how many tests there are; otherwise it writes the
    arguments it was given, then a summary line as pytest -q ends with. Run across processors, pytest's summary
    leaves out the tests the picker deselected, so the stand-in's does too."""
    code = (f"import sys; print('{there_are} tests collected in 0.01s') if '--collect-only' in sys.argv "
            f"else print(' '.join(sys.argv[1:]) + '\\n' + {summary!r})")
    return (name, [PY, "-c", code], 1)


def unit_pick(tmp_path, summary="3 passed in 0.10s"):
    code, printed, runs = run(tmp_path, [counted("unit", summary)], pick=True)
    said = next(line for line in printed if line.startswith("unit") and "picked" in line)
    given = (tmp_path / ".checks" / "unit.txt").read_text().splitlines()[0].split()
    return code, said, given, runs[-1]["picks"]


def test_a_picked_run_whose_changed_files_are_all_python_lets_the_unit_check_select_and_says_how_many_of_how_many(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "app/a.js").write_text("a")
    (tmp_path / "lib.py").write_text("")
    (tmp_path / ".scratch/thing").mkdir(parents=True)
    (tmp_path / ".scratch/thing/notes.md").write_text("")
    code, said, given, picks = unit_pick(tmp_path)
    assert code == 0
    assert given == ["--testmon"]
    assert "picked 3 of 12 unit tests" in said and "`lib.py`" in said
    assert picks == [{"check": "unit", "ran": 3, "of": 12, "why": said.split(": ", 1)[1]}]


def test_a_picked_run_with_a_changed_file_that_is_not_python_runs_the_whole_unit_suite_and_says_which(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "lib.py").write_text("")
    _, said, given, picks = unit_pick(tmp_path, "12 passed in 0.30s")
    assert given == ["--testmon-noselect"]
    assert "picked 12 of 12 unit tests" in said and "whole" in said and "`app/a.js` is not Python" in said
    assert "`lib.py`" not in said
    assert picks[0]["ran"] == picks[0]["of"] == 12


def test_a_picked_run_that_cannot_tell_what_changed_runs_the_whole_unit_suite_and_says_so(tmp_path):
    _, said, given, picks = unit_pick(tmp_path, "1 failed, 11 passed, 2 skipped in 0.30s")
    assert given == ["--testmon-noselect"]
    assert "picked 14 of 14 unit tests" in said and "whole" in said and "cannot tell" in said
    assert picks[0]["why"] == said.split(": ", 1)[1]


def test_a_run_that_is_not_picked_gives_the_unit_check_the_whole_suite_and_refreshes_its_record(tmp_path):
    git_repo(tmp_path)
    for options in ({}, {"quick": True}):
        _, printed, runs = run(tmp_path, [args_of("unit")], **options)
        assert (tmp_path / ".checks" / "unit.txt").read_text().split() == ["--testmon-noselect"]
        assert runs[-1]["picks"] == [] and not any("picked" in line for line in printed)


def test_the_unit_check_keeps_pytests_cache_which_its_picker_needs():
    unit = next(command for name, command, _ in checks.CHECKS if name == "unit")
    assert "no:cacheprovider" not in unit


def test_pick_is_an_option_that_combines_with_quick_and_with_the_names_of_checks(monkeypatch):
    calls = []
    monkeypatch.setattr(checks, "run", lambda names=(), quick=False, pick=False: calls.append((list(names), quick, pick)) or 0)
    checks.main(["--quick", "--pick", "walks"])
    checks.main(["--pick"])
    checks.main(["walks"])
    assert calls == [(["walks"], True, True), ([], False, True), (["walks"], False, False)]


SELF = "assert (a, ident) == " + "(b, ident)\n"

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
    assert names == ["lint", "patterns", "escapes", "unit", "walks"]
    assert all(command for _, command, _ in checks.CHECKS)
    limits = {name: minutes for name, _, minutes in checks.CHECKS}
    assert limits == {"lint": 1, "patterns": 1, "escapes": 1, "unit": 3, "walks": 8}


def test_the_unit_check_runs_the_suite_across_the_processors_the_machine_has():
    unit = next(command for name, command, _ in checks.CHECKS if name == "unit")
    assert unit[unit.index("-m") + 1] == "pytest"
    assert unit[unit.index("-n") + 1] == "auto"


def test_the_unit_picker_is_pinned_to_one_exact_version_and_its_record_is_never_tracked():
    lines = (checks.ROOT / "requirements-dev.txt").read_text().splitlines()
    testmon = [line for line in lines if line.startswith("pytest-testmon")]
    assert len(testmon) == 1 and re.fullmatch(r"pytest-testmon==\d+\.\d+\.\d+", testmon[0]), testmon
    for record in (".testmondata", ".testmondata-shm", ".testmondata-wal"):
        ignored = subprocess.run(["git", "check-ignore", "-q", "--no-index", record], cwd=checks.ROOT)
        assert ignored.returncode == 0, f"{record} is not git-ignored"


WAITED_ON = 10
NUMBERS = {"five": 5, "ten": 10, "twelve": 12, "thirteen": 13, "fifteen": 15, "twenty": 20, "thirty": 30}


def test_the_repo_notes_say_to_run_a_whole_run_in_the_background_when_it_can_outlast_a_waited_on_command():
    notes = (checks.ROOT / "docs" / "agents" / "local" / "repo.md").read_text()
    every = next(line for line in notes.splitlines() if line.startswith("- **Every check.**"))
    if sum(minutes for _, _, minutes in checks.CHECKS) > WAITED_ON:
        assert "in the background" in every
    stated = [int(n) if n.isdigit() else NUMBERS.get(n.lower(), 999)
              for n in re.findall(r"(\w+)[- ]minute timeout", notes)]
    assert all(minutes <= WAITED_ON for minutes in stated), stated


def lint_copy(tmp_path, code):
    (tmp_path / "ruff.toml").write_text((checks.ROOT / "ruff.toml").read_text())
    (tmp_path / "app.py").write_text(code)
    lint = next(check for check in checks.CHECKS if check[0] == "lint")
    return run(tmp_path, [lint, passing("later")])


def test_the_lint_check_is_red_on_an_unused_import_and_the_run_stops_there(tmp_path):
    code, printed, runs = lint_copy(tmp_path, "import os\n")
    assert code == 1
    assert [(c["name"], c["result"]) for c in runs[-1]["checks"]] == [("lint", "red"), ("later", "not run")]
    assert "F401" in (tmp_path / ".checks" / "lint.txt").read_text()


def test_the_lint_check_is_green_on_clean_code_and_leaves_no_file_behind(tmp_path):
    code, _, runs = lint_copy(tmp_path, "import os\n\nprint(os.sep)\n")
    assert code == 0
    assert [(c["name"], c["result"]) for c in runs[-1]["checks"]] == [("lint", "green"), ("later", "green")]
    assert sorted(p.name for p in tmp_path.iterdir()) == [".checks", "app.py", "ruff.toml"]


def test_the_every_check_line_of_repo_md_names_the_checks_in_CHECKS_in_order():
    numbers = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
    text = (checks.ROOT / "docs" / "agents" / "local" / "repo.md").read_text()
    line = next(line for line in text.splitlines() if line.startswith("- **Every check.**"))
    said, listed = re.search(r"runs (\w+) checks, cheapest first, stopping at the first red: (.*?); the list is", line).groups()
    names = [name for name, _, _ in checks.CHECKS]
    assert re.findall(r"`(\w+)`", listed) == names
    assert said == numbers[len(names)]


def test_the_checks_line_of_claude_md_lists_one_phrase_for_each_check_in_CHECKS_in_order():
    words = {"lint": "common mistakes", "patterns": "pattern", "escapes": "defect log", "unit": "unit", "walks": "walks"}
    text = (checks.ROOT / "CLAUDE.md").read_text()
    line = next(line for line in text.splitlines() if line.startswith("- **Checks.**"))
    listed = re.search(r"runs every check \(([^)]*)\)", line).group(1).split(", ")
    names = [name for name, _, _ in checks.CHECKS]
    assert len(listed) == len(names)
    assert [words[name] in phrase for name, phrase in zip(names, listed)] == [True] * len(names)


def tracked(tmp_path, files):
    """A repo in a temporary folder whose files are all added to git."""
    for name, body in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(body)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)


def test_a_python_comment_on_its_own_line_or_after_code_is_listed_with_its_file_line_and_text(tmp_path):
    tracked(tmp_path, {"app/x.py": "x = 1\n# on its own\ny = 2  # after code\n"})
    assert checks.comment_hits(tmp_path) == ["app/x.py:2: # on its own", "app/x.py:3: # after code"]


def test_a_hash_in_a_string_a_hashbang_first_line_and_a_linter_directive_with_its_reason_are_not_comments(tmp_path):
    tracked(tmp_path, {"run.py": "#!/usr/bin/env python3\ns = '# not one'\nt = \"\"\"# nor this\"\"\"\n"
                                 "import os  # " "noqa: F401 kept for the caller that imports it from here\n"})
    assert checks.comment_hits(tmp_path) == []


def test_a_linter_directive_with_no_reason_or_more_than_one_rule_is_listed(tmp_path):
    tracked(tmp_path, {"x.py": "import os  # " "noqa: F401\nimport re  # " "noqa\nimport io  # " "noqa: F401,E402 both\n"})
    assert checks.comment_hits(tmp_path) == ["x.py:1: # " "noqa: F401", "x.py:2: # " "noqa",
                                             "x.py:3: # " "noqa: F401,E402 both"]


def test_a_python_file_git_does_not_track_or_under_scratch_is_never_read(tmp_path):
    tracked(tmp_path, {".scratch/f/x.py": "# a record\n"})
    (tmp_path / "loose.py").write_text("# not tracked\n")
    assert checks.comment_hits(tmp_path) == []


def test_a_script_style_sheet_or_page_under_static_holding_a_comment_is_listed(tmp_path):
    tracked(tmp_path, {"webapp/static/a.js": "let a = 1;\n// on its own\nlet b = 2; /* after */\n",
                       "webapp/static/views/s.css": "p { color: red; } /* why */\n",
                       "webapp/static/index.html": "<p>hi</p>\n<!-- a note -->\n"})
    assert checks.comment_hits(tmp_path) == ["webapp/static/a.js:2: // on its own", "webapp/static/a.js:3: /* after */",
                                             "webapp/static/index.html:2: <!-- a note -->",
                                             "webapp/static/views/s.css:1: /* why */"]


def test_a_script_style_sheet_or_page_without_one_is_not_listed_nor_is_a_script_outside_static(tmp_path):
    tracked(tmp_path, {"webapp/static/a.js": "let a = 1 / 2;\n", "webapp/static/s.css": "p { color: red; }\n",
                       "webapp/static/index.html": "<p>a / b</p>\n", "other/b.js": "// elsewhere\n",
                       ".scratch/f/webapp/static/c.js": "// a record\n"})
    assert checks.comment_hits(tmp_path) == []


def test_in_a_folder_git_cannot_list_every_file_outside_scratch_and_tool_folders_is_read(tmp_path):
    files = {"a.py": "x = 1  # in a copy with no git\n", "webapp/static/a.js": "// a script's\n",
             ".github/b.py": "# under a dotted folder\n", ".scratch/f/c.py": "# a record\n",
             ".venv/lib/d.py": "# a tool's\n", "__pycache__/e.py": "# a cache's\n"}
    for name, body in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(body)
    assert checks.comment_hits(tmp_path) == [".github/b.py:1: # under a dotted folder",
                                             "a.py:1: # in a copy with no git", "webapp/static/a.js:1: // a script's"]


def test_the_comments_command_lists_each_comment_then_the_total_and_ends_zero(tmp_path, monkeypatch, capsys):
    tracked(tmp_path, {"a.py": "# one\n", "b.py": "x = 1  # two\n# three\n"})
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    assert checks.main(["--comments"]) == 0
    assert capsys.readouterr().out.splitlines() == ["a.py:1: # one", "b.py:1: # two", "b.py:2: # three",
                                                     "3 comments in 2 files"]


ADVICE = "say it in a name, or in a test that fails without it; a comment is checked by nothing"


def test_a_comment_in_python_or_in_a_script_turns_the_patterns_check_red_naming_its_file_and_line(tmp_path, monkeypatch, capsys):
    tracked(tmp_path, {"app/x.py": "x = 1\ny = 2  # after code\n", "webapp/static/a.js": "let a = 1;\n\n// on its own\n"})
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(checks, "pattern_hits", lambda: [])
    assert checks.main(["--patterns"]) == 1
    printed = capsys.readouterr().out.splitlines()
    assert printed == [f"app/x.py:2: {ADVICE} (# after code)", f"webapp/static/a.js:3: {ADVICE} (// on its own)"]


def test_without_a_comment_the_patterns_check_is_green(tmp_path, monkeypatch):
    tracked(tmp_path, {"app/x.py": "x = '# not one'\n", "webapp/static/a.js": "let a = 1 / 2;\n"})
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(checks, "pattern_hits", lambda: [])
    assert checks.main(["--patterns"]) == 0


def kept(*entries):
    return {"docs/agents/local/comments-kept.json": json.dumps(list(entries))}


def patterns_check(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(checks, "pattern_hits", lambda: [])
    code = checks.main(["--patterns"])
    return code, capsys.readouterr().out.splitlines()


def test_a_kept_comment_is_let_through_by_the_patterns_check_and_by_the_count(tmp_path, monkeypatch, capsys):
    tracked(tmp_path, {"app/x.py": "x = 1  # the registry counts from one\n",
                       **kept({"file": "app/x.py", "text": "# the registry counts from one",
                               "why": "No name can say which number the registry starts from."})})
    assert patterns_check(tmp_path, monkeypatch, capsys)[0] == 0
    assert checks.main(["--comments"]) == 0
    assert capsys.readouterr().out.splitlines() == ["0 comments in 0 files"]


def test_a_kept_entry_whose_text_is_no_longer_in_its_file_is_reported(tmp_path, monkeypatch, capsys):
    tracked(tmp_path, {"app/x.py": "x = 1\n", **kept({"file": "app/x.py", "text": "# gone", "why": "It was needed."})})
    code, printed = patterns_check(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert printed == ["docs/agents/local/comments-kept.json: entry 1 keeps `# gone`, which is no longer a comment in "
                       "app/x.py: remove the entry"]


def test_a_kept_entry_with_a_field_missing_is_reported(tmp_path, monkeypatch, capsys):
    tracked(tmp_path, {"app/x.py": "x = 1  # here\n", **kept({"file": "app/x.py", "text": "# here"})})
    code, printed = patterns_check(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert printed == ["docs/agents/local/comments-kept.json: entry 1 needs a `file`, the comment's exact `text` and "
                       "`why` it must stay", f"app/x.py:1: {ADVICE} (# here)"]


def test_the_kept_list_has_a_ceiling_of_ten_and_an_eleventh_entry_is_reported(tmp_path, monkeypatch, capsys):
    assert checks.KEPT_CEILING == 10
    lines = [f"x{n} = {n}  # kept {n}\n" for n in range(11)]
    entries = [{"file": "app/x.py", "text": f"# kept {n}", "why": "It must stay."} for n in range(11)]
    tracked(tmp_path, {"app/x.py": "".join(lines), **kept(*entries[:10])})
    assert patterns_check(tmp_path, monkeypatch, capsys) == (1, [f"app/x.py:11: {ADVICE} (# kept 10)"])
    tracked(tmp_path, kept(*entries))
    assert patterns_check(tmp_path, monkeypatch, capsys) == (1, [
        "docs/agents/local/comments-kept.json: 11 entries, over the ceiling of 10: say the rest in a name or a test"])


def test_a_kept_list_that_is_not_a_json_list_is_reported(tmp_path, monkeypatch, capsys):
    tracked(tmp_path, {"app/x.py": "x = 1\n", "docs/agents/local/comments-kept.json": "{}"})
    code, printed = patterns_check(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert printed == ["docs/agents/local/comments-kept.json: not a JSON list"]


def test_this_repo_holds_no_comment_the_rule_does_not_let_through_and_its_kept_list_reads():
    assert (checks.ROOT / checks.KEPT).is_file()
    assert checks.comment_faults(checks.ROOT) == []
