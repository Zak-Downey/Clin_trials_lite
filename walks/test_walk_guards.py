"""Walk guards: each fails a walk when its condition occurs.

Runs walks/broken/broken_pages.py, whose pages are broken on purpose, in a
separate pytest and reads which walks it failed. Lacks: the guards under
WebKit or Firefox, and a covered element (Playwright's own click refuses one).
"""

from __future__ import annotations

import pathlib

import pytest
import subprocess
import sys

BROKEN = pathlib.Path(__file__).parent / "broken" / "broken_pages.py"
ROOT = BROKEN.parent.parent.parent


@pytest.fixture(scope="module")
def broken_run(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("broken")
    out = subprocess.run(
        [sys.executable, "-m", "pytest", str(BROKEN), "-q", "-p", "no:cacheprovider", "-rf",
         "--basetemp", str(tmp_path / "inner")],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    ).stdout
    return out


def failing(output, name):
    return [line for line in output.splitlines() if line.startswith("FAILED") and name in line]


def test_walk_guard_fails_a_walk_on_a_console_error(broken_run):
    """test_walk_guard_fails_a_walk_on_a_console_error"""
    out = broken_run
    assert failing(out, "test_broken_console_error"), out
    assert "console error: deliberate console error" in out


def test_walk_guard_fails_a_walk_on_a_failed_request_or_one_to_somewhere_else(broken_run):
    """test_walk_guard_fails_a_walk_on_a_failed_request_or_one_to_somewhere_else"""
    out = broken_run
    assert failing(out, "test_broken_failed_request"), out
    assert failing(out, "test_broken_foreign_request"), out
    assert "missing-file.js (status 404)" in out
    assert "not the app's own server" in out


def test_walk_guard_fails_a_walk_on_an_uncaught_page_error(broken_run):
    """test_walk_guard_fails_a_walk_on_an_uncaught_page_error"""
    out = broken_run
    assert failing(out, "test_broken_page_error"), out


def test_walk_guard_fails_a_walk_on_horizontal_scrolling(broken_run):
    """test_walk_guard_fails_a_walk_on_horizontal_scrolling"""
    out = broken_run
    assert failing(out, "test_broken_sideways_scroll"), out
    assert "horizontal scrolling" in out
