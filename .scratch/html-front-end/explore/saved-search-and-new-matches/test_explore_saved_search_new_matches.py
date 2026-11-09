"""Red scripts from the exploration of saved search and new matches (ticket 16).

Run by path: .venv/bin/python -m pytest .scratch/html-front-end/explore/saved-search-and-new-matches -q
Each test is red because of one defect (see explore/saved-search-and-new-matches.md).
"""
from __future__ import annotations

import re

from walks.test_new_matches_walk import open_tab, box
from walks.test_saved_search_walk import dialog, results, seed as saved_seed


def focus(page):
    return page.evaluate("document.activeElement === document.body ? 'body' : document.activeElement.tagName + ' ' + (document.activeElement.textContent || '').trim().slice(0, 30)")


def test_focus_stays_in_the_page_after_dismiss_undo_and_add(make_app, make_walk):
    _, walk = open_tab(make_app, make_walk)
    page = walk.page
    box(page, "NCT00000002").check()
    page.get_by_role("button", name="Dismiss 1").click()
    page.get_by_role("button", name="Yes, dismiss 1").click()
    page.get_by_role("button", name="Undo").wait_for()
    assert focus(page) != "body", "after Dismiss focus fell to the page body"
    page.get_by_role("button", name="Undo").click()
    page.get_by_text("Undone.").wait_for()
    assert focus(page) != "body", "after Undo focus fell to the page body"
    box(page, "NCT00000002").check()
    page.get_by_role("button", name=re.compile("^Add 1")).click()
    page.get_by_text("1 added").wait_for()
    assert focus(page) != "body", "after Add focus fell to the page body"


def test_focus_returns_after_turn_off_closes_the_dialog(make_app, make_walk):
    _, walk = open_tab(make_app, make_walk, tab=None)
    page = walk.page
    page.get_by_role("button", name="Manage").click()
    page.get_by_role("button", name="Turn off").click()
    page.get_by_text("Saved search is on").wait_for(state="detached")
    walk.shot("after-turn-off")
    assert focus(page) != "body", "after Turn off focus fell to the page body"


def test_undo_that_the_server_refuses_says_so_and_can_be_pressed_again(make_app, make_walk):
    app, walk = open_tab(make_app, make_walk, watchlist="Quiet")
    page = walk.page
    walk.expect(404, page.evaluate("location.origin").replace(app.url.rstrip("/"), "") + "/api/watchlists/2/new-matches/undo")
    box(page, "NCT00000002").check()
    page.get_by_role("button", name="Dismiss 1").click()
    page.get_by_role("button", name="Yes, dismiss 1").click()
    page.get_by_role("button", name="Undo").wait_for()
    # Another window deletes the watchlist.
    other = page.context.new_page()
    other.goto(app.url)
    other.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Quiet")).click()
    other.get_by_role("heading", level=1, name="Quiet").wait_for()
    other.get_by_role("button", name="Watchlist actions").click()
    other.get_by_role("menuitem", name="Delete watchlist").click()
    other.get_by_role("dialog").get_by_role("button", name="Delete watchlist").click()
    other.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Quiet")).wait_for(state="detached")
    page.get_by_role("button", name="Undo").click()
    page.wait_for_timeout(800)
    walk.shot("undo-refused")
    text = page.locator("body").inner_text()
    assert page.get_by_role("alert").filter(has_text=re.compile(".+")).count() or "no longer" in text or "not found" in text.lower(), \
        "Undo was refused and the page said nothing"
    assert not page.get_by_role("button", name="Undo").is_disabled(), "Undo stayed disabled after the failure"


def test_dismissing_a_match_already_added_elsewhere_does_not_claim_it_was_dismissed(make_app, make_walk):
    app, walk = open_tab(make_app, make_walk)
    page = walk.page
    other = page.context.new_page()
    other.goto(page.url)
    other.get_by_role("tab", name=re.compile("^New matches")).click()
    other.get_by_role("heading", level=2, name=re.compile("new match")).wait_for()
    box(other, "NCT00000002").check()
    other.get_by_role("button", name=re.compile("^Add 1")).click()
    other.get_by_text("1 added").wait_for()
    box(page, "NCT00000002").check()  # this window still offers it
    page.get_by_role("button", name="Dismiss 1").click()
    page.get_by_role("button", name="Yes, dismiss 1").click()
    page.wait_for_timeout(800)
    walk.shot("stale-dismiss")
    text = page.locator("body").inner_text()
    assert "0 trials dismissed" not in text, "the bar says 0 trials dismissed, will not be suggested again, with an Undo"


def test_a_long_unbroken_condition_keeps_find_trials_inside_the_window(make_app, make_walk):
    app = make_app(seed=saved_seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/find")
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    page.get_by_label("Condition").fill("z" * 150)
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="3 matches").wait_for()
    walk.shot("long-condition")
    # the guard reports a page wider than the window when the test ends; assert it now as well
    wide = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert wide <= 0, f"the page is {wide}px wider than the window; Watch this search and Edit search are pushed off its edge"


def test_the_watch_dialog_shows_no_empty_warning_strip_for_a_watchlist_without_a_saved_search(make_app, make_walk):
    _, walk = results(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    watch.get_by_role("button", name="Watch this search").wait_for()
    walk.shot("empty-strip")
    box_ = watch.locator(".replace-warning").bounding_box()
    assert box_ is None or box_["height"] < 1, f"an empty {box_['height']}px warning strip is drawn above the buttons"
