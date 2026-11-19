"""review-server-and-checks: a picked unit run in a copy that carries the picker's base and record (as prove.py --pick
makes it). Run from the repo root, after a whole green run on a clean folder:
    .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-3/findings/scripts/test_review_unit_pick.py -q
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import prove  # noqa: E402


def picked_unit(copy):
    done = subprocess.run([sys.executable, "checks.py", "--pick", "unit"], cwd=copy, capture_output=True, text=True)
    line = json.loads((copy / ".checks" / "runs.jsonl").read_text().splitlines()[-1])
    return done.returncode, done.stdout, next(p for p in line["picks"] if p["check"] == "unit")


def test_a_break_in_python_a_test_runs_only_in_a_subprocess_turns_the_picked_unit_run_red(tmp_path):
    copy = prove.copy_for_pick(ROOT, tmp_path)
    script = copy / ".github" / "workflows" / "judge_notice.py"
    text = script.read_text()
    assert 'TEST_DEF = re.compile(r"^\\s*(async\\s+)?def\\s+test_")' in text
    script.write_text(text.replace('TEST_DEF = re.compile(r"^\\s*(async\\s+)?def\\s+test_")', 'TEST_DEF = re.compile(r"^NEVER")'))
    plain = subprocess.run([str(copy / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_judge_notice.py"], cwd=copy, capture_output=True, text=True)
    assert plain.returncode == 1, "the break is caught by tests/test_judge_notice.py when it is named"
    code, printed, pick = picked_unit(copy)
    assert code == 1, f"the picked unit run stayed green: {printed}"


def test_a_picked_unit_run_never_ends_green_having_run_no_test(tmp_path):
    copy = prove.copy_for_pick(ROOT, tmp_path)  # nothing changed since the base
    code, printed, pick = picked_unit(copy)
    assert isinstance(pick["ran"], int) and pick["ran"] > 0, f"ran {pick['ran']} of {pick['of']}, ended {code}: {printed}"
