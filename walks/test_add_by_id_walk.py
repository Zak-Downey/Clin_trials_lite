"""Walk: New watchlist, dialogs, Add by NCT ID and the first-use screen (ticket 09).

Data: Find walks use ticket 08's seed ("Myeloma" holding NCT10000002, empty "Elsewhere")
and the stand-in's "many" search; the others start from a fresh database (one empty
default watchlist) and the stand-in's copies NCT00000002 and NCT00000003.
Lacks: a slow registry, a long watchlist name in the dialog, more than a handful of lists.
"""

from __future__ import annotations

import re

from walks import helper
from walks.test_find_select_walk import box, results, seed


def bar(page):
    return page.get_by_role("region", name="Add selected trials")


def dialog(page):
    return page.get_by_role("dialog", name="New watchlist")


def test_walk_new_watchlist_from_the_sidebar_and_the_picker_validates_inline_and_selects_the_new_destination(make_app, make_walk):
    """test_walk_new_watchlist_from_the_sidebar_and_the_picker_validates_inline_and_selects_the_new_destination"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    box(page, "NCT10000001").check()
    picker = bar(page).get_by_label("Add to")
    picker.select_option(label="+ New watchlist")
    dialog(page).wait_for()
    dialog(page).get_by_role("button", name="Create watchlist").click()
    assert dialog(page).get_by_text("Give the watchlist a name.").is_visible()
    dialog(page).get_by_label("Name").fill("myeloma")
    walk.expect(409, "/api/watchlists")
    dialog(page).get_by_role("button", name="Create watchlist").click()
    dialog(page).get_by_text("There is already a watchlist called").wait_for()
    assert dialog(page).get_by_label("Name").input_value() == "myeloma"  # kept
    walk.shot("refused")
    dialog(page).get_by_label("Name").fill("Lung")
    dialog(page).get_by_role("button", name="Create watchlist").click()
    dialog(page).wait_for(state="detached")
    assert page.locator("#add-to").evaluate("(s) => s.selectedOptions[0].textContent") == "Lung"
    assert page.get_by_role("link", name=re.compile("^Lung")).count() == 1  # in the sidebar
    assert page.locator("li.card input:checked").count() == 1  # the task is as it was
    page.get_by_role("button", name="+ New watchlist").click()
    dialog(page).get_by_label("Name").fill("Kidney")
    dialog(page).get_by_role("button", name="Create watchlist").click()
    dialog(page).wait_for(state="detached")
    page.wait_for_function("document.querySelector('#add-to').selectedOptions[0].textContent === 'Kidney'")
    walk.shot("created")


def test_walk_every_dialog_traps_focus_and_escape_cancels_and_returns_to_the_opener_in_place(make_app, make_walk):
    """test_walk_every_dialog_traps_focus_and_escape_cancels_and_returns_to_the_opener_in_place"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    box(page, "NCT10000001").check()
    # the sidebar's button, from the top of the page
    names = page.locator("#sidebar a").count()
    opener = page.get_by_role("button", name="+ New watchlist")
    opener.click()
    dialog(page).wait_for()
    assert page.evaluate("document.activeElement.id") == "new-watchlist-name"
    for _ in range(6):  # more tabs than the dialog has controls
        page.keyboard.press("Tab")
        assert page.evaluate("!!document.activeElement.closest('dialog')")
    page.keyboard.press("Shift+Tab")
    assert page.evaluate("!!document.activeElement.closest('dialog')")
    page.get_by_label("Name").fill("Never made")
    page.keyboard.press("Escape")
    dialog(page).wait_for(state="detached")
    page.wait_for_function("document.activeElement.id === 'new-watchlist'")
    assert page.locator("#sidebar a").count() == names  # nothing created
    # the picker's entry, further down the page
    page.evaluate("window.scrollTo(0, 400)")
    here = page.evaluate("[location.hash, window.scrollY]")
    assert here[1] > 0
    bar(page).get_by_label("Add to").select_option(label="+ New watchlist")
    dialog(page).wait_for()
    page.keyboard.press("Escape")
    dialog(page).wait_for(state="detached")
    page.wait_for_function("document.activeElement.id === 'add-to'")
    assert page.evaluate("[location.hash, window.scrollY]") == here
    bar(page).get_by_label("Add to").select_option(label="+ New watchlist")
    dialog(page).get_by_role("button", name="Cancel").click()
    dialog(page).wait_for(state="detached")
    assert page.locator("#add-to").evaluate("(s) => s.selectedOptions[0].textContent") != "+ New watchlist"
    assert page.evaluate("[location.hash, window.scrollY]") == here
    # saving leaves the view and place too
    bar(page).get_by_label("Add to").select_option(label="+ New watchlist")
    dialog(page).get_by_label("Name").fill("Saved")
    dialog(page).get_by_role("button", name="Create watchlist").click()
    dialog(page).wait_for(state="detached")
    assert page.evaluate("[location.hash, window.scrollY]") == here
    walk.shot("back")


def open_by_id(make_app, make_walk, seed=None):
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/find/1/id")
    page.get_by_role("button", name="Look up trial").wait_for()
    return app, walk


def test_walk_add_by_nct_id_names_its_destination_and_shows_the_trial_before_adding_it(make_app, make_walk):
    """test_walk_add_by_nct_id_names_its_destination_and_shows_the_trial_before_adding_it"""
    app, walk = open_by_id(make_app, make_walk, seed=seed)
    page = walk.page
    assert page.locator("#destination").evaluate("(s) => s.selectedOptions[0].textContent") == "Myeloma"
    page.get_by_label("NCT ID").fill("nct00000002")
    page.get_by_role("button", name="Look up trial").click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    found = page.locator(".found")
    for word in ("NCT00000002", "Sponsor:", "Status:"):
        assert word in found.inner_text()
    assert page.get_by_role("link", name=re.compile("^Myeloma")).inner_text().count("1 trial") == 1  # nothing added yet
    walk.shot("looked-up")
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text("Added NCT00000002 to Myeloma.").wait_for()
    assert "2 trials" in page.get_by_role("link", name=re.compile("^Myeloma")).inner_text()
    assert page.get_by_label("NCT ID").input_value() == ""


def test_walk_each_lookup_failure_shows_its_own_message_in_place_keeps_the_id_and_focuses_the_input(make_app, make_walk):
    """test_walk_each_lookup_failure_shows_its_own_message_in_place_keeps_the_id_and_focuses_the_input"""
    app, walk = open_by_id(make_app, make_walk)
    page = walk.page
    registry = app.registry
    path = "/api/watchlists/1/lookup"
    field, look = page.get_by_label("NCT ID"), page.get_by_role("button", name="Look up trial")

    def attempt(text, expect):
        if expect:
            walk.expect(expect, path)
        field.fill(text)
        look.click()
        page.locator("#nct-error").filter(has_text=re.compile(".")).wait_for()
        assert field.input_value() == text and page.evaluate("document.activeElement.id") == "nct-id"
        return page.locator("#nct-error").inner_text()

    invalid = attempt("NCT123", 400)
    assert "NCT followed by 8 digits" in invalid
    walk.shot("invalid")
    registry.set("not_found")
    missing = attempt("NCT00000002", 404)
    registry.set("not_found", False)
    assert "No trial with that ID was found" in missing
    page.get_by_role("link", name="Find trials").first.hover()  # keep the page honest
    field.fill("NCT00000002")
    look.click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text("Added NCT00000002").wait_for()
    again = attempt("NCT00000002", 409)
    assert "already in" in again
    registry.set("server_error")
    down = attempt("NCT00000003", 502)
    registry.set("server_error", False)
    assert "could not be reached" in down
    assert len({invalid, missing, again, down}) == 4
    walk.shot("unavailable")


def test_walk_an_empty_watchlist_shows_only_the_first_trial_screen_and_its_buttons_carry_the_destination(make_app, make_walk):
    """test_walk_an_empty_watchlist_shows_only_the_first_trial_screen_and_its_buttons_carry_the_destination"""
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/watchlists/2")
    page.get_by_role("heading", name="Monitor your first trial").wait_for()
    text = page.locator("#view").inner_text()
    assert "saves a starting point" in text and "You choose when to check for updates." in text
    assert page.get_by_role("button", name="Check for updates").count() == 0
    assert page.get_by_role("tab").count() == 0
    assert page.get_by_text("Last checked").count() == 0 and page.get_by_text("Not checked yet").count() == 0
    walk.shot("first-use")
    page.get_by_role("link", name="Add by NCT ID").click()
    page.get_by_role("button", name="Look up trial").wait_for()
    assert page.evaluate("location.hash") == "#/find/2/id"
    assert page.locator("#destination").evaluate("(s) => s.selectedOptions[0].textContent") == "Elsewhere"
    page.go_back()
    page.locator("#view").get_by_role("link", name="Find trials").click()
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    assert page.evaluate("location.hash") == "#/find/2"
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    box(page, "NCT10000001").check()
    assert page.locator("#add-to").evaluate("(s) => s.selectedOptions[0].textContent") == "Elsewhere"


def test_walk_the_first_trial_added_takes_its_baseline_and_is_not_in_needs_review(make_app, make_walk):
    """test_walk_the_first_trial_added_takes_its_baseline_and_is_not_in_needs_review"""
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("link", name="Add by NCT ID").click()
    page.get_by_label("NCT ID").fill("NCT00000002")
    page.get_by_role("button", name="Look up trial").click()
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_role("link", name=re.compile("^Open ")).click()
    page.get_by_role("button", name="Check for updates").wait_for()
    page.get_by_role("heading", name="0 trials need review").wait_for()
    page.get_by_role("tab", name="All trials").click()
    row = page.locator('tr[data-nct="NCT00000002"]')
    row.wait_for()
    assert "No changes" in row.inner_text()
    walk.shot("baseline")
