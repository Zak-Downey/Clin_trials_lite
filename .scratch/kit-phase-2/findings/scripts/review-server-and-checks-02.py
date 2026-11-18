"""review-server-and-checks-02: a bare `# noqa` on a line silences the linter and every check stays green.

A small git repo in a temporary folder holds this repo's ruff.toml and requirements-dev.txt and one
file whose unused import carries a bare `# noqa` (no rule named, no reason). Ruff reports nothing,
and every rule test in tests/test_lint.py passes when pointed at that folder. Red while none fails.
Run: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-2/findings/scripts/review-server-and-checks-02.py -q
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from tests import test_lint


def test_a_bare_noqa_turns_a_rule_test_red(tmp_path, monkeypatch):
    for name in ("ruff.toml", "requirements-dev.txt"):
        shutil.copy(test_lint.ROOT / name, tmp_path / name)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("import os  # noqa\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "."], cwd=tmp_path,
                          capture_output=True, text=True)
    assert ruff.returncode == 0, ruff.stdout  # the unused import is silenced, so the lint check is green
    monkeypatch.setattr(test_lint, "ROOT", tmp_path)
    rules = [test for name, test in vars(test_lint).items()
             if name.startswith("test_") and name != "test_each_way_of_exempting_code_turns_a_rule_test_red"]
    failed = []
    for test in rules:
        try:
            test()
        except (AssertionError, subprocess.CalledProcessError):
            failed.append(test.__name__)
    assert failed, "every rule test passed while a bare # noqa silenced an unused import"
