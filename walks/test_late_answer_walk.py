"""Walk: a late answer never draws over the page the analyst moved to, and the sidebar keeps its mark (ticket 03).

Data: helper.seed_queue (the long-named watchlist with three trials, and "Quiet" with one).
Answers are held in the browser (Playwright route) and released by the walk, so "late" is exact.
Lacks: a late answer on the Registry details or Find trials pages (they already take `alive`),
three or more watchlists, a late answer racing a finished check.
"""

from __future__ import annotations

import re

import pytest

from walks import helper


def open_app(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("heading", level=1, name=helper.LONG_NAME).wait_for()
    return app, walk


def sidebar_link(page, name):
    return page.get_by_label("Watchlists").get_by_role("link", name=re.compile(f"^{name}"))


def hold_first(page, pattern):
    """Hold the first request matching pattern; let every later one through. Returns the held routes."""
    held = []

    def handler(route):
        if held:
            route.continue_()
        else:
            held.append(route)

    page.route(pattern, handler)
    return held


def release(page, held, pattern):
    """Let the held request go and wait until the page has had time to draw what came back."""
    with page.expect_response(pattern):
        held[0].continue_()
    page.evaluate("new Promise((done) => setTimeout(done, 300))")


def test_walk_a_delayed_trial_answer_leaves_the_watchlist_the_address_names(make_app, make_walk):
    """test_walk_a_delayed_trial_answer_leaves_the_watchlist_the_address_names"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    pattern = "**/api/trials/NCT03412565"
    held = hold_first(page, pattern)
    page.get_by_role("link", name="Review changes").first.click()
    page.wait_for_function("location.hash.startsWith('#/trials/')")
    sidebar_link(page, "Quiet").click()
    page.wait_for_url(re.compile(r"#/watchlists/2/"))
    page.get_by_role("heading", name="All caught up").wait_for()
    assert held, "the trial's answer was never asked for"
    release(page, held, pattern)
    walk.shot("after-late-trial")
    assert page.url.endswith("#/watchlists/2/needs-review"), page.url
    assert page.get_by_role("heading", name="All caught up").count() == 1, "the address names Quiet but the page shows the trial"
    assert page.get_by_role("link", name="Back to Quiet").count() == 0 and page.locator(".trial-head").count() == 0


def tab_answer(tab):
    return {"Needs review": "**/api/watchlists/1/needs-review", "All trials": "**/api/watchlists/1/all-trials",
            "Summary": "**/api/watchlists/1/summary?*"}[tab]


@pytest.mark.parametrize("tab, start, side", [("Needs review", "All trials", True), ("All trials", "Needs review", True), ("Summary", "Needs review", True),
                                               ("Needs review", "All trials", False), ("All trials", "Needs review", False), ("Summary", "Needs review", False)])
def test_walk_a_delayed_answer_for_a_tab_already_left_does_not_replace_the_page_the_address_names(make_app, make_walk, tab, start, side):
    """test_walk_a_delayed_answer_for_a_tab_already_left_does_not_replace_the_page_the_address_names"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    if start != "Needs review":
        page.get_by_role("tab", name=re.compile(start)).click()
        page.get_by_label("Filter by title, NCT ID or sponsor").wait_for()
    # The tab's own answers, and the sidebar's, are held for the first click only: the tab is left before they land.
    held_tab = hold_first(page, tab_answer(tab))
    held_side = hold_first(page, "**/api/watchlists") if side else []
    page.get_by_role("tab", name=re.compile(tab)).click()
    page.wait_for_function("(t) => location.hash.includes(t)", arg={"Needs review": "needs-review", "All trials": "all-trials", "Summary": "summary"}[tab])
    sidebar_link(page, "Quiet").click()
    page.wait_for_url(re.compile(r"#/watchlists/2/"))
    page.get_by_role("heading", name="All caught up").wait_for()
    for held, pattern in ((held_side, "**/api/watchlists"), (held_tab, tab_answer(tab))):
        if held:
            release(page, held, pattern)
    walk.shot(f"after-late-{tab.lower().replace(' ', '-')}-{'sidebar' if side else 'tab'}")
    assert "#/watchlists/2/" in page.url, (tab, page.url)
    hrefs = page.get_by_role("tablist", name="Watchlist views").get_by_role("tab").evaluate_all("(a) => a.map((x) => x.getAttribute('href'))")
    assert hrefs and all("/watchlists/2/" in h for h in hrefs), (tab, hrefs)
    assert page.get_by_role("heading", name="All caught up").count() == 1, tab
    assert sidebar_link(page, "Quiet").get_attribute("aria-current") == "page", tab


def marked(page):
    return page.get_by_label("Watchlists").locator('a[aria-current="page"]')


def test_walk_rename_from_the_header_menu_keeps_the_open_watchlist_marked_in_the_sidebar(make_app, make_walk):
    """test_walk_rename_from_the_header_menu_keeps_the_open_watchlist_marked_in_the_sidebar"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    assert marked(page).count() == 1
    page.get_by_role("button", name="Watchlist actions").click()
    page.get_by_role("menuitem", name="Rename watchlist").click()
    dialog = page.get_by_role("dialog", name="Rename watchlist")
    dialog.get_by_label("Watchlist name").fill("Lung, renamed")
    dialog.get_by_role("button", name="Save name").click()
    dialog.wait_for(state="detached")
    page.get_by_role("heading", level=1, name="Lung, renamed").wait_for()
    sidebar_link(page, "Lung, renamed").wait_for()
    walk.shot("renamed")
    assert marked(page).count() == 1 and "Lung, renamed" in marked(page).inner_text()
    assert "active" in (sidebar_link(page, "Lung, renamed").get_attribute("class") or "")


def test_walk_new_watchlist_keeps_the_open_watchlist_marked_in_the_sidebar(make_app, make_walk):
    """test_walk_new_watchlist_keeps_the_open_watchlist_marked_in_the_sidebar"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="+ New watchlist").click()
    dialog = page.get_by_role("dialog", name="New watchlist")
    dialog.get_by_label("Name").fill("Kidney")
    dialog.get_by_role("button", name="Create watchlist").click()
    dialog.wait_for(state="detached")
    sidebar_link(page, "Kidney").wait_for()
    walk.shot("created")
    assert marked(page).count() == 1 and helper.LONG_NAME[:20] in marked(page).inner_text()
    assert "active" in (sidebar_link(page, helper.LONG_NAME[:20]).get_attribute("class") or "")


def test_walk_removing_a_trial_and_its_undo_leave_the_sidebar_marking_where_the_address_points(make_app, make_walk):
    """test_walk_removing_a_trial_and_its_undo_leave_the_sidebar_marking_where_the_address_points"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    page.get_by_role("link", name="Review changes").first.click()
    page.get_by_role("button", name="More actions").click()
    held = hold_first(page, "**/api/watchlists")  # the sidebar answer to the removal is held
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.get_by_role("button", name="Undo").wait_for()
    assert held, "the removal did not ask for the sidebar"
    assert marked(page).count() == 0  # a trial page names no watchlist, so the sidebar marks none
    page.get_by_role("button", name="Undo").click()
    page.get_by_role("button", name="Undo").wait_for(state="detached")
    page.get_by_role("link", name=re.compile("^‹ Back to")).click()
    page.get_by_role("tab", name=re.compile("Needs review")).wait_for()
    assert marked(page).count() == 1
    release(page, held, "**/api/watchlists")  # the removal's sidebar answer lands on the watchlist page
    walk.shot("back-after-undo")
    assert marked(page).count() == 1 and helper.LONG_NAME[:20] in marked(page).inner_text()
