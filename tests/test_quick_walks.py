"""A quick run's walks: what pytest collects from the walk files with and without the quick setting.

Collection only: no browser starts and no walk runs.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = ["walks/test_walk_guards.py", "walks/test_acceptance_walk.py", "walks/test_summary_walk.py"]


def collected(quick: bool) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k != "WALK_QUICK"}
    if quick:
        env["WALK_QUICK"] = "1"
    done = subprocess.run([sys.executable, "-m", "pytest", *FILES, "--collect-only", "-q", "-p", "no:cacheprovider"],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    return [line for line in done.stdout.splitlines() if "::" in line]


def test_a_walk_runs_at_both_window_sizes_in_a_full_run_and_at_the_first_only_in_a_quick_run():
    full = [n for n in collected(False) if "test_summary_walk" in n]
    quick = [n for n in collected(True) if "test_summary_walk" in n]
    assert full and any(n.endswith("[1440x900]") for n in full) and any(n.endswith("[1024x768]") for n in full)
    assert quick == [n for n in full if n.endswith("[1440x900]")]


def test_the_acceptance_walk_keeps_chromium_and_webkit_at_the_first_size_in_a_quick_run():
    quick = {n.split("[")[1] for n in collected(True) if "test_acceptance_walk" in n}
    assert quick == {"chromium-1440x900]", "webkit-1440x900]"}


def test_every_walk_guard_test_is_still_collected_in_a_quick_run():
    def guards(quick):
        return {n.split("[")[0] for n in collected(quick) if "test_walk_guards" in n}
    full = guards(False)
    assert len(full) >= 10
    assert guards(True) == full
