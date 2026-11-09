"""Walk: saving a search, replacing it, the banner and Manage (ticket 10).

Data: ticket 08's seed ("Myeloma" holding NCT10000002, empty "Elsewhere"), plus a
revision on NCT10000002 so Myeloma has one trial needing review, and a "Prior" watchlist
that already has a saved search; the stand-in's "many" search (134 copies).
Lacks: a saved search with every filter set, a registry failure while saving, more than a
handful of watchlists.
"""

from __future__ import annotations

import re

from walks.test_find_select_walk import STAMP, seed as find_seed


def seed(db, registry):
    import monitor
    import storage

    find_seed(db, registry)
    conn = storage.connect(db)
    mine = next(w["id"] for w in storage.list_lists(conn) if w["name"] == "Myeloma")
    storage.add_change(conn, "NCT10000002", {"field": "enrollment", "previous": 1, "current": 2}, STAMP)
    prior = monitor.create_list(conn, "Prior", when=STAMP)
    monitor.remember_search(conn, prior, monitor.as_query(cond="lymphoma", statuses=["RECRUITING"]))
    conn.close()


def results(make_app, make_walk, start="#/find"):
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + start)
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    return app, walk


def dialog(page, name="Watch this search"):
    return page.get_by_role("dialog", name=name)


def sidebar_count(page, name):
    return page.get_by_label("Watchlists").get_by_role("link", name=re.compile(f"^{name}")).locator(".counts").inner_text()


def test_walk_watch_this_search_saves_the_query_with_nothing_selected_to_an_empty_watchlist_and_adds_no_trials(make_app, make_walk):
    """test_walk_watch_this_search_saves_the_query_with_nothing_selected_to_an_empty_watchlist_and_adds_no_trials"""
    app, walk = results(make_app, make_walk, start="#/find")
    page = walk.page
    assert page.get_by_role("region", name="Add selected trials").is_hidden()  # nothing selected
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    watch.wait_for()
    assert "many" in watch.locator(".query-box").inner_text()  # the submitted query
    assert page.evaluate("document.activeElement.id") == "watch-destination"
    watch.get_by_label("Watchlist").select_option(label="Elsewhere")  # a watchlist with no trials
    watch.get_by_role("button", name="Watch this search").wait_for()
    assert watch.get_by_text("already has a saved search").count() == 0
    walk.shot("dialog")
    watch.get_by_role("button", name="Watch this search").click()
    watch.get_by_role("heading", name="Search saved").wait_for()
    text = watch.inner_text()
    assert "Elsewhere will check for new matches when you run Check for updates." in text
    walk.shot("saved")
    assert sidebar_count(page, "Elsewhere") == "0 trials"  # nothing was added
    assert sidebar_count(page, "Myeloma") == "1 trial"
    watch.get_by_role("link", name=re.compile("^Open watchlist")).click()
    page.get_by_role("heading", level=1, name="Elsewhere").wait_for()
    page.get_by_text("Saved search is on").wait_for()  # a watchlist with a saved search and no trials is not first-use
    assert page.get_by_role("heading", name="Monitor your first trial").count() == 0


def test_walk_a_watchlist_that_already_has_a_saved_search_shows_it_and_replace_is_deliberate(make_app, make_walk):
    """test_walk_a_watchlist_that_already_has_a_saved_search_shows_it_and_replace_is_deliberate"""
    app, walk = results(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    watch.get_by_label("Watchlist").select_option(label="Prior")
    watch.get_by_text("This watchlist already has a saved search.").wait_for()
    assert "lymphoma" in watch.locator(".replace-warning").inner_text()
    assert "Recruiting" in watch.locator(".replace-warning").inner_text()
    watch.get_by_role("button", name="Replace saved search").wait_for()
    assert watch.get_by_role("button", name="Watch this search").count() == 0
    walk.shot("replace")
    watch.get_by_role("button", name="Cancel").click()
    watch.wait_for(state="detached")
    prior = page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Prior"))
    prior.click()
    page.get_by_role("heading", level=1, name="Prior").wait_for()
    page.get_by_role("button", name="Manage").click()
    dialog(page, "Manage saved search").get_by_text("lymphoma").wait_for()  # Cancel left the old one
    dialog(page, "Manage saved search").get_by_role("button", name="Close").click()
    # and replacing is possible: pick it again and confirm
    page.goto(app.url + "#/find")
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    watch.get_by_label("Watchlist").select_option(label="Prior")
    watch.get_by_role("button", name="Replace saved search").click()
    watch.get_by_role("heading", name="Search saved").wait_for()
    watch.get_by_role("link", name=re.compile("^Open watchlist")).click()
    page.get_by_role("heading", level=1, name="Prior").wait_for()
    page.get_by_role("button", name="Manage").click()
    dialog(page, "Manage saved search").get_by_text("many").wait_for()
    assert "lymphoma" not in dialog(page, "Manage saved search").inner_text()


def test_walk_the_picker_can_create_a_watchlist_and_save_to_it(make_app, make_walk):
    """test_walk_the_picker_can_create_a_watchlist_and_save_to_it"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    watch.get_by_role("button", name="+ Create a new watchlist").click()
    dialog(page, "New watchlist").get_by_label("Name").fill("Brand new")
    dialog(page, "New watchlist").get_by_role("button", name="Create watchlist").click()
    dialog(page, "New watchlist").wait_for(state="detached")
    assert watch.get_by_label("Watchlist").evaluate("(s) => s.selectedOptions[0].textContent") == "Brand new"
    watch.get_by_role("button", name="Watch this search").click()
    watch.get_by_text("Brand new will check for new matches").wait_for()


def test_walk_a_saved_search_banner_sits_above_the_tabs_and_leaves_the_review_list_in_view(make_app, make_walk):
    """test_walk_a_saved_search_banner_sits_above_the_tabs_and_leaves_the_review_list_in_view"""
    app, walk = results(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    watch.get_by_label("Watchlist").select_option(label="Myeloma")
    watch.get_by_role("button", name="Watch this search").click()
    watch.get_by_role("link", name=re.compile("^Open watchlist")).click()
    banner = page.get_by_label("Saved search")
    banner.wait_for()
    text = banner.inner_text()
    for words in ("Saved search is on", "runs when you check for updates", "New matches need your approval", "Manage"):
        assert words in text
    tabs = page.get_by_role("tablist", name="Watchlist views")
    assert banner.bounding_box()["y"] + banner.bounding_box()["height"] <= tabs.bounding_box()["y"]
    card = page.locator("li.card[data-nct=NCT10000002]")
    card.wait_for()
    size = page.viewport_size
    box = card.bounding_box()
    assert box["y"] + box["height"] <= size["height"]  # the list is still on the first screen
    assert page.get_by_role("heading", name="Monitor your first trial").count() == 0
    walk.shot("banner")


def test_walk_manage_shows_the_query_edit_search_prefills_find_and_turn_off_keeps_every_trial(make_app, make_walk):
    """test_walk_manage_shows_the_query_edit_search_prefills_find_and_turn_off_keeps_every_trial"""
    app, walk = results(make_app, make_walk)
    page = walk.page
    page.goto(app.url + "#/watchlists/3/needs-review")  # Prior
    page.get_by_role("heading", level=1, name="Prior").wait_for()
    page.get_by_role("button", name="Manage").click()
    manage = dialog(page, "Manage saved search")
    assert "lymphoma" in manage.locator(".query-box").inner_text()
    assert manage.get_by_role("link", name="Edit search").count() == 1
    assert manage.get_by_role("button", name="Turn off").count() == 1
    walk.shot("manage")
    manage.get_by_role("link", name="Edit search").click()
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    page.get_by_text("matches").first.wait_for()
    assert "lymphoma" in page.locator("#query-summary").inner_text()  # Find trials, pre-filled
    page.get_by_role("button", name="Edit search").click()
    assert page.get_by_label("Condition").input_value() == "lymphoma"
    # nothing was replaced by looking: Prior still has its query
    page.goto(app.url + "#/watchlists/3/needs-review")
    page.get_by_role("button", name="Manage").click()
    assert "lymphoma" in dialog(page, "Manage saved search").locator(".query-box").inner_text()
    dialog(page, "Manage saved search").get_by_role("button", name="Close").click()
    # Turn off keeps every trial: use Myeloma, which holds one
    page.goto(app.url + "#/watchlists/1/needs-review")
    page.get_by_role("heading", level=1, name="Myeloma").wait_for()
    page.get_by_text("Saved search is on").count()  # may be absent: Myeloma has none yet
    assert page.get_by_label("Saved search").count() == 0
    # give Myeloma one through the dialog, then turn it off
    page.goto(app.url + "#/find")
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    page.get_by_role("button", name="Watch this search").click()
    dialog(page).get_by_label("Watchlist").select_option(label="Myeloma")
    dialog(page).get_by_role("button", name="Watch this search").click()
    dialog(page).get_by_role("link", name=re.compile("^Open watchlist")).click()
    page.get_by_text("Saved search is on").wait_for()
    page.get_by_role("button", name="Manage").click()
    dialog(page, "Manage saved search").get_by_role("button", name="Turn off").click()
    page.get_by_text("Saved search is on").wait_for(state="detached")
    assert page.locator("li.card[data-nct=NCT10000002]").count() == 1
    assert sidebar_count(page, "Myeloma") == "1 trial"
    walk.shot("off")


def test_walk_a_late_answer_for_an_earlier_watchlist_never_changes_the_dialog_for_the_one_now_chosen(make_app, make_walk):
    """test_walk_a_late_answer_for_an_earlier_watchlist_never_changes_the_dialog_for_the_one_now_chosen"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    held = []
    page.route(re.compile(r"/api/watchlists/3/saved-search$"), lambda route: held.append(route))
    page.get_by_role("button", name="Watch this search").click()
    watch = dialog(page)
    picker = watch.get_by_label("Watchlist")
    picker.select_option(label="Prior")  # its answer is held back
    page.wait_for_function("true")
    while not held:
        page.wait_for_timeout(50)
    picker.select_option(label="Myeloma")  # answered at once: no saved search
    watch.get_by_role("button", name="Watch this search").wait_for()
    held[0].continue_()  # now the earlier answer arrives
    page.wait_for_timeout(500)
    assert watch.get_by_text("already has a saved search").count() == 0
    assert watch.get_by_role("button", name="Replace saved search").count() == 0
