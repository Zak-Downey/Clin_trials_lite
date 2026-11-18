"""The linter's rules, read from the files that set them.

Nothing here re-tests Ruff. It holds what this repo decided: the version is pinned to one exact
release, the rule groups are exactly the agreed ones and none is left to Ruff's defaults, `.scratch/`
(records, not code) is not read, and no rule, file or folder is exempted.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

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
    top = config()
    lint = top.get("lint", {})
    for key in ("ignore", "extend-ignore", "per-file-ignores", "extend-per-file-ignores",
                "exclude", "include", "extend-include"):
        assert key not in top, key
        assert key not in lint, key
    assert top.get("extend-exclude") == [".scratch"]
    assert "extend-exclude" not in lint
    assert top.get("force-exclude", False) is False


def test_ruff_reads_every_tracked_python_file_outside_scratch_and_nothing_under_scratch_or_venv():
    tracked = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.split()
    shown = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "--show-files", "."],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    read = {str(Path(p).resolve().relative_to(ROOT)) for p in shown if p.endswith(".py")}
    assert not [p for p in read if p.startswith((".scratch/", ".venv/"))]
    assert {p for p in tracked if not p.startswith(".scratch/")} <= read
