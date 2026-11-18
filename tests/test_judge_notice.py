"""The notice a pull request gets when it changes what judges it, run against a real temporary git repo.

The notice is what lands in the run's summary on GitHub: the judging files the pull request changes and how many
tests it removes. It never fails the run and says nothing when there is nothing to say.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "judge_notice.py"
JUDGING = [".github/workflows/", ".claude/settings.json", "pytest.ini", "checks.py"]


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def write(repo, files):
    for name, content in files.items():
        path = repo / name
        if content is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def commit(repo, files, message):
    write(repo, files)
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


BASE_FILES = {
    "checks.py": "print('checks')\n",
    "pytest.ini": "[pytest]\n",
    ".github/workflows/checks.yml": "name: checks\n",
    ".claude/settings.json": "{}\n",
    "app.py": "x = 1\n",
    "tests/test_app.py": "def test_one():\n    pass\n\n\ndef test_two():\n    pass\n",
    "tests/test_other.py": "def test_three():\n    pass\n",
}


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    return root


def notice(repo, base, tmp_path):
    """Run the notice as the workflow step does; return (exit code, what it wrote to the run's summary)."""
    summary = tmp_path / "summary.md"
    summary.write_text("")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), base, *JUDGING],
        cwd=repo, capture_output=True, text=True, env={"GITHUB_STEP_SUMMARY": str(summary), "PATH": "/usr/bin:/bin"},
    )
    return result.returncode, summary.read_text()


def test_a_pull_request_that_changes_checks_py_and_the_workflow_is_told_so_by_name(repo, tmp_path):
    base = commit(repo, BASE_FILES, "base")
    commit(repo, {"checks.py": "print('lenient')\n", ".github/workflows/checks.yml": "name: other\n"}, "change")
    code, summary = notice(repo, base, tmp_path)
    assert code == 0
    assert "`checks.py`" in summary
    assert "`.github/workflows/checks.yml`" in summary
    assert "Tests removed: 0" in summary


def test_tests_taken_out_are_counted_net_of_tests_put_in_and_a_deleted_test_file_counts_all_of_its_tests(
    repo, tmp_path
):
    base = commit(repo, BASE_FILES, "base")
    commit(repo, {
        "tests/test_app.py": "def test_one():\n    pass\n",  # test_two out
        "tests/test_other.py": None,  # test_three out with its file
        "walks/test_added.py": "async def test_four():\n    pass\n",  # test_four in
        "app.py": "x = 2\n\n\ndef test_like():\n    pass\n",  # not a test file: counts as nothing
    }, "drop tests")
    code, summary = notice(repo, base, tmp_path)
    assert code == 0
    assert "Tests removed: 1" in summary  # two out (test_two, test_three), one in (test_four)
    assert "Files that judge" not in summary


def test_a_pull_request_that_changes_nothing_judging_and_removes_no_test_gets_no_notice(repo, tmp_path):
    base = commit(repo, BASE_FILES, "base")
    commit(repo, {"app.py": "x = 2\n", "tests/test_app.py": BASE_FILES["tests/test_app.py"] + "\n\ndef test_more():\n    pass\n",
                  ".github/README.md": "not a workflow\n", "checks.py.bak": "x\n"}, "ordinary change")
    code, summary = notice(repo, base, tmp_path)
    assert (code, summary) == (0, "")


def test_a_run_started_by_hand_has_no_base_and_gets_no_notice(repo, tmp_path):
    commit(repo, BASE_FILES, "base")
    commit(repo, {"checks.py": "print('lenient')\n"}, "change")
    code, summary = notice(repo, "", tmp_path)
    assert (code, summary) == (0, "")


def test_a_notice_that_cannot_be_worked_out_still_does_not_fail_the_run(repo, tmp_path):
    commit(repo, BASE_FILES, "base")
    code, summary = notice(repo, "no-such-commit", tmp_path)
    assert (code, summary) == (0, "")


def test_renaming_a_judging_file_away_is_named_and_renaming_a_test_file_out_of_collection_counts_its_tests_removed(
    repo, tmp_path
):
    # review-server-and-checks-02: git's rename detection reported only the new name, with no removed lines.
    base = commit(repo, BASE_FILES, "base")
    for old, new in [("pytest.ini", "pytest.ini.off"), ("checks.py", "checks_old.py"),
                     ("tests/test_app.py", "tests/app_checks_off.py")]:
        git(repo, "mv", old, new)
    commit(repo, {}, "move the judges and a test file aside")
    code, summary = notice(repo, base, tmp_path)
    assert code == 0
    assert "`pytest.ini`" in summary and "`checks.py`" in summary
    assert "Tests removed: 2" in summary  # test_one and test_two are no longer in a test_*.py file
