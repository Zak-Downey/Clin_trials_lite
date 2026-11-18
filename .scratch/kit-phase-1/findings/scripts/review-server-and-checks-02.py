"""review-server-and-checks-02: a pull request that renames a judging file away is told so.

Run from the repo root: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-1/findings/scripts/review-server-and-checks-02.py -q
Red today: git's rename detection reports only the new name, so a renamed pytest.ini or checks.py gets no notice.
"""

import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[4] / ".github" / "workflows" / "judge_notice.py"
JUDGING = [".github/workflows/", ".claude/settings.json", "pytest.ini", "checks.py"]


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_renaming_pytest_ini_and_checks_py_away_is_named_in_the_notice(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "pytest.ini").write_text("[pytest]\ntestpaths = tests\naddopts = -p no:cacheprovider\n")
    (repo / "checks.py").write_text("import sys\n" + "print('a check')\n" * 20)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "pytest.ini", "pytest.ini.off")
    git(repo, "mv", "checks.py", "checks_old.py")
    git(repo, "commit", "-q", "-m", "move the judges aside")
    summary = tmp_path / "summary.md"
    summary.write_text("")
    subprocess.run([sys.executable, str(SCRIPT), base, *JUDGING], cwd=repo, capture_output=True, text=True,
                   env={"GITHUB_STEP_SUMMARY": str(summary), "PATH": "/usr/bin:/bin"})
    text = summary.read_text()
    assert "`pytest.ini`" in text and "`checks.py`" in text, text or "(no notice at all)"


def test_renaming_a_test_file_so_its_tests_are_no_longer_collected_counts_them_removed(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "tests" / "test_app.py").write_text("def test_one():\n    assert True\n\n\ndef test_two():\n    assert True\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "tests/test_app.py", "tests/app_checks_off.py")
    git(repo, "commit", "-q", "-m", "park the tests")
    summary = tmp_path / "summary.md"
    summary.write_text("")
    subprocess.run([sys.executable, str(SCRIPT), base, *JUDGING], cwd=repo, capture_output=True, text=True,
                   env={"GITHUB_STEP_SUMMARY": str(summary), "PATH": "/usr/bin:/bin"})
    assert "Tests removed: 2" in summary.read_text(), summary.read_text() or "(no notice at all)"
