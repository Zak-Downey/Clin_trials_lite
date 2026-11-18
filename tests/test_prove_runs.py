"""The proof itself: `python3 prove.py` makes each break in a copy and says whether its test or check noticed.

Every case is a small hand-made git repo in a temporary folder (a module, its tests, a list of
breaks), whose `.venv` is a link to this repo's, as a real one would be. The proof runs real pytest
and the real checks.py in its copy; nothing is stubbed but the time limit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import prove

ROOT = Path(__file__).resolve().parent.parent

APP = "def total(a, b):\n    return a + b\n\n\ndef label(n):\n    return 'many' if n > 1 else 'one'\n"
TESTS = "import app\n\n\ndef test_total_adds():\n    assert app.total(2, 3) == 5\n"


def small_repo(tmp_path, breaks, tests=TESTS):
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    (root / "app.py").write_text(APP)
    (root / "tests" / "test_app.py").write_text(tests)
    (root / ".gitignore").write_text(".venv\n.checks/\n__pycache__/\n")
    (root / prove.BREAKS).parent.mkdir(parents=True)
    (root / prove.BREAKS).write_text(json.dumps(breaks))
    shutil.copy(ROOT / "checks.py", root / "checks.py")
    (root / ".venv").symlink_to(ROOT / ".venv")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "start"],
                   cwd=root, check=True)
    return root


def entry(**changes):
    base = {"id": "adds-wrong", "file": "app.py", "find": "a + b", "replace": "a - b",
            "why": "a sum that subtracts is a plausible slip.", "test": "tests/test_app.py::test_total_adds"}
    base.update(changes)
    return {key: value for key, value in base.items() if value is not None}


def snapshot(root):
    """Every file and folder under root (links not followed) and its bytes, but the proof's own log and its folder."""
    files = {}
    for folder, dirs, names in os.walk(root):
        for name in names:
            path = Path(folder) / name
            if path.relative_to(root) != Path(".checks/proof.jsonl"):
                files[str(path.relative_to(root))] = path.read_bytes() if not path.is_symlink() else os.readlink(path)
        files.update({str((Path(folder) / d).relative_to(root)): "dir" for d in dirs if d != ".checks"})
    return files


def prove_in(root, **options):
    printed = []
    before = snapshot(root)
    code = prove.prove(root, out=printed.append, **options)
    assert snapshot(root) == before, "the proof changed the folder it was run in"
    log = (root / ".checks" / "proof.jsonl").read_text().splitlines()
    return code, printed, json.loads(log[-1])


def test_a_break_its_test_catches_is_reported_caught_and_the_proof_ends_zero(tmp_path):
    code, printed, line = prove_in(small_repo(tmp_path, [entry()]))
    assert code == 0
    assert printed[0].split() == ["adds-wrong", "tests/test_app.py::test_total_adds", "caught"]
    assert printed[-1] == "proof: 1 of 1 breaks caught"
    assert line["result"] == "green"
    assert line["breaks"] == [{"id": "adds-wrong", "outcome": "caught"}]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=tmp_path / "repo", capture_output=True, text=True)
    assert line["commit"] == commit.stdout.strip() != ""
    assert line["at"].endswith("Z") and line["dirty"] is False


def test_a_break_its_test_misses_is_reported_as_stayed_green_and_the_proof_ends_one(tmp_path):
    misses = entry(id="label-wrong", find="n > 1", replace="n > 2")
    code, printed, line = prove_in(small_repo(tmp_path, [entry(), misses]))
    assert code == 1
    assert printed[0].split()[-1] == "caught"
    assert printed[1].split() == ["label-wrong", "tests/test_app.py::test_total_adds", "stayed", "green"]
    assert printed[-1] == "proof: 1 of 2 breaks caught"
    assert line["result"] == "red"
    assert [b["outcome"] for b in line["breaks"]] == ["caught", "stayed green"]


def test_a_test_that_is_red_before_the_break_is_reported_so_and_the_proof_ends_one(tmp_path):
    already_red = TESTS + "\n\ndef test_total_of_nothing():\n    assert app.total(0, 0) == 1\n"
    item = entry(test="tests/test_app.py::test_total_of_nothing")
    code, printed, line = prove_in(small_repo(tmp_path, [item], tests=already_red))
    assert code == 1
    assert printed[0].split()[:6] == ["adds-wrong", "tests/test_app.py::test_total_of_nothing", "red", "before", "the", "change"]
    assert "assert 0 == 1" in "\n".join(printed)  # the end of its output says why
    assert line["breaks"] == [{"id": "adds-wrong", "outcome": "red before the change"}]


def test_a_break_that_stops_the_tests_being_collected_is_not_proof(tmp_path):
    item = entry(id="syntax", find="return a + b", replace="return a +")
    code, printed, line = prove_in(small_repo(tmp_path, [item]))
    assert code == 1
    assert printed[0].split()[2:5] == ["could", "not", "run"]
    assert "pytest ended 4" in printed[0]  # pytest's code when the test it was named could not be collected
    assert line["breaks"] == [{"id": "syntax", "outcome": "could not run"}]


def test_a_run_that_passes_its_time_limit_is_stopped_with_all_it_started_and_the_proof_ends_one(tmp_path):
    pid_file = tmp_path / "child.pid"
    child = f"import os, time; open({str(pid_file)!r}, 'w').write(str(os.getpid())); time.sleep(30)"
    slow = TESTS + ("\n\ndef test_slow():\n    import subprocess, sys, time\n"
                    f"    subprocess.Popen([sys.executable, '-c', {child!r}])\n    time.sleep(30)\n")
    started = time.monotonic()
    code, printed, line = prove_in(small_repo(tmp_path, [entry(test="tests/test_app.py::test_slow")], tests=slow),
                                   minutes=0.02)
    assert time.monotonic() - started < 10
    assert code == 1
    assert printed[0].split()[2:5] == ["could", "not", "run"]
    assert "stopped after 0.02 minutes" in printed[0]
    assert line["breaks"] == [{"id": "adds-wrong", "outcome": "could not run"}]
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        raise AssertionError("a process the proof started outlived it")


def test_an_empty_list_proves_nothing_and_the_proof_ends_one(tmp_path):
    code, printed, line = prove_in(small_repo(tmp_path, []))
    assert code == 1
    assert printed == ["proof: the list of breaks is empty, so nothing is proved"]
    assert line["result"] == "red" and line["breaks"] == []


def test_a_list_with_a_fault_stops_the_proof_before_anything_runs(tmp_path):
    root = small_repo(tmp_path, [entry(), entry(id="gone", find="a * b")])
    code, printed, line = prove_in(root)
    assert code == 1
    assert printed == ["gone: the find text is not in app.py",
                       "proof: the list of breaks has 1 fault; nothing was run"]
    assert line["result"] == "red" and line["breaks"] == []


def test_a_break_proved_by_a_check_is_caught_when_that_check_goes_red_in_the_copy(tmp_path):
    by_check = entry(id="adds-wrong-unit", test=None, check="unit")
    missed = entry(id="label-wrong-unit", test=None, check="unit", find="n > 1", replace="n > 2")
    code, printed, line = prove_in(small_repo(tmp_path, [by_check, missed]))
    assert printed[0].split() == ["adds-wrong-unit", "unit", "caught"]
    assert printed[1].split()[:4] == ["label-wrong-unit", "unit", "stayed", "green"]
    assert code == 1
    assert [b["outcome"] for b in line["breaks"]] == ["caught", "stayed green"]
