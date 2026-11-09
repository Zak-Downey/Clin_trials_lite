"""Explore: a check that finishes after the analyst left New matches resets where "View details" came from.

Data: walks/test_new_matches_walk.py's seed ("Myeloma" with a saved search, "Quiet" id 2, "Bare").
Lacks: more than one slow answer; the late answer here is held by Playwright route.
Run: .venv/bin/python -m pytest walks/test_explore_wr_check_refresh_clobbers_trial_origin.py -q
"""
import pytest


import re

from walks import test_new_matches_walk as nm


def test_walk_a_check_finishing_after_leaving_new_matches_does_not_change_where_find_trials_details_came_from(make_app, make_walk):
    app, walk = nm.open_tab(make_app, make_walk)
    page = walk.page
    held = []

    def handler(route):
        if route.request.method == "GET" and route.request.url.endswith("/api/watchlists") and armed and not held:
            held.append(route)
        else:
            route.continue_()

    armed = []
    page.route("**/api/watchlists", handler)
    armed.append(1)
    page.get_by_role("button", name="Check for updates").click()
    page.wait_for_function("true")  # let the click run
    deadline = 0
    while not held and deadline < 100:
        page.wait_for_timeout(100)
        deadline += 1
    assert held, "the check never asked for the sidebar after finishing"
    page.goto(app.url + "#/find/2")
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    with page.expect_response(re.compile(r"/api/watchlists$")):
        held[0].continue_()
    page.wait_for_timeout(500)  # the late refresh has now drawn or not
    page.locator("li.card").first.get_by_role("link", name=re.compile("^View details")).click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    walk.shot("details")
    assert page.locator("#add-to").evaluate("(s) => s.selectedOptions[0].textContent") == "Quiet", \
        "Add to is preset to the New matches watchlist, not the Find trials destination"
    assert page.locator("a.back").inner_text() == "‹ Back to results"
