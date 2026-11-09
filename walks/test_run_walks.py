"""The walk runner's reading of a pytest run. No browser. Lacks: a real browser walk;
the re-run is shown on two tiny pytest files, not on the app."""

import re

from walks import run_walks


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
        "def test_bystander_fails_only_in_the_full_run():\n"
        "    assert True\n")
    code = run_walks.main([], targets=(str(tmp_path),), cwd=tmp_path, shots=tmp_path / "out")
    out = capsys.readouterr().out
    result = out.split("## Result")[1]
    assert re.search(r"test_always\.py::test_always -- red alone", result)
    assert re.search(r"test_once\.py::test_once -- red under load, green alone", result)
    assert code == 1
    alone = tmp_path / "out" / "alone-test-always.txt"
    text = alone.read_text()
    assert "1 failed" in text and "passed" not in text
    assert "test_bystander" not in text and "test_once" not in text
