"""The fidelity check's comparison, on small records. No network.

Lacks: the live registry (that is the by-hand run).
"""

from __future__ import annotations

import copy

from walks import fidelity_check

RECORD = {"a": {"b": 1, "c": ["x"]}, "d": "text", "e": None}


def test_fidelity_compare_of_equal_records_finds_nothing():
    """test_fidelity_compare_of_equal_records_finds_nothing"""
    assert fidelity_check.compare(RECORD, copy.deepcopy(RECORD)) == ([], [])


def test_fidelity_compare_reports_a_path_missing_live_and_one_only_live():
    """test_fidelity_compare_reports_a_path_missing_live_and_one_only_live"""
    live = copy.deepcopy(RECORD)
    del live["a"]["b"]
    live["new"] = 1
    problems, extras = fidelity_check.compare(RECORD, live)
    assert problems == ["missing live: .a.b"]
    assert extras == [".new"]


def test_fidelity_compare_reports_a_retyped_value_but_not_a_null_one():
    """test_fidelity_compare_reports_a_retyped_value_but_not_a_null_one"""
    live = copy.deepcopy(RECORD)
    live["d"] = 5
    live["e"] = "now text"
    problems, _ = fidelity_check.compare(RECORD, live)
    assert problems == ["type differs: .d fixture str, live int"]
