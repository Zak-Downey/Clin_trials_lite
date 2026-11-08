"""Walk: Find trials, selecting results and adding them (ticket 08).

Data: two watchlists, "Myeloma" (holding NCT10000002 already) and "Elsewhere" (empty);
the stand-in's "many" search (134 copies of the captured study, so every title is the
same long one). Lacks: distinct titles, a registry failure while adding, a third list,
the All trials tab (ticket 06).
"""

from __future__ import annotations

import re

from walks import helper

STAMP = "2026-11-01T08:00:00+00:00"


def seed(db: str, registry: helper.Registry) -> None:
    import monitor
    import storage

    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.rename_list(conn, first, "Myeloma")
    monitor.create_list(conn, "Elsewhere", when=STAMP)
    monitor.add(conn, "NCT10000002", first, fetch=registry.fetch, when=STAMP)
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


def box(page, nct):
    return page.locator(f'li.card[data-nct="{nct}"] input[type=checkbox]')


def test_walk_each_result_has_a_real_checkbox_and_a_separate_title_link_and_long_titles_wrap(make_app, make_walk):
    """test_walk_each_result_has_a_real_checkbox_and_a_separate_title_link_and_long_titles_wrap"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    first = page.locator("li.card").first
    assert first.get_by_role("checkbox").count() == 1 and first.get_by_role("link", name=re.compile("^View details")).count() == 1
    results_hash = page.evaluate("location.hash")
    box(page, "NCT10000001").check()
    assert page.evaluate("location.hash") == results_hash  # ticking never opens
    page.get_by_text("1 trial selected").wait_for()
    first.get_by_role("link", name=re.compile("^View details")).click()
    page.get_by_role("button", name="Add to watchlist").wait_for()  # the details view, unique to it
    page.go_back()
    page.get_by_role("heading", name="134 matches").wait_for()
    page.get_by_text("1 trial selected").wait_for()  # the link did not change what was selected
    assert box(page, "NCT10000001").is_checked() and not box(page, "NCT10000003").is_checked()
    title = page.locator("li.card").first.locator("strong")
    line = page.evaluate("(e) => parseFloat(getComputedStyle(e).lineHeight) || 20", title.element_handle())
    assert title.bounding_box()["height"] > line * 1.5  # wraps over several lines
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    walk.shot("rows")


def test_walk_select_ten_on_this_page_selects_only_the_page_and_selections_survive_paging_details_and_leaving(make_app, make_walk):
    """test_walk_select_ten_on_this_page_selects_only_the_page_and_selections_survive_paging_details_and_leaving"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    page.get_by_label("Select 10 on this page").check()
    page.get_by_text("10 trials selected").wait_for()
    assert page.locator("li.card input:checked").count() == 10
    page.get_by_role("button", name="Next").click()
    page.get_by_text("11–20 of 134 matches").wait_for()
    assert page.locator("li.card input:checked").count() == 0  # only the first page
    box(page, "NCT10000011").check()
    page.get_by_text("11 trials selected").wait_for()
    page.get_by_role("button", name="Previous").click()
    page.get_by_text("1–10 of 134 matches").wait_for()
    assert page.locator("li.card input:checked").count() == 10
    page.locator("li.card").first.get_by_role("link", name=re.compile("^View details")).click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    page.go_back()
    page.get_by_role("heading", name="134 matches").wait_for()
    page.get_by_text("11 trials selected").wait_for()
    page.get_by_role("link", name="Watchlists", exact=True).first.click()
    page.get_by_role("button", name="Check for updates").wait_for()
    page.get_by_role("link", name="Find trials").click()
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    page.get_by_text("11 trials selected").wait_for()
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    assert page.locator("li.card input:checked").count() == 10
    walk.shot("kept")


def test_walk_the_action_bar_names_count_clear_and_destination_and_leaves_the_last_result_reachable(make_app, make_walk):
    """test_walk_the_action_bar_names_count_clear_and_destination_and_leaves_the_last_result_reachable"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    bar = page.get_by_role("region", name="Add selected trials")
    assert not bar.is_visible() or bar.inner_text().strip() == ""
    box(page, "NCT10000001").check()
    box(page, "NCT10000003").check()
    bar.get_by_text("2 trials selected").wait_for()
    assert bar.get_by_role("button", name="Clear").is_visible()
    assert bar.get_by_label("Add to").is_visible()
    assert bar.get_by_role("button", name="Add 2 trials").is_visible()
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    last = page.locator("li.card").last.bounding_box()
    assert last["y"] + last["height"] <= bar.bounding_box()["y"] + 1  # not covered
    walk.shot("bar")
    bar.get_by_role("button", name="Clear").click()
    assert page.locator("li.card input:checked").count() == 0
    assert bar.get_by_text("selected").count() == 0


def test_walk_opened_from_add_trials_the_destination_is_that_watchlist(make_app, make_walk):
    """test_walk_opened_from_add_trials_the_destination_is_that_watchlist"""
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Elsewhere")).click()
    page.get_by_role("link", name="Add trials").click()
    page.get_by_role("heading", level=1, name="Find trials").wait_for()
    page.get_by_label("Condition").fill("many")
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("heading", name="134 matches").wait_for()
    box(page, "NCT10000001").check()
    picker = page.get_by_label("Add to")
    picker.wait_for()
    assert picker.locator("option:checked").inner_text() == "Elsewhere"
    page.get_by_role("button", name="Add 1 trial").wait_for()
    walk.shot("destination")


def add_three(page):
    for nct in ("NCT10000001", "NCT10000002", "NCT10000003"):
        box(page, nct).check()
    page.get_by_role("button", name="Add 3 trials").wait_for()


def test_walk_adding_reports_added_and_already_in_this_list_links_the_watchlist_and_clears_the_selection(make_app, make_walk):
    """test_walk_adding_reports_added_and_already_in_this_list_links_the_watchlist_and_clears_the_selection"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    add_three(page)
    page.get_by_label("Add to").select_option(label="Myeloma")
    page.get_by_role("button", name="Add 3 trials").click()
    page.get_by_text("2 added; 1 already in this list").wait_for()
    assert page.get_by_role("link", name="Open Myeloma").is_visible()
    assert page.locator("li.card input:checked").count() == 0
    assert page.get_by_text("selected").count() == 0
    walk.shot("added")
    page.get_by_role("link", name="Open Myeloma").click()
    page.get_by_role("button", name="Check for updates").wait_for()


def test_walk_a_newly_added_trial_is_monitored_with_no_changes_and_does_not_enter_needs_review(make_app, make_walk):
    """test_walk_a_newly_added_trial_is_monitored_with_no_changes_and_does_not_enter_needs_review"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    box(page, "NCT10000001").check()
    page.get_by_label("Add to").select_option(label="Myeloma")
    page.get_by_role("button", name="Add 1 trial").click()
    page.get_by_text("1 added").wait_for()
    side = page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Myeloma"))
    side.get_by_text("2 trials").wait_for()
    assert side.locator(".badge").get_attribute("title") == "0 to review"
    page.get_by_role("link", name="Open Myeloma").click()
    page.get_by_role("button", name="Check for updates").wait_for()
    assert page.locator('li.card[data-nct="NCT10000001"]').count() == 0  # not in Needs review
    page.goto(page.url.split("#")[0] + "#/trials/NCT10000001")
    page.get_by_text("No unreviewed changes").wait_for()
    page.get_by_role("tab", name="History").click()
    page.get_by_text("Monitoring started").wait_for()
    assert page.get_by_text("Detected").count() == 0


def test_walk_view_details_of_a_trial_not_monitored_shows_sections_without_changes_or_history_and_stores_nothing_until_added(make_app, make_walk):
    """test_walk_view_details_of_a_trial_not_monitored_shows_sections_without_changes_or_history_and_stores_nothing_until_added"""
    _, walk = results(make_app, make_walk)
    page = walk.page
    page.locator('li.card[data-nct="NCT10000005"]').get_by_role("link", name=re.compile("^View details")).click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    assert page.get_by_role("heading", name="At a glance").is_visible()
    assert page.get_by_role("button", name=re.compile("Summary|Eligibility|Design|Sponsor", re.I)).count() > 0
    assert page.get_by_role("tab").count() == 0  # no Changes or History tabs
    assert page.get_by_text("Not monitored").first.is_visible()
    walk.shot("details")
    assert page.request.get(page.url.split("#")[0] + "api/trials/NCT10000005").status == 404
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text(re.compile("^Added to ")).wait_for()
    assert page.request.get(page.url.split("#")[0] + "api/trials/NCT10000005").status == 200
