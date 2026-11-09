"""Walk: trial details and Add by NCT ID go where the analyst came from; a failed add is an error (ticket 05).

Data: ticket 08's seed ("Myeloma" holding NCT10000002, empty "Elsewhere") and the stand-in's
"many" search; ticket 11's seed ("Myeloma", "Quiet", "Bare") where Quiet's New matches offers
NCT00000002. Lacks: a trial already in the destination, a slow registry.
"""

from __future__ import annotations

import re

from walks import test_find_select_walk as find_seed
from walks import test_new_matches_walk as matches_seed


def search_from_elsewhere(page, app):
    page.goto(app.url)
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Elsewhere")).click()
    page.locator("#view").get_by_role("link", name="Find trials").click()
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()


def test_walk_view_details_from_find_trials_presets_add_to_the_find_destination_and_adds_there(make_app, make_walk):
    """test_walk_view_details_from_find_trials_presets_add_to_the_find_destination_and_adds_there"""
    app = make_app(seed=find_seed.seed)
    walk = make_walk(app)
    page = walk.page
    search_from_elsewhere(page, app)
    page.locator('li.card[data-nct="NCT10000001"]').get_by_role("link", name=re.compile("^View details")).click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    assert page.locator("#add-to").evaluate("(s) => s.selectedOptions[0].textContent") == "Elsewhere"
    walk.shot("details-from-find")
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text("Added to Elsewhere.").wait_for()
    assert "1 trial" in page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Elsewhere")).inner_text()


def test_walk_view_details_from_a_new_matches_card_presets_that_watchlist_and_back_returns_to_its_tab(make_app, make_walk):
    """test_walk_view_details_from_a_new_matches_card_presets_that_watchlist_and_back_returns_to_its_tab"""
    app, walk = matches_seed.open_tab(make_app, make_walk, watchlist="Quiet")
    page = walk.page
    tab = page.evaluate("location.hash")
    assert tab.endswith("/new-matches")
    page.locator('li.card[data-nct="NCT00000002"] h3 a').click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    assert page.locator("#add-to").evaluate("(s) => s.selectedOptions[0].textContent") == "Quiet"
    walk.shot("details-from-new-matches")
    page.locator("a.back").click()
    page.get_by_role("heading", level=2, name=re.compile("new match")).wait_for()
    assert page.evaluate("location.hash") == tab
    assert page.get_by_role("tab", name=re.compile("^New matches")).get_attribute("aria-selected") == "true"


def test_walk_a_registry_failure_on_add_by_nct_id_is_an_error_beside_the_field_and_keeps_and_focuses_the_id(make_app, make_walk):
    """test_walk_a_registry_failure_on_add_by_nct_id_is_an_error_beside_the_field_and_keeps_and_focuses_the_id"""
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/find/1/id")
    page.get_by_label("NCT ID").fill("NCT00000002")
    page.get_by_role("button", name="Look up trial").click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    app.registry.set("server_error")
    page.get_by_role("button", name="Add to watchlist").click()
    page.locator("#nct-error").filter(has_text=re.compile(".")).wait_for()
    app.registry.set("server_error", False)
    assert page.locator(".banner").count() == 0
    assert page.get_by_role("link", name=re.compile("^Open ")).count() == 0
    assert page.get_by_label("NCT ID").input_value() == "NCT00000002"
    assert page.evaluate("document.activeElement.id") == "nct-id"
    walk.shot("add-failed")


def test_walk_a_registry_failure_on_add_from_trial_details_is_an_error_with_no_link_to_a_trial_page(make_app, make_walk):
    """test_walk_a_registry_failure_on_add_from_trial_details_is_an_error_with_no_link_to_a_trial_page"""
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/registry/NCT00000002")
    page.get_by_role("button", name="Add to watchlist").wait_for()
    app.registry.set("server_error")
    page.get_by_role("button", name="Add to watchlist").click()
    page.locator("#add-error").filter(has_text=re.compile(".")).wait_for()
    app.registry.set("server_error", False)
    assert page.get_by_role("link", name="Open the trial").count() == 0
    assert page.locator('a[href^="#/trials/"]').count() == 0
    assert page.locator(".banner:visible").count() == 0
    walk.shot("details-add-failed")
