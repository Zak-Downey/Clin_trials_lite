"""review-server-and-checks-01: a quick run's flaky browser test is not also blamed on the full run straight after it.

Run from the repo root: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-1/findings/scripts/review-server-and-checks-01.py -q
Red today: the full run that starts within a minute of the quick run's end is matched to the quick run's line too.
"""

import handover

CHECKS = [{"name": name, "result": "green", "minutes": 0.5, "output": f".checks/{name}.txt"} for name in handover.CHECK_NAMES]
WOBBLY = "walks/test_x.py::test_a_page_loads[1440x900]"


def test_a_flaky_walk_of_the_quick_run_is_not_put_on_the_full_run_after_it():
    # After the last ticket: a quick run ends at 10:00:00, then the full run starts 20 seconds later on the same commit.
    quick = {"at": "2026-11-16T10:00:00Z", "branch": "feature/x", "tip": "abc1234", "dirty": False, "result": "green",
             "minutes": 2.6, "quick": True, "checks": CHECKS}
    full = {"at": "2026-11-16T10:04:02Z", "branch": "feature/x", "tip": "abc1234", "dirty": False, "result": "green",
            "minutes": 3.7, "quick": False, "checks": CHECKS}
    lines = [{"at": "2026-11-16T09:59:58Z", "tip": "abc1234", "flaky": [WOBBLY]},  # written by the quick run's walks
             {"at": "2026-11-16T10:04:00Z", "tip": "abc1234", "flaky": []}]  # written by the full run's walks
    facts = handover.flaky_facts(handover.run_facts([quick, full], "feature/x"), lines)
    assert facts["walks"] == {WOBBLY: ["2026-11-16T10:00:00Z"]}


def test_a_full_run_with_no_line_of_its_own_is_still_called_missing():
    quick = {"at": "2026-11-16T10:00:00Z", "branch": "feature/x", "tip": "abc1234", "dirty": False, "result": "green",
             "minutes": 2.6, "quick": True, "checks": CHECKS}
    full = {"at": "2026-11-16T10:04:02Z", "branch": "feature/x", "tip": "abc1234", "dirty": False, "result": "green",
            "minutes": 3.7, "quick": False, "checks": CHECKS}
    lines = [{"at": "2026-11-16T09:59:58Z", "tip": "abc1234", "flaky": []}]  # only the quick run's line
    assert handover.flaky_facts(handover.run_facts([quick, full], "feature/x"), lines)["missing"] is True
