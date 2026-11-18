"""early-read-whole-01: the tests that hold ruff.toml to "exempts nothing" pass while the linter is told to exempt.

Each case builds a small git repo in a temporary folder: this repo's ruff.toml and requirements-dev.txt,
plus one exemption the spec forbids, and a file with an unused import that Ruff then does not report.
It points tests/test_lint.py at that folder and expects one of its tests to fail. Red while none does.
Run: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-2/findings/scripts/early-read-whole-01.py -q
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests import test_lint

REPO = Path(__file__).resolve().parents[4]
UNUSED = "import os\n"

CASES = {
    # An unused import allowed by name in ruff.toml itself.
    "allowed-unused-imports": ({"ruff.toml": "\n[lint.pyflakes]\nallowed-unused-imports = [\"os\"]\n"}, "pkg/a.py"),
    # A second config in a folder, which Ruff uses for that folder in place of the root one.
    "nested-config": ({"pkg/ruff.toml": "[lint]\nselect = []\n"}, "pkg/a.py"),
    # A whole file silenced from inside it.
    "file-level-noqa": ({}, "pkg/a.py", "# ruff: noqa\n"),
}


def build(tmp, extra, target, head=""):
    shutil.copy(REPO / "ruff.toml", tmp / "ruff.toml")
    shutil.copy(REPO / "requirements-dev.txt", tmp / "requirements-dev.txt")
    (tmp / "pkg").mkdir()
    for name, text in extra.items():
        path = tmp / name
        path.write_text((path.read_text() if path.exists() else "") + text)
    (tmp / target).write_text(head + UNUSED)
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)


@pytest.mark.parametrize("case", list(CASES))
def test_an_exemption_turns_a_lint_test_red(case, tmp_path, monkeypatch):
    build(tmp_path, *CASES[case])
    ruff = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "."], cwd=tmp_path,
                          capture_output=True, text=True)
    assert ruff.returncode == 0, "set-up: Ruff should be silenced here"  # the exemption works
    monkeypatch.setattr(test_lint, "ROOT", tmp_path)
    tests = [getattr(test_lint, n) for n in dir(test_lint) if n.startswith("test_")]
    failed = []
    for test in tests:
        try:
            test()
        except AssertionError:
            failed.append(test.__name__)
        except subprocess.CalledProcessError:
            failed.append(test.__name__)
    assert failed, f"{case}: every test in tests/test_lint.py passed while Ruff was told to exempt"
