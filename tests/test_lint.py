"""The linter's rules, read from the files that set them.

Nothing here re-tests Ruff. It holds what this repo decided: the version is pinned to one exact
release, the rule groups are exactly the agreed ones and none is left to Ruff's defaults, `.scratch/`
(records, not code) is not read, and no rule, file or folder is exempted.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RULES = ["E4", "E7", "E9", "F", "RUF100"]


def config():
    return tomllib.loads((ROOT / "ruff.toml").read_text(encoding="utf-8"))


def test_requirements_dev_pins_ruff_to_one_exact_version():
    lines = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    ruff = [line.split("#")[0].strip() for line in lines if re.match(r"\s*ruff\b", line, re.I)]
    assert len(ruff) == 1
    assert re.fullmatch(r"ruff==\d+\.\d+\.\d+", ruff[0])


def test_ruff_toml_selects_exactly_the_agreed_rule_groups():
    lint = config().get("lint", {})
    assert lint.get("select") == RULES
    assert "select" not in config()
    assert not any(key.startswith("extend-select") for key in lint)


def test_ruff_toml_states_the_python_version_of_this_repos_venv():
    major, minor = sys.version_info[:2]
    assert config().get("target-version") == f"py{major}{minor}"


def test_ruff_toml_exempts_no_rule_file_or_folder_but_leaves_scratch_unread():
    # Held to exactly the agreed keys, so any setting that skips code (an ignore list, an allowed
    # unused import, an exclude) turns this red without being named here.
    top = config()
    assert set(top) == {"target-version", "extend-exclude", "lint"}
    assert set(top["lint"]) == {"select"}
    assert top["extend-exclude"] == [".scratch"]


def test_ruff_toml_at_the_root_is_the_only_ruff_config():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.split()
    configs = [p for p in tracked if Path(p).name in ("ruff.toml", ".ruff.toml")
               or (Path(p).name == "pyproject.toml" and "[tool.ruff" in (ROOT / p).read_text(encoding="utf-8"))]
    assert configs == ["ruff.toml"]


def test_no_python_file_silences_the_linter_for_the_whole_file():
    tracked = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.split()
    blanket = re.compile(r"^\s*#\s*(ruff|flake8)\s*:\s*noqa", re.I | re.M)
    silenced = [p for p in tracked if not p.startswith(".scratch/")
                and blanket.search((ROOT / p).read_text(encoding="utf-8"))]
    assert silenced == []


def test_ruff_reads_every_tracked_python_file_outside_scratch_and_nothing_under_scratch_or_venv():
    tracked = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.split()
    shown = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "--show-files", "."],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    read = {str(Path(p).resolve().relative_to(ROOT)) for p in shown if p.endswith(".py")}
    assert not [p for p in read if p.startswith((".scratch/", ".venv/"))]
    assert {p for p in tracked if not p.startswith(".scratch/")} <= read


# Each way of telling Ruff to skip code that the rule tests must catch: an unused import allowed
# by name in ruff.toml, a second config that switches the rules off in one folder, and a file
# silenced from inside it. Each case is a small copy of the repo where Ruff would report nothing.
EXEMPTIONS = {
    "allowed-unused-imports": ({"ruff.toml": '\n[lint.pyflakes]\nallowed-unused-imports = ["os"]\n'}, ""),
    "nested-config": ({"pkg/ruff.toml": "[lint]\nselect = []\n"}, ""),
    "file-level-noqa": ({}, "# ruff: noqa\n"),
}


@pytest.mark.parametrize("case", list(EXEMPTIONS))
def test_each_way_of_exempting_code_turns_a_rule_test_red(case, tmp_path, monkeypatch):
    extra, head = EXEMPTIONS[case]
    for name in ("ruff.toml", "requirements-dev.txt"):
        shutil.copy(ROOT / name, tmp_path / name)
    (tmp_path / "pkg").mkdir()
    for name, text in extra.items():
        path = tmp_path / name
        path.write_text((path.read_text() if path.exists() else "") + text)
    (tmp_path / "pkg" / "a.py").write_text(head + "import os\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    rules = [test for name, test in globals().items()
             if name.startswith("test_") and name != "test_each_way_of_exempting_code_turns_a_rule_test_red"]
    failed = []
    for test in rules:
        try:
            test()
        except (AssertionError, subprocess.CalledProcessError):
            failed.append(test.__name__)
    assert failed, f"{case}: every rule test passed while Ruff was told to skip code"
