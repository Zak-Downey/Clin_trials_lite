"""Walk guards: each fails a walk when its condition occurs.

Runs walks/broken/broken_pages.py, whose pages are broken on purpose, in a
separate pytest and reads which walks it failed. Lacks: the guards under
WebKit or Firefox, and a covered element (Playwright's own click refuses one).
"""

from __future__ import annotations

import pathlib
import re

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


def blocks(output, name):
    """The failure blocks of the walk `name` (one per viewport): its header to the next header."""
    found, inside = [], False
    for line in output.splitlines():
        header = re.fullmatch(r"_+ (\S+) _+", line)
        if header:
            inside = header.group(1).startswith(name + "[")
            if inside:
                found.append([])
        elif inside:
            found[-1].append(line)
    return ["\n".join(b) for b in found]


def in_block(output, name, text):
    """Whether every viewport's failure block of `name` holds `text`, and there is one."""
    found = blocks(output, name)
    return bool(found) and all(text in b for b in found)


def test_walk_guard_fails_a_walk_on_a_console_error(broken_run):
    """test_walk_guard_fails_a_walk_on_a_console_error"""
    out = broken_run
    assert failing(out, "test_broken_console_error"), out
    assert in_block(out, "test_broken_console_error", "console error: deliberate console error"), out


def test_walk_guard_fails_a_walk_on_a_failed_request_or_one_to_somewhere_else(broken_run):
    """test_walk_guard_fails_a_walk_on_a_failed_request_or_one_to_somewhere_else"""
    out = broken_run
    assert failing(out, "test_broken_failed_request"), out
    assert failing(out, "test_broken_foreign_request"), out
    assert in_block(out, "test_broken_failed_request", "missing-file.js (status 404)"), out
    assert in_block(out, "test_broken_foreign_request", "not the app's own server"), out


def test_walk_guard_fails_a_walk_on_an_uncaught_page_error(broken_run):
    """test_walk_guard_fails_a_walk_on_an_uncaught_page_error"""
    out = broken_run
    assert failing(out, "test_broken_page_error"), out


def test_walk_guard_fails_a_walk_on_horizontal_scrolling(broken_run):
    """test_walk_guard_fails_a_walk_on_horizontal_scrolling"""
    out = broken_run
    assert failing(out, "test_broken_sideways_scroll"), out
    assert in_block(out, "test_broken_sideways_scroll", "horizontal scrolling"), out


def test_walk_guard_fails_a_walk_on_a_request_to_the_app_that_gets_no_answer(broken_run):
    """test_walk_guard_fails_a_walk_on_a_request_to_the_app_that_gets_no_answer"""
    out = broken_run
    assert failing(out, "test_broken_request_to_the_app_that_gets_no_answer"), out
    assert in_block(out, "test_broken_request_to_the_app_that_gets_no_answer", "/static/aborted.js (net::ERR"), out
    assert not in_block(out, "test_broken_request_to_the_app_that_gets_no_answer", "not the app's own server: "), out


def test_walk_guard_fails_a_walk_that_was_wide_only_at_a_screenshot_or_in_a_region(broken_run):
    """test_walk_guard_fails_a_walk_that_was_wide_only_at_a_screenshot_or_in_a_region"""
    out = broken_run
    assert failing(out, "test_broken_sideways_scroll_only_in_the_middle"), out
    assert failing(out, "test_broken_region_that_scrolls_sideways"), out
    assert in_block(out, "test_broken_region_that_scrolls_sideways", "div#strip scrolls sideways inside the page"), out


def test_walk_guard_keeps_the_first_of_two_pages_and_a_closed_pages_findings(broken_run):
    """test_walk_guard_keeps_the_first_of_two_pages_and_a_closed_pages_findings"""
    out = broken_run
    assert failing(out, "test_broken_first_of_two_pages_has_an_error"), out
    assert in_block(out, "test_broken_first_of_two_pages_has_an_error", "error on the first page"), out
    assert failing(out, "test_broken_page_closed_after_an_error"), out
    assert in_block(out, "test_broken_page_closed_after_an_error", "error before the page closed"), out


def test_walk_guard_fails_an_expected_response_that_never_came_or_came_elsewhere(broken_run):
    """test_walk_guard_fails_an_expected_response_that_never_came_or_came_elsewhere"""
    out = broken_run
    assert failing(out, "test_broken_expected_response_that_never_comes"), out
    assert in_block(out, "test_broken_expected_response_that_never_comes", "expected response never came: 404 /api/watchlists"), out
    assert failing(out, "test_broken_other_status_than_the_expected_one"), out
    assert in_block(out, "test_broken_other_status_than_the_expected_one", "/api/watchlists/998/needs-review (status 404)"), out


def test_walk_guard_does_not_take_a_longer_port_for_the_apps_own_origin():
    """test_walk_guard_does_not_take_a_longer_port_for_the_apps_own_origin"""
    from types import SimpleNamespace

    from walks import helper

    class Page:
        def on(self, *_):
            pass

    guards = helper.Guards(Page(), "http://127.0.0.1:5803")
    for url in ("http://127.0.0.1:5803", "http://127.0.0.1:5803/api/x", "data:text/plain,x"):
        guards._foreign(SimpleNamespace(url=url))
    assert guards.found == []
    guards._foreign(SimpleNamespace(url="http://127.0.0.1:58032/api/x"))
    assert guards.found == ["failed request: http://127.0.0.1:58032/api/x (not the app's own server)"]


def test_walk_second_page_shots_keep_their_own_names(make_app, make_walk):
    """test_walk_second_page_shots_keep_their_own_names"""
    app = make_app()
    first, second = make_walk(app), make_walk(app)
    assert first.name != second.name
    assert second.name.endswith("-page2")
