"""The list of deliberate breaks: what the reading function in prove.py says is wrong with a list.

Each case is a hand-made list over a small repo in a temporary folder. The last test reads this
repo's own list, so an entry whose text has left its file turns the ordinary checks red. Nothing
here makes a break or runs a test.
"""

from __future__ import annotations

import json
from pathlib import Path

import prove

ROOT = Path(__file__).resolve().parent.parent
CHECK_NAMES = ["lint", "unit"]


def small_repo(tmp_path):
    (tmp_path / "app.py").write_text("def total(a, b):\n    return a + b\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text(
        "import app\n\n\ndef test_total_adds():\n    assert app.total(2, 3) == 5\n\n\n"
        "class TestMore:\n    def test_zero(self):\n        assert app.total(0, 0) == 0\n")
    return tmp_path


def entry(**changes):
    base = {"id": "adds-wrong", "file": "app.py", "find": "a + b", "replace": "a - b",
            "why": "a sum that subtracts is a plausible slip.", "test": "tests/test_app.py::test_total_adds"}
    base.update(changes)
    return {key: value for key, value in base.items() if value is not None}


def problems(tmp_path, breaks):
    return prove.list_problems(breaks, small_repo(tmp_path), check_names=CHECK_NAMES)


def test_a_well_formed_list_has_no_problems(tmp_path):
    breaks = [entry(), entry(id="by-lint", check="lint", test=None),
              entry(id="in-a-class", test="tests/test_app.py::TestMore::test_zero[case]")]
    assert problems(tmp_path, breaks) == []


def test_an_entry_missing_a_field_is_named_with_the_field(tmp_path):
    found = problems(tmp_path, [entry(why=None)])
    assert found == ["adds-wrong: has no why"]


def test_an_entry_with_no_id_is_named_by_its_place_in_the_list(tmp_path):
    found = problems(tmp_path, [entry(), entry(id=None)])
    assert found == ["entry 2: has no id"]


def test_a_replace_that_deletes_the_text_is_well_formed(tmp_path):
    assert problems(tmp_path, [entry(replace="")]) == []


def test_an_entry_naming_both_a_test_and_a_check_or_neither_is_reported(tmp_path):
    found = problems(tmp_path, [entry(check="lint"), entry(id="unproved", test=None)])
    assert found == ["adds-wrong: names both a test and a check; it takes one",
                     "unproved: names neither a test nor a check"]


def test_a_repeated_id_is_reported(tmp_path):
    found = problems(tmp_path, [entry(), entry(find="return")])
    assert found == ["adds-wrong: the id is used more than once"]


def test_a_file_that_does_not_exist_is_reported(tmp_path):
    found = problems(tmp_path, [entry(file="gone.py")])
    assert found == ["adds-wrong: gone.py does not exist"]


def test_find_text_that_is_absent_or_occurs_twice_is_reported(tmp_path):
    found = problems(tmp_path, [entry(find="a * b"), entry(id="twice", find="a")])
    assert found == ["adds-wrong: the find text is not in app.py",
                     "twice: the find text occurs 3 times in app.py; it must occur once"]


def test_find_and_replace_the_same_is_reported(tmp_path):
    found = problems(tmp_path, [entry(replace="a + b")])
    assert found == ["adds-wrong: find and replace are the same, so nothing breaks"]


def test_a_test_whose_file_or_function_does_not_exist_is_reported(tmp_path):
    found = problems(tmp_path, [entry(test="tests/test_gone.py::test_total_adds"),
                                entry(id="no-function", test="tests/test_app.py::test_total_subtracts"),
                                entry(id="no-class", test="tests/test_app.py::TestLess::test_zero"),
                                entry(id="no-name", test="tests/test_app.py")])
    assert found == ["adds-wrong: the test file tests/test_gone.py does not exist",
                     "no-function: tests/test_app.py has no test test_total_subtracts",
                     "no-class: tests/test_app.py has no test TestLess::test_zero",
                     "no-name: the test is not one test, written <file>::<test>"]


def test_a_check_that_is_not_one_of_the_checks_is_reported(tmp_path):
    found = problems(tmp_path, [entry(test=None, check="typing")])
    assert found == ["adds-wrong: typing is not one of the checks (lint, unit)"]


def test_without_names_given_the_checks_are_the_ones_checks_py_runs(tmp_path):
    breaks = [entry(test=None, check="walks"), entry(id="made-up", test=None, check="typing")]
    assert prove.list_problems(breaks, small_repo(tmp_path)) == [
        "made-up: typing is not one of the checks (lint, patterns, escapes, unit, walks)"]


def test_this_repos_list_of_breaks_is_current():
    breaks = json.loads((ROOT / prove.BREAKS).read_text(encoding="utf-8"))
    assert breaks, "the list of breaks is empty"
    assert prove.list_problems(breaks, ROOT) == []


def test_every_check_in_checks_py_has_a_break_in_this_repos_list():
    breaks = json.loads((ROOT / prove.BREAKS).read_text(encoding="utf-8"))
    proved = {item["check"] for item in breaks if "check" in item}
    proved |= {"unit" for item in breaks if item.get("test", "").startswith("tests/")}
    proved |= {"walks" for item in breaks if item.get("test", "").startswith("walks/")}
    missing = [name for name, *_ in prove.checks.CHECKS if name not in proved]
    assert missing == [], f"no break proves these checks can fail: {', '.join(missing)}"
