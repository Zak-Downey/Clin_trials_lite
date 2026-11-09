"""Explore (find trials): a slow registry answer lands on a page the analyst has left.

Run: .venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/find-trials/test_stale_response_overwrites_view.py -q
Data: the stand-in's "many" (134 studies) and "nothing" (none) conditions, with its slow switch.
"""
from walks import helper


def open_find(make_app, make_walk, seed=None):
    app = make_app(seed)
    walk = make_walk(app)
    walk.page.goto(app.url + "#/find")
    walk.page.get_by_role("heading", level=1, name="Find trials").wait_for()
    return app, walk


def test_explore_a_slow_search_does_not_draw_over_the_watchlist_the_analyst_went_to(make_app, make_walk, registry):
    app, walk = open_find(make_app, make_walk, helper.seed_queue)
    page = walk.page
    registry.set("slow", True, delay=3)
    page.get_by_label("Condition").fill("lung")
    page.get_by_label("Condition").press("Enter")
    page.get_by_text("Searching").wait_for()
    registry.set("slow", False)
    page.get_by_role("link", name="Watchlists").first.click()
    page.wait_for_url("**#/watchlists/**")
    page.get_by_role("tab", name="Needs review").wait_for()
    page.wait_for_timeout(4000)  # the slow answer has arrived by now
    walk.shot("after-slow-answer")
    assert page.get_by_role("heading", level=1, name="Find trials").count() == 0, \
        f"address {page.url} but the page shows the Find trials results"
    assert page.get_by_role("tab", name="Needs review").count() == 1


def test_explore_an_older_slow_search_does_not_replace_the_newer_one(make_app, make_walk, registry):
    app, walk = open_find(make_app, make_walk)
    page = walk.page
    registry.set("slow", True, delay=3)
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_text("Searching").wait_for()
    registry.set("slow", False)
    page.get_by_label("Condition").count()  # the form is gone while searching: a user edits the address or goes Back/forward
    page.go_back()
    page.get_by_label("Condition").wait_for()
    page.get_by_label("Condition").fill("nothing")
    page.get_by_label("Condition").press("Enter")
    page.get_by_text("No trials match this search.").wait_for()
    page.wait_for_timeout(4000)
    walk.shot("after-old-answer")
    assert "nothing" in page.url
    assert page.get_by_text("No trials match this search.").count() == 1, "the older search's 134 matches replaced the newer search's empty answer"


def test_explore_a_slow_trial_detail_does_not_draw_over_the_page_left(make_app, make_walk, registry):
    app, walk = open_find(make_app, make_walk, helper.seed_queue)
    page = walk.page
    registry.set("slow", True, delay=3)
    page.goto(app.url + "#/registry/NCT10000005")
    page.get_by_role("link", name="Watchlists").first.click()
    page.wait_for_url("**#/watchlists/**")
    page.get_by_role("tab", name="Needs review").wait_for()
    registry.set("slow", False)
    page.wait_for_timeout(4000)
    walk.shot("after-slow-detail")
    assert page.get_by_role("link", name="Back to results").count() == 0, \
        f"address {page.url} but the page shows a registry trial"
