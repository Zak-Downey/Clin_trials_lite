"""The hook before a push: a real push from a repo in a temporary folder to a temporary remote, with a stand-in checks.py."""

from __future__ import annotations

import pathlib
import shutil
import subprocess

HOOK = pathlib.Path(__file__).resolve().parent.parent / ".githooks" / "pre-push"

STAND_IN = '''import pathlib, sys
assert sys.argv[1:] == ["lint", "patterns", "escapes"], sys.argv
for number, line in enumerate(pathlib.Path("app.py").read_text().splitlines(), 1):
    if "#" in line:
        print("patterns  red      0.0 min  .checks/patterns.txt")
        print(f"    app.py:{number}: a comment; say it in a name instead")
        sys.exit(1)
print("lint      green    0.0 min  .checks/lint.txt")
'''


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=cwd,
                          capture_output=True, text=True)


def a_clone_with_the_hook(tmp_path, code):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    work.mkdir()
    (work / ".githooks").mkdir()
    shutil.copy(HOOK, work / ".githooks" / "pre-push")
    (work / "checks.py").write_text(STAND_IN)
    (work / "app.py").write_text(code)
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "core.hooksPath", ".githooks")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "start")
    return remote, work


def test_a_push_with_a_red_check_is_refused_prints_the_checks_lines_and_the_remote_does_not_get_the_commit(tmp_path):
    remote, work = a_clone_with_the_hook(tmp_path, "x = 1\ny = 2  # two\n")
    pushed = git(work, "push", "-q", "origin", "main")
    assert pushed.returncode != 0
    assert "app.py:2: a comment; say it in a name instead" in pushed.stderr + pushed.stdout
    assert git(remote, "rev-parse", "--verify", "-q", "main").stdout == ""


def test_a_push_with_every_check_green_arrives_and_the_hook_prints_nothing(tmp_path):
    remote, work = a_clone_with_the_hook(tmp_path, "x = 1\n")
    pushed = git(work, "push", "-q", "origin", "main")
    assert pushed.returncode == 0, pushed.stderr
    assert "green" not in pushed.stderr + pushed.stdout
    assert git(remote, "rev-parse", "main").stdout == git(work, "rev-parse", "HEAD").stdout

