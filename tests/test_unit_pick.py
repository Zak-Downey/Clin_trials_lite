"""A picked unit run, end to end: the real checks.py, picker.py and walk_map.py, and real pytest with its record of
which test ran which code (pytest-testmon), in a small git repo in a temporary folder whose `.venv` is a link to this
repo's. The repo has a module its tests import, a program one test runs as a separate program, a map that names both
lists the unit picker reads, the record a whole run leaves and that run's green line in the run log.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = {
    "app.py": "def total(a, b):\n    return a + b\n",
    "tool.py": "import sys\n\nif __name__ == '__main__':\n    print(int(sys.argv[1]) * 2)\n",
    "tests/test_app.py": "import app\n\n\ndef test_total_adds():\n    assert app.total(2, 3) == 5\n\n\n"
                         "def test_total_of_nothing():\n    assert app.total(0, 0) == 0\n",
    "tests/test_tool.py": "import subprocess, sys\n\n\ndef test_tool_doubles():\n"
                          "    done = subprocess.run([sys.executable, 'tool.py', '4'], capture_output=True, text=True)\n"
                          "    assert done.stdout.strip() == '8'\n",
    "pytest.ini": "[pytest]\ntestpaths = tests\n",
    ".gitignore": ".venv\n.checks/\n__pycache__/\n.testmondata*\n",
}
MAP = {"shared": [], "always": [], "areas": [], "none": ["*"],
       "run_apart": ["tool.py"], "unit_always": ["tests/test_app.py"]}


def git(root, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=root, check=True,
                   capture_output=True)


def picking_repo(tmp_path, the_map=MAP) -> Path:
    root = tmp_path / "repo"
    mapped = {"docs/agents/local/walk-map.json": json.dumps(the_map)} if the_map is not None else {}
    for name, text in {**FILES, **mapped}.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    for name in ("checks.py", "picker.py", "walk_map.py"):
        shutil.copy(ROOT / name, root / name)
    (root / ".venv").symlink_to(ROOT / ".venv")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    subprocess.run([str(root / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "--testmon-noselect"], cwd=root,
                   check=True, capture_output=True, env=quiet_env())
    tip = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    (root / ".checks").mkdir()
    (root / ".checks" / "runs.jsonl").write_text(json.dumps(
        {"tip": tip, "dirty": False, "result": "green", "every": True, "picked": False}) + "\n")
    return root


def quiet_env():
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def picked_unit(root):
    """(exit code, the printed line of the unit pick, the unit pick in the run log)."""
    done = subprocess.run([sys.executable, "checks.py", "--pick", "unit"], cwd=root, capture_output=True, text=True,
                          env=quiet_env())
    said = next(line for line in done.stdout.splitlines() if line.startswith("unit") and "picked" in line)
    line = json.loads((root / ".checks" / "runs.jsonl").read_text().splitlines()[-1])
    return done.returncode, said, next(p for p in line["picks"] if p["check"] == "unit")


def test_a_break_in_python_a_test_runs_only_as_a_separate_program_turns_the_picked_unit_run_red(tmp_path):
    root = picking_repo(tmp_path)
    (root / "tool.py").write_text(FILES["tool.py"].replace("* 2", "* 3"))
    code, said, pick = picked_unit(root)
    assert code == 1, said
    assert pick["ran"] == pick["of"] == 3 and "`tool.py`" in pick["why"], pick
    assert said == f"unit      picked 3 of 3 unit tests: {pick['why']}"


def test_without_a_map_a_picked_unit_run_cannot_tell_which_python_runs_apart_and_runs_every_test(tmp_path):
    root = picking_repo(tmp_path, the_map=None)
    (root / "app.py").write_text(FILES["app.py"].replace("a + b", "b + a"))
    code, said, pick = picked_unit(root)
    assert code == 0 and pick["ran"] == pick["of"] == 3 and "no map" in pick["why"], said


def test_a_picked_unit_run_whose_record_selects_no_test_runs_the_tests_that_always_run_and_says_so(tmp_path):
    root = picking_repo(tmp_path)
    code, said, pick = picked_unit(root)
    assert code == 0, said
    assert pick["ran"] == 2 and pick["of"] == 3, pick
    assert "none was selected, so the tests that always run, `tests/test_app.py`" in pick["why"], pick
    assert said == f"unit      picked 2 of 3 unit tests: {pick['why']}"


def test_a_picked_unit_run_whose_record_selects_no_test_and_whose_map_names_none_that_always_run_runs_every_test(tmp_path):
    root = picking_repo(tmp_path, the_map={**MAP, "unit_always": []})
    code, said, pick = picked_unit(root)
    assert code == 0 and pick["ran"] == pick["of"] == 3, said
    assert "none was selected, and the map names no test that always runs, so every test" in pick["why"], pick
