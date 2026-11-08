"""The walk runner's reading of a pytest run. No browser. Lacks: the re-run itself."""

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
