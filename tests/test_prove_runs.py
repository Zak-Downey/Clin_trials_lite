"""The proof itself: `python3 prove.py` makes each break in a copy and says whether its test or check noticed.

Every case is a small hand-made git repo in a temporary folder (a module, its tests, a list of
breaks), whose `.venv` is a link to this repo's, as a real one would be. The proof runs real pytest
and the real checks.py in its copy; nothing is stubbed but the time limit, and in two tests the refused
kill macOS answers for a group whose members have exited but are not yet reaped.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
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


def test_a_check_past_its_time_limit_does_not_outlive_the_proof(tmp_path):
    # checks.py starts each check in a session of its own, so stopping the proof's run must let
    # checks.py stop its check, or the check (here its pytest) keeps running after the proof ends.
    pid_file = tmp_path / "check.pid"
    slow = TESTS + ("\n\ndef test_slow():\n    import os, time\n"
                    f"    open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n    time.sleep(60)\n")
    code, printed, line = prove_in(small_repo(tmp_path, [entry(test=None, check="unit")], tests=slow), minutes=0.05)
    assert code == 1
    assert line["breaks"] == [{"id": "adds-wrong", "outcome": "could not run"}]
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        raise AssertionError("the check's pytest outlived the proof that started it")


def test_ctrl_c_during_a_check_leaves_nothing_running(tmp_path):
    pid_file = tmp_path / "check.pid"
    slow = TESTS + ("\n\ndef test_slow():\n    import os, time\n"
                    f"    open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n    time.sleep(60)\n")
    root = small_repo(tmp_path, [entry(test=None, check="unit")], tests=slow)
    shutil.copy(ROOT / "prove.py", root / "prove.py")
    proof = subprocess.Popen([sys.executable, "prove.py"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 30
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        pid = int(pid_file.read_text())
        proof.send_signal(signal.SIGINT)
        proof.wait(timeout=20)
    finally:
        if proof.poll() is None:
            proof.kill()
            proof.wait()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        raise AssertionError("the check's pytest outlived the proof stopped by Ctrl+C")


def killpg_refusing_the_kill(real=os.killpg):
    """os.killpg as macOS answers it when every member of the group has exited but some are not yet
    reaped: the stop is delivered, the kill after it is refused with EPERM."""
    def killpg(pgid, sig):
        if sig == signal.SIGKILL:
            raise PermissionError(1, "Operation not permitted")
        real(pgid, sig)
    return killpg


def test_a_run_whose_group_has_only_unreaped_members_left_at_the_kill_is_still_stopped_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(prove.os, "killpg", killpg_refusing_the_kill())
    code = prove.run_in([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, 0.005, tmp_path / "out.txt")
    assert code is None


def test_a_refused_kill_of_a_group_with_a_live_member_is_not_hidden(tmp_path, monkeypatch):
    monkeypatch.setattr(prove, "GRACE_SECONDS", 0.2)
    monkeypatch.setattr(prove.os, "killpg", killpg_refusing_the_kill())
    stubborn = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
    pid_file = tmp_path / "pid"
    command = [sys.executable, "-c", f"import os; open({str(pid_file)!r}, 'w').write(str(os.getpid())); {stubborn}"]
    try:
        try:
            prove.run_in(command, tmp_path, 0.01, tmp_path / "out.txt")
        except PermissionError:
            pass
        else:
            raise AssertionError("a refused kill of a live process was taken for a stopped run")
    finally:
        os.kill(int(pid_file.read_text()), signal.SIGKILL)


# `python3 prove.py --pick`: each break proved by a test is made in a copy that carries the picker's base and record,
# and the copy's `checks.py --quick --pick <check>` must go red.

PICK_TESTS = TESTS + "\n\ndef test_label_says_many():\n    assert app.label(3) == 'many'\n"
WALK = ("import pathlib\n\n\ndef test_{name}_page_reads_ok():\n"
        "    for page in ('pages/{name}.js', 'pages/shared.js'):\n"
        "        assert 'ok' in pathlib.Path(page).read_text()\n")
RUN_WALKS = "import subprocess, sys\nsys.exit(subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *(sys.argv[1:] or ['walks'])]).returncode)\n"
MAP = {"shared": ["pages/shared.js"], "always": [],
       "areas": [{"name": "Page A", "files": ["pages/a.js"], "walks": ["walks/test_a_walk.py"]},
                 {"name": "Page B", "files": ["pages/b.js"], "walks": ["walks/test_b_walk.py"]}],
       "none": ["*.py", "tests/*", "docs/*", ".gitignore", "pytest.ini"]}


def pick_repo(tmp_path, breaks, the_map=MAP, run_walks=RUN_WALKS):
    """A small repo with a unit suite, two walk files on a map of two pages, and what the picker reads: a green run of
    every check at its last commit in the run log, and the unit record that run would have left."""
    root = small_repo(tmp_path, breaks, tests=PICK_TESTS)
    for name in ("picker.py", "walk_map.py"):
        shutil.copy(ROOT / name, root / name)
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    (root / ".gitignore").write_text(".venv\n.checks/\n__pycache__/\n.testmondata*\n")
    (root / "pages").mkdir()
    for name in ("a", "b", "shared"):
        (root / "pages" / f"{name}.js").write_text(f"// {name}: ok\n")
    (root / "walks").mkdir()
    (root / "walks" / "run_walks.py").write_text(run_walks)
    for name in ("a", "b"):
        (root / "walks" / f"test_{name}_walk.py").write_text(WALK.format(name=name))
    (root / "docs" / "agents" / "local" / "walk-map.json").write_text(json.dumps(the_map))
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "pages"],
                   cwd=root, check=True)
    subprocess.run([str(root / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
                    "--testmon-noselect"], cwd=root, check=True, capture_output=True)
    tip = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    (root / ".checks").mkdir()
    (root / ".checks" / "runs.jsonl").write_text(json.dumps(
        {"tip": tip, "dirty": False, "result": "green", "every": True, "picked": False}) + "\n")
    return root


def walk_entry(page="a", walk="a"):
    """A break of a page, proved by the walk file that reads it."""
    return entry(id=f"{page}-broken", file=f"pages/{page}.js", find="ok", replace="bad",
                 test=f"walks/test_{walk}_walk.py::test_{walk}_page_reads_ok")


def test_a_picked_proof_reports_a_break_its_pick_includes_as_caught_with_how_many_the_pick_ran(tmp_path):
    lint = entry(id="by-lint", test=None, check="lint")
    code, printed, line = prove_in(pick_repo(tmp_path, [entry(), walk_entry(), lint]), pick=True)
    assert printed[0].startswith("adds-wrong  unit  caught  picked 1 of 2 unit tests: "), printed
    assert printed[1].startswith("a-broken  walks  caught  picked 1 of 2 walk files: Page A, "), printed
    assert printed[2] == "by-lint  lint  left to python3 prove.py: it is proved by a check, which runs whole"
    assert printed[-1] == "proof --pick: 2 of 2 breaks caught, 2 by a pick smaller than the whole; 1 proved by a check left to python3 prove.py"
    assert code == 0
    assert line["picked"] is True and line["result"] == "green"
    assert line["breaks"] == [{"id": "adds-wrong", "outcome": "caught", "ran": 1, "of": 2},
                              {"id": "a-broken", "outcome": "caught", "ran": 1, "of": 2}]


def test_a_break_the_pick_leaves_out_is_reported_hidden_and_the_picked_proof_ends_one(tmp_path):
    wrong_map = {**MAP, "areas": [{"name": "Page A", "files": ["pages/b.js"], "walks": ["walks/test_a_walk.py"]},
                                  {"name": "Page B", "files": ["pages/a.js"], "walks": ["walks/test_b_walk.py"]}]}
    code, printed, line = prove_in(pick_repo(tmp_path, [walk_entry()], the_map=wrong_map), pick=True)
    assert printed[0].startswith("a-broken  walks  hidden  picked 1 of 2 walk files: Page B, "), printed
    assert printed[-1] == "proof --pick: 0 of 1 breaks caught, 0 by a pick smaller than the whole; 0 proved by a check left to python3 prove.py"
    assert code == 1
    assert line["result"] == "red" and line["breaks"] == [{"id": "a-broken", "outcome": "hidden", "ran": 1, "of": 2}]


def test_a_break_whose_pick_ran_everything_is_caught_but_not_counted_as_proof_of_picking(tmp_path):
    code, printed, line = prove_in(pick_repo(tmp_path, [walk_entry(page="shared")]),
                                   pick=True)
    assert printed[0].startswith("shared-broken  walks  caught, but nothing was picked  picked 2 of 2 walk files: every walk"), printed
    assert printed[-1] == "proof --pick: 1 of 1 breaks caught, 0 by a pick smaller than the whole; 0 proved by a check left to python3 prove.py"
    assert code == 0
    assert line["breaks"] == [{"id": "shared-broken", "outcome": "caught, but nothing was picked", "ran": 2, "of": 2}]


def test_a_pick_of_everything_stopped_at_the_limit_is_reported_so_and_does_not_fail_the_picked_proof(tmp_path):
    # nothing was picked, so picking hid nothing; whether the test catches the break is the plain proof's to say
    slow_whole = "import sys, time\nif not sys.argv[1:]:\n    time.sleep(30)\n" + RUN_WALKS
    root = pick_repo(tmp_path, [walk_entry(page="shared"), walk_entry()], run_walks=slow_whole)
    code, printed, line = prove_in(root, pick=True, minutes=0.1)
    assert printed[0].startswith("shared-broken  walks  could not run, but nothing was picked (stopped after 0.1 minutes)"
                                 "  picked 2 of 2 walk files: every walk"), printed
    assert printed[-1] == ("proof --pick: 1 of 2 breaks caught, 1 by a pick smaller than the whole; 1 stopped at the limit, "
                           "but its pick ran everything; 0 proved by a check left to python3 prove.py")
    assert code == 0
    assert line["breaks"][0] == {"id": "shared-broken", "outcome": "could not run, but nothing was picked", "ran": 2, "of": 2}
