"""Walk: the watchlist's ⋯ menu: rename, manage saved search, full recheck, delete (ticket 13, design 13, 12/F).

Data: helper.seed_queue (the long-named watchlist with three trials, and "Quiet" with one
shared trial) plus a saved search on the first. Lacks: many watchlists, a rename racing a
check, a delete while a check runs.
"""

from __future__ import annotations

import re

from walks import helper
from walks.test_check_walk import seed_checked


def open_app(make_app, make_walk):
    app = make_app(seed=seed_checked)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    return app, walk


def choose(page, item):
    page.get_by_role("button", name="Watchlist actions").click()
    page.get_by_role("menuitem", name=item).click()


def test_walk_the_menu_offers_four_actions_and_each_opens_its_own_dialog(make_app, make_walk):
    """test_walk_the_menu_offers_four_actions_and_each_opens_its_own_dialog"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Watchlist actions").click()
    items = page.get_by_role("menuitem")
    assert [items.nth(i).inner_text() for i in range(items.count())] == [
        "Rename watchlist", "Manage saved search", "Full recheck", "Delete watchlist"]
    walk.shot("menu")
    titles = {}
    for item, title in (("Rename watchlist", "Rename watchlist"), ("Manage saved search", "Manage saved search"),
                        ("Full recheck", "Full recheck"), ("Delete watchlist", f"Delete “{helper.LONG_NAME}”?")):
        if not page.get_by_role("menuitem", name=item).is_visible():
            page.get_by_role("button", name="Watchlist actions").click()
        page.get_by_role("menuitem", name=item).click()
        dialog = page.get_by_role("dialog", name=title)
        dialog.wait_for()
        # One task per dialog: the other actions' buttons are not here.
        names = [dialog.get_by_role("button").nth(i).inner_text() for i in range(dialog.get_by_role("button").count())]
        titles[item] = names
        page.keyboard.press("Escape")
        dialog.wait_for(state="detached")
        page.wait_for_function("document.activeElement.id === 'watchlist-menu-button'")  # focus returns to the menu button
    assert "Create watchlist" not in sum(titles.values(), [])
    assert titles["Rename watchlist"] == ["Cancel", "Save name"]
    assert titles["Delete watchlist"] == ["Cancel", "Delete watchlist"]
    assert titles["Full recheck"] == ["Cancel", "Start full recheck"]


def test_walk_rename_shows_the_current_name_refuses_empty_and_duplicate_inline_and_keeps_the_place(make_app, make_walk):
    """test_walk_rename_shows_the_current_name_refuses_empty_and_duplicate_inline_and_keeps_the_place"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    page.evaluate("document.body.style.minHeight = '3000px'")
    url = page.url
    choose(page, "Rename watchlist")  # the click brings the menu into view, so scroll once the dialog is open
    page.evaluate("window.scrollTo(0, 250)")
    assert page.evaluate("window.scrollY") == 250  # the page really scrolls
    dialog = page.get_by_role("dialog", name="Rename watchlist")
    name = dialog.get_by_label("Watchlist name")
    assert name.input_value() == helper.LONG_NAME
    name.fill("   ")
    dialog.get_by_role("button", name="Save name").click()
    dialog.get_by_text("Give the watchlist a name.").wait_for()
    walk.expect(409, "/api/watchlists/1/rename")
    name.fill("quiet")
    dialog.get_by_role("button", name="Save name").click()
    dialog.get_by_text("There is already a watchlist called “quiet”.").wait_for()
    walk.shot("duplicate")
    dialog.get_by_role("button", name="Cancel").click()
    dialog.wait_for(state="detached")
    assert page.url == url and page.evaluate("window.scrollY") == 250
    assert page.get_by_role("heading", level=1).inner_text() == helper.LONG_NAME
    page.evaluate("window.scrollTo(0, 0)")
    choose(page, "Rename watchlist")
    page.evaluate("window.scrollTo(0, 250)")
    dialog = page.get_by_role("dialog", name="Rename watchlist")
    dialog.get_by_label("Watchlist name").fill("Lung, renamed")
    dialog.get_by_role("button", name="Save name").click()
    dialog.wait_for(state="detached")
    page.get_by_role("heading", level=1, name="Lung, renamed").wait_for()
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Lung, renamed")).wait_for()
    assert page.url == url and page.evaluate("window.scrollY") == 250
    walk.shot("renamed")


def test_walk_full_recheck_explains_itself_runs_once_and_finishes_with_its_own_label(make_app, make_walk):
    """test_walk_full_recheck_explains_itself_runs_once_and_finishes_with_its_own_label"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    choose(page, "Full recheck")
    dialog = page.get_by_role("dialog", name="Full recheck")
    text = dialog.inner_text()
    assert "compares every monitored field" in text and "even when the registry's update date has not moved" in text, text
    walk.shot("explained")
    dialog.get_by_role("button", name="Start full recheck").click()
    status = page.get_by_role("status")
    status.get_by_text(re.compile("^Full recheck complete")).wait_for(timeout=30000)
    walk.shot("full-complete")
    # Once: the next normal check carries the normal label.
    page.get_by_role("button", name="Check for updates").click()
    status.get_by_text(re.compile("^Check complete")).wait_for(timeout=30000)
    assert "Full recheck" not in status.inner_text()


def test_walk_delete_names_the_watchlist_states_what_goes_and_stays_and_lands_on_another(make_app, make_walk):
    """test_walk_delete_names_the_watchlist_states_what_goes_and_stays_and_lands_on_another"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Quiet")).click()
    page.get_by_role("heading", level=1, name="Quiet").wait_for()
    choose(page, "Delete watchlist")
    dialog = page.get_by_role("dialog", name="Delete “Quiet”?")
    text = dialog.inner_text()
    assert "removes this watchlist, its saved search and its trial memberships" in text, text
    assert "Trials in other watchlists are unchanged." in text
    assert "Monitoring history is kept. Trials with no remaining watchlist stop being checked." in text
    assert "cannot be undone" in text
    walk.shot("delete")
    dialog.get_by_role("button", name="Cancel").click()
    assert page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Quiet")).count() == 1
    choose(page, "Delete watchlist")
    page.get_by_role("dialog", name="Delete “Quiet”?").get_by_role("button", name="Delete watchlist").click()
    page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    assert page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Quiet")).count() == 0
    # The trial it shared is still in the other watchlist, unchanged.
    assert "3 trials" in page.locator("#watchlist-meta").inner_text()
    walk.shot("after-delete")
