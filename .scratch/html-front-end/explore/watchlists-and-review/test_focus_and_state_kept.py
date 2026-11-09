"""Explore: redraws that drop the keyboard's place or the analyst's typing.

Data: helper.seed_queue (three trials in a long-named list, one in "Quiet"). Lacks: a
list with more than a few trials.
Run: .venv/bin/python -m pytest -p walks.conftest <this file> -q
"""

from walks import helper


def focused(page):
    return page.evaluate("document.activeElement === document.body ? 'body' : (document.activeElement.getAttribute('aria-label') || document.activeElement.textContent.trim().slice(0, 30))")


def test_walk_focus_is_not_lost_after_remove_from_this_list_and_its_undo(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/trials/NCT00000002")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    page.get_by_role("button", name="More actions").focus()
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")  # Remove from this list
    undo = page.get_by_role("button", name="Undo")
    undo.wait_for()
    walk.shot("after-remove")
    assert focused(page) != "body", "focus fell to the page after Remove from this list"
    undo.focus()
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Undo").wait_for(state="hidden")
    walk.shot("after-undo")
    assert focused(page) != "body", "focus fell to the page after Undo of a removal"


def test_walk_focus_is_not_lost_when_a_check_finishes(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1).wait_for()
    app.registry.set("slow", True, delay=1)
    page.get_by_role("button", name="Check for updates").focus()
    page.keyboard.press("Enter")
    page.get_by_text("Check complete").wait_for()
    walk.shot("after-check")
    assert focused(page) != "body", "focus fell to the page when the check finished"


def test_walk_a_typed_filter_and_sort_survive_a_check_finishing(make_app, make_walk):
    """Spec story 8: what I am reading does not move."""
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/watchlists/1/all-trials")
    page.locator("table.trials").wait_for()
    page.get_by_label("Filter by title, NCT ID or sponsor").fill("NCT00000002")
    page.get_by_label("Sort").select_option("status")
    app.registry.set("slow", True, delay=1)
    page.get_by_role("button", name="Check for updates").click()
    page.get_by_text("Check complete").wait_for()
    walk.shot("after-check")
    assert page.get_by_label("Filter by title, NCT ID or sponsor").input_value() == "NCT00000002"
    assert page.get_by_label("Sort").input_value() == "status"
    assert page.locator("#trial-count").inner_text() == "1 of 3 trials"
