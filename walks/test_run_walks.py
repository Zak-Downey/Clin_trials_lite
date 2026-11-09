"""The walk runner's reading of a pytest run. No browser. Lacks: a real browser walk;
the re-run is shown on two tiny pytest files, not on the app."""

import pathlib
import re
import sys

from walks import run_walks

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / ".claude" / "factory"))
from gate import checks  # noqa: E402  the gate's reader of the runner's output


def test_runner_lists_a_walk_that_erred_in_setup_as_well_as_one_that_failed():
    """test_runner_lists_a_walk_that_erred_in_setup_as_well_as_one_that_failed"""
    text = (
        "FAILED walks/test_a.py::test_flaky[1440x900] - boom\n"
        "ERROR walks/test_b.py::test_no_app[1440x900] - RuntimeError: the app did not start\n"
        "1 failed, 1 error in 3s\n"
    )
    assert run_walks.red_walks(text) == [
        "walks/test_a.py::test_flaky[1440x900]", "walks/test_b.py::test_no_app[1440x900]"]


def test_runner_is_red_when_a_walk_is_red_alone_and_when_a_run_failed_with_nothing_to_re_run():
    """test_runner_is_red_when_a_walk_is_red_alone_and_when_a_run_failed_with_nothing_to_re_run"""
    assert run_walks.exit_code(1, ["a -- red alone (x)", "b -- red under load, green alone (y)"]) == 1
    assert run_walks.exit_code(1, ["b -- red under load, green alone (y)"]) == 0
    assert run_walks.exit_code(2, []) == 2
    assert run_walks.exit_code(0, []) == 0


def test_runner_reports_red_alone_and_red_under_load_green_alone_in_one_run(tmp_path, capsys):
    """test_runner_reports_red_alone_and_red_under_load_green_alone_in_one_run"""
    (tmp_path / "test_always.py").write_text("def test_always():\n    assert False\n")
    (tmp_path / "test_once.py").write_text(
        "import pathlib\n"
        "def test_once():\n"
        "    m = pathlib.Path(__file__).with_name('seen')\n"
        "    first = not m.exists()\n"
        "    m.write_text('x')\n"
        "    assert not first\n"
        "def test_bystander():\n"
        "    assert True\n")
    code = run_walks.main([], targets=(str(tmp_path),), cwd=tmp_path, shots=tmp_path / "out")
    out = capsys.readouterr().out
    result = out.split("## Result")[1]
    assert re.search(r"test_always\.py \u203a test_always: red alone", result)
    assert re.search(r"test_once\.py \u203a test_once: red under load, green alone", result)
    assert code == 1
    assert "Walk output written to " + str(tmp_path / "out" / "walks-run.txt") in out
    alone = tmp_path / "out" / "alone-test_always-test-always.txt"
    text = alone.read_text()
    assert "1 failed" in text and "passed" not in text
    assert "passed" not in text


def test_runner_runs_the_first_run_and_each_rerun_in_the_directory_it_is_given(tmp_path):
    """test_runner_runs_the_first_run_and_each_rerun_in_the_directory_it_is_given"""
    (tmp_path / "test_where.py").write_text(
        "import os, pathlib\n"
        "def test_where():\n"
        "    with open('where.log', 'a') as f:\n"
        "        f.write(os.path.realpath(os.getcwd()) + '\\n')\n"
        "    assert False\n")
    run_walks.main([], targets=("test_where.py",), cwd=tmp_path, shots=tmp_path / "out")
    lines = (tmp_path / "where.log").read_text().split()
    assert lines == [str(tmp_path.resolve())] * 2


def run_in(tmp_path, capsys, args=(), targets=None):
    code = run_walks.main(list(args), targets=targets or (str(tmp_path),), cwd=tmp_path, shots=tmp_path / "out")
    return code, capsys.readouterr().out


def test_gate_reads_the_runner_verdicts_with_walk_results(tmp_path, capsys):
    """test_gate_reads_the_runner_verdicts_with_walk_results"""
    (tmp_path / "test_always.py").write_text("def test_always():\n    assert False\n")
    (tmp_path / "test_once.py").write_text(
        "import pathlib\n"
        "def test_once():\n"
        "    m = pathlib.Path(__file__).with_name('seen')\n"
        "    first = not m.exists()\n"
        "    m.write_text('x')\n"
        "    assert not first\n")
    _, out = run_in(tmp_path, capsys)
    got = checks.walk_results(out)
    verdicts = {(f.rsplit("/", 1)[-1], t): v for f, t, v, _ in got}
    assert verdicts == {("test_always.py", "test_always"): "red alone",
                        ("test_once.py", "test_once"): "red under load, green alone"}
    assert all(pathlib.Path(path).is_file() for *_, path in got)


def test_runner_re_runs_at_most_ten_red_walks_alone_and_lists_the_rest_as_red(tmp_path, capsys):
    """test_runner_re_runs_at_most_ten_red_walks_alone_and_lists_the_rest_as_red"""
    for n in range(12):
        (tmp_path / f"test_m{n:02}.py").write_text(f"def test_m{n:02}():\n    assert False\n")
    code, out = run_in(tmp_path, capsys)
    got = checks.walk_results(out)
    assert len(got) == 12 and {v for _, _, v, _ in got} == {"red alone"}
    assert len(list((tmp_path / "out").glob("alone-*.txt"))) == 10
    assert sum("not re-run" in path for *_, path in got) == 2
    assert code == 1


def test_runner_keeps_the_alone_output_of_same_named_walks_in_different_files_apart(tmp_path, capsys):
    """test_runner_keeps_the_alone_output_of_same_named_walks_in_different_files_apart"""
    for name in ("a", "b"):
        (tmp_path / f"test_{name}.py").write_text("def test_x():\n    assert False\n")
    _, out = run_in(tmp_path, capsys)
    paths = [path for *_, path in checks.walk_results(out)]
    assert len(paths) == 2 and len(set(paths)) == 2


def test_runner_takes_targets_from_its_command_line_and_gives_options_to_each_re_run(tmp_path, capsys, monkeypatch):
    """test_runner_takes_targets_from_its_command_line_and_gives_options_to_each_re_run"""
    (tmp_path / "test_wanted.py").write_text("def test_wanted():\n    assert False\n")
    (tmp_path / "test_other.py").write_text("def test_other():\n    assert False\n")
    monkeypatch.chdir(tmp_path)
    _, out = run_in(tmp_path, capsys, args=["test_wanted.py", "--tb=short"], targets=())
    names = [t for _, t, _, _ in checks.walk_results(out)]
    assert names == ["test_wanted"]
    alone = (tmp_path / "out" / "alone-test_wanted-test-wanted.txt").read_text()
    assert "1 failed" in alone and "test_wanted.py:" in alone  # the option reached the re-run (short traceback)
