"""Exploration, dialogs and administration (ticket 16). Each test is red because of one defect.

Run by path, with the walk fixtures:
    .venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/dialogs-and-administration/test_explore_dialogs_and_administration.py -q
Data: helper.seed_queue plus a saved search (seed_checked), or an empty database (the one
default watchlist). Lacks: many watchlists. Screenshots land in .scratch/html-front-end/walks/.
"""

from __future__ import annotations

import os
import subprocess
import sys

from walks import helper
from walks.test_check_walk import seed_checked

ROOT = helper.ROOT


def open_menu_item(page, item):
    page.get_by_role("button", name="Watchlist actions").click()
    page.get_by_role("menuitem", name=item).click()


def test_explore_an_empty_watchlist_can_be_renamed_and_deleted(make_app, make_walk):
    """test_explore_an_empty_watchlist_can_be_renamed_and_deleted"""
    app = make_app()  # a fresh database: one empty default watchlist
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=2, name="Monitor your first trial").wait_for()
    walk.shot("first-use-no-menu")
    # A mistaken or unwanted empty watchlist has no way to be renamed or deleted.
    assert page.get_by_role("button", name="Watchlist actions").count() == 1


def test_explore_deleting_the_last_watchlist_leaves_focus_somewhere_usable(make_app, make_walk):
    """test_explore_deleting_the_last_watchlist_leaves_focus_somewhere_usable"""
    app = make_app(seed=seed_checked)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    for _ in range(2):
        page.get_by_role("heading", level=1).first.wait_for()
        open_menu_item(page, "Delete watchlist")
        page.get_by_role("dialog").get_by_role("button", name="Delete watchlist").click()
        page.wait_for_function("!document.querySelector('dialog')")
        page.wait_for_timeout(500)
    page.get_by_text("No watchlists yet").wait_for()
    walk.shot("no-watchlists")
    # Focus fell to the page body: a keyboard user starts again from the top.
    assert page.evaluate("document.activeElement !== document.body")


def test_explore_the_delete_dialog_title_shows_a_long_unbroken_name(make_app, make_walk):
    """test_explore_the_delete_dialog_title_shows_a_long_unbroken_name"""
    app = make_app(seed=seed_checked)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    open_menu_item(page, "Rename watchlist")
    dialog = page.get_by_role("dialog", name="Rename watchlist")
    dialog.get_by_label("Watchlist name").fill("W" * 120)
    dialog.get_by_role("button", name="Save name").click()
    dialog.wait_for(state="detached")
    open_menu_item(page, "Delete watchlist")
    title = page.get_by_role("dialog").get_by_role("heading", level=2)
    walk.shot("long-delete-title")
    # The name being deleted runs out of the dialog's box and is clipped.
    assert title.evaluate("e => e.scrollWidth <= e.clientWidth")


def test_explore_enter_on_check_for_updates_keeps_keyboard_focus(make_app, make_walk, registry):
    """test_explore_enter_on_check_for_updates_keeps_keyboard_focus"""
    app = make_app(seed=seed_checked)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    registry.set("slow", True, delay=3)
    page.get_by_role("button", name="Check for updates").focus()
    page.keyboard.press("Enter")
    page.get_by_text("Checking for updates…").wait_for()
    walk.shot("focus-after-check")
    # The button is disabled while it runs and focus drops to the body.
    assert page.evaluate("document.activeElement !== document.body")


def test_explore_full_recheck_while_a_check_runs_says_why_nothing_started(make_app, make_walk, registry):
    """test_explore_full_recheck_while_a_check_runs_says_why_nothing_started"""
    app = make_app(seed=seed_checked)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    registry.set("slow", True, delay=3)
    page.get_by_role("button", name="Check for updates").click()
    page.get_by_text("Checking for updates…").wait_for()
    walk.expect(409, "/api/watchlists/1/recheck")
    open_menu_item(page, "Full recheck")
    page.get_by_role("dialog").get_by_role("button", name="Start full recheck").click()
    page.wait_for_function("!document.querySelector('dialog')")
    page.wait_for_timeout(500)
    walk.shot("recheck-while-busy")
    # The dialog closed as if it had started; the refusal is never shown to the user.
    assert "already" in page.locator("#view").inner_text().lower().replace("a check is already running.", "") \
        or page.locator("#view .error").count() > 0


def _run_py(env_db, *args, timeout=15):
    env = {**os.environ, "MONITOR_DB": env_db}
    return subprocess.Popen([sys.executable, str(ROOT / "run.py"), "--no-browser", *args],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_explore_a_second_start_through_a_symlink_does_not_start_a_second_server(tmp_path):
    """test_explore_a_second_start_through_a_symlink_does_not_start_a_second_server"""
    db = tmp_path / "a.db"
    link = tmp_path / "link.db"
    link.symlink_to(db)
    first = _run_py(str(db))
    second = None
    try:
        first.stdout.readline()
        second = _run_py(str(link))
        try:
            out, _ = second.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            out = "still serving: a second server holds the same database"
            second.terminate()
            second.wait(timeout=10)
        assert "already running" in out, out
    finally:
        for proc in (first, second):
            if proc and proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=10)


def test_explore_an_impossible_port_is_a_sentence_not_a_traceback(tmp_path):
    """test_explore_an_impossible_port_is_a_sentence_not_a_traceback"""
    proc = _run_py(str(tmp_path / "b.db"), "--port", "99999")
    out, err = proc.communicate(timeout=15)
    assert "Traceback" not in err, err
