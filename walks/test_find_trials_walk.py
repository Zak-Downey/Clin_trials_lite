"""Walk: Find trials, the Search tab (ticket 07).

Data: the stand-in registry's default three studies; condition "many" answers 134,
"nothing" answers none, and its server_error switch fails the search. Lacks: real
filtering (every other query answers the same three studies), selecting and adding
results (ticket 08).
"""

from __future__ import annotations

from walks import helper


def open_find(make_app, make_walk):
    app = make_app()
    walk = make_walk(app)
    walk.page.goto(app.url + "#/find")
    walk.page.get_by_role("heading", level=1, name="Find trials").wait_for()
    return app, walk


def search(page, cond):
    page.get_by_label("Condition").fill(cond)
    page.get_by_label("Condition").press("Enter")


def test_walk_the_form_opens_expanded_with_the_four_field_rule_above_the_four_fields(make_app, make_walk):
    """test_walk_the_form_opens_expanded_with_the_four_field_rule_above_the_four_fields"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    rule = page.get_by_text("Start with at least one of these four fields")
    assert rule.is_visible()
    rule_y = rule.bounding_box()["y"]
    for label in ("Condition", "Intervention", "Sponsor"):
        assert page.get_by_label(label, exact=True).bounding_box()["y"] > rule_y
    assert page.get_by_role("group", name="Phase").bounding_box()["y"] > rule_y
    walk.shot("form")


def test_walk_submitting_with_none_of_the_four_shows_the_error_and_keeps_every_value(make_app, make_walk):
    """test_walk_submitting_with_none_of_the_four_shows_the_error_and_keeps_every_value"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="More filters").click()
    page.get_by_role("group", name="Lead sponsor type").get_by_label("Industry").check()
    page.get_by_label("Recruiting", exact=True).check()
    page.get_by_label("Study started from").fill("2020-01-01")
    page.get_by_role("button", name="Search trials").click()
    error = page.get_by_role("alert")
    assert "at least" in error.inner_text().lower() or "add a condition" in error.inner_text().lower()
    group = page.get_by_role("group", name="Start with at least one of these four fields")
    assert group.get_by_role("alert").count() == 1  # beside the group, inside it
    assert page.get_by_role("group", name="Lead sponsor type").get_by_label("Industry").is_checked()
    assert page.get_by_label("Recruiting", exact=True).is_checked()
    assert page.get_by_label("Study started from").input_value() == "2020-01-01"
    walk.shot("error")


def test_walk_phase_is_labelled_toggle_buttons_that_differ_by_more_than_colour_and_clear_all_clears(make_app, make_walk):
    """test_walk_phase_is_labelled_toggle_buttons_that_differ_by_more_than_colour_and_clear_all_clears"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    phase3, phase2 = page.get_by_role("button", name="Phase 3", exact=True), page.get_by_role("button", name="Phase 2", exact=True)
    phase3.click()
    phase2.click()
    assert phase3.get_attribute("aria-pressed") == "true" and phase2.get_attribute("aria-pressed") == "true"
    assert page.get_by_role("button", name="Phase 1", exact=True).get_attribute("aria-pressed") == "false"
    mark = page.evaluate("(el) => getComputedStyle(el, '::before').content", phase3.element_handle())
    assert "✓" in mark  # a tick, not only a colour
    page.get_by_label("Condition").fill("kept until cleared")
    page.get_by_role("button", name="Clear all").click()
    assert phase3.get_attribute("aria-pressed") == "false" and phase2.get_attribute("aria-pressed") == "false"
    assert page.get_by_label("Condition").input_value() == ""
    walk.shot("phases")


def test_walk_more_filters_starts_folded_and_opens_with_its_help_visible(make_app, make_walk):
    """test_walk_more_filters_starts_folded_and_opens_with_its_help_visible"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    sponsor_help = page.get_by_text("Sponsor type uses the lead sponsor, not collaborators")
    date_help = page.get_by_text("Date filters exclude trials without a reported start date")
    assert not sponsor_help.is_visible() and not date_help.is_visible()
    toggle = page.get_by_role("button", name="More filters")
    assert toggle.get_attribute("aria-expanded") == "false"
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert sponsor_help.is_visible() and date_help.is_visible()
    assert page.get_by_role("group", name="Lead sponsor type").is_visible()
    assert page.get_by_label("Study started from").is_visible() and page.get_by_label("Study started to").is_visible()
    for text in ("Not yet recruiting", "Recruiting", "Enrolling by invitation", "Active, not recruiting", "Suspended",
                 "Terminated", "Completed", "Withdrawn", "Unknown"):
        assert page.get_by_label(text, exact=True).is_visible()
    assert page.get_by_label("Active, not recruiting", exact=True).bounding_box()["width"] > 0
    walk.shot("more-filters")


def test_walk_enter_in_any_field_submits_the_search(make_app, make_walk):
    """test_walk_enter_in_any_field_submits_the_search"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    page.get_by_label("Sponsor", exact=True).fill("Janssen")
    page.get_by_label("Sponsor", exact=True).press("Enter")
    page.get_by_role("heading", name="3 matches").wait_for()
    page.get_by_role("button", name="Edit search").click()
    page.get_by_label("Intervention").fill("daratumumab")
    page.get_by_label("Intervention").press("Enter")
    page.get_by_role("heading", name="3 matches").wait_for()
    assert "daratumumab" in page.locator("#query-summary").inner_text()


def test_walk_after_results_the_form_is_a_one_line_summary_and_edit_search_keeps_every_value(make_app, make_walk):
    """test_walk_after_results_the_form_is_a_one_line_summary_and_edit_search_keeps_every_value"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    page.get_by_label("Condition").fill("Multiple myeloma")
    page.get_by_label("Sponsor", exact=True).fill("Janssen")
    page.get_by_role("button", name="Phase 3", exact=True).click()
    page.get_by_role("button", name="More filters").click()
    page.get_by_role("group", name="Lead sponsor type").get_by_label("Industry").check()
    page.get_by_label("Recruiting", exact=True).check()
    page.get_by_label("Active, not recruiting", exact=True).check()
    page.get_by_role("button", name="Search trials").click()
    page.get_by_role("heading", name="3 matches").wait_for()
    assert page.get_by_label("Condition").count() == 0  # the form is gone
    summary = page.locator(".summary").inner_text()
    assert "Multiple myeloma · Janssen · Phase 3" in summary
    assert "Industry · Recruiting or Active, not recruiting" in summary
    walk.shot("summary")
    page.get_by_role("button", name="Edit search").click()
    assert page.get_by_label("Condition").input_value() == "Multiple myeloma"
    assert page.get_by_label("Sponsor", exact=True).input_value() == "Janssen"
    assert page.get_by_role("button", name="Phase 3", exact=True).get_attribute("aria-pressed") == "true"
    assert page.get_by_role("group", name="Lead sponsor type").get_by_label("Industry").is_checked()
    assert page.get_by_label("Recruiting", exact=True).is_checked()
    assert page.get_by_label("Active, not recruiting", exact=True).is_checked()


def test_walk_results_page_with_next_and_previous_and_the_cap_is_stated(make_app, make_walk):
    """test_walk_results_page_with_next_and_previous_and_the_cap_is_stated"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    search(page, "many")
    page.get_by_role("heading", name="134 matches").wait_for()
    assert page.locator("#range").inner_text() == "1–10 of 134 matches"
    assert page.get_by_text("Showing the first 100 of 134. Narrow your search to see the rest").is_visible()
    assert page.locator(".card").count() == 10
    assert page.get_by_role("button", name="Previous").is_disabled()
    # one page, no nested scrolling area
    nested = page.evaluate("""() => [...document.querySelectorAll('*')].filter((e) => {
      const s = getComputedStyle(e); return /(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 1 &&
      e !== document.documentElement && e !== document.body; }).length""")
    assert nested == 0
    walk.shot("page-1")
    page.get_by_role("button", name="Next").click()
    page.get_by_text("11–20 of 134 matches").wait_for()
    first_on_two = page.locator(".card").first.get_attribute("data-nct")
    assert first_on_two == "NCT10000011"
    page.get_by_role("button", name="Previous").click()
    page.get_by_text("1–10 of 134 matches").wait_for()
    for _ in range(9):
        page.get_by_role("button", name="Next").click()
        page.get_by_text("Page %d of 10" % (_ + 2)).wait_for()
    assert page.get_by_role("button", name="Next").is_disabled()
    assert page.locator("#range").inner_text() == "91–100 of 134 matches"
    walk.shot("page-10")


def test_walk_zero_matches_keep_the_summary_and_offer_edit_search_and_clear_optional_filters(make_app, make_walk):
    """test_walk_zero_matches_keep_the_summary_and_offer_edit_search_and_clear_optional_filters"""
    _, walk = open_find(make_app, make_walk)
    page = walk.page
    page.get_by_label("Condition").fill("nothing")
    page.get_by_role("button", name="More filters").click()
    page.get_by_label("Recruiting", exact=True).check()
    page.get_by_role("button", name="Search trials").click()
    page.get_by_text("No trials match this search").wait_for()
    assert "nothing" in page.locator("#query-summary").inner_text()
    assert page.get_by_text("Recruiting").first.is_visible()
    walk.shot("zero")
    page.get_by_role("button", name="Clear optional filters").click()
    page.wait_for_function("() => !document.querySelector('.summary').innerText.includes('Recruiting')")
    page.get_by_text("No trials match this search").wait_for()
    page.get_by_role("button", name="Edit search").first.click()
    assert page.get_by_label("Condition").input_value() == "nothing"


def test_walk_a_registry_error_keeps_the_form_and_retry_runs_the_search_again(make_app, make_walk):
    """test_walk_a_registry_error_keeps_the_form_and_retry_runs_the_search_again"""
    app, walk = open_find(make_app, make_walk)
    page = walk.page
    walk.expect(502, "/api/search")
    app.registry.set("server_error", True)
    page.get_by_label("Condition").fill("many")
    page.get_by_role("button", name="Search trials").click()
    retry = page.get_by_role("button", name="Retry")
    retry.wait_for()
    assert page.get_by_label("Condition").input_value() == "many"
    assert page.get_by_role("alert").is_visible()
    walk.shot("error")
    app.registry.set("server_error", False)
    retry.click()
    page.get_by_role("heading", name="134 matches").wait_for()


def test_walk_start_dates_the_wrong_way_round_show_the_swap_message_beside_the_dates_with_no_retry(make_app, make_walk):
    """test_walk_start_dates_the_wrong_way_round_show_the_swap_message_beside_the_dates_with_no_retry"""
    app, walk = open_find(make_app, make_walk)
    page = walk.page
    walk.expect(400, "/api/search")
    page.get_by_label("Condition").fill("many")
    page.get_by_role("button", name="More filters").click()
    page.get_by_label("Study started from").fill("2022-01-01")
    page.get_by_label("Study started to").fill("2020-01-01")
    page.get_by_role("button", name="Search trials").click()
    message = page.get_by_text("Swap the two dates.")
    message.wait_for()
    assert page.get_by_role("button", name="More filters").get_attribute("aria-expanded") == "true"
    assert page.get_by_label("Study started from").is_visible() and message.is_visible()
    dates = page.locator(".dates")
    assert dates.get_by_text("Swap the two dates.").count() == 1  # beside the date fields
    assert page.get_by_role("button", name="Retry").count() == 0
    assert page.get_by_label("Condition").input_value() == "many"
    assert page.get_by_label("Study started from").input_value() == "2022-01-01"
    walk.shot("bad-dates")


def test_walk_a_filtered_search_reaches_the_registry_with_its_phase_status_and_dates(make_app, make_walk):
    """test_walk_a_filtered_search_reaches_the_registry_with_its_phase_status_and_dates"""
    from urllib.parse import unquote

    app, walk = open_find(make_app, make_walk)
    page = walk.page
    page.get_by_label("Condition").fill("Multiple myeloma")
    page.get_by_role("button", name="Phase 3", exact=True).click()
    page.get_by_role("button", name="More filters").click()
    page.get_by_label("Recruiting", exact=True).check()
    page.get_by_label("Study started from").fill("2020-01-01")
    page.get_by_label("Study started to").fill("2022-12-31")
    page.get_by_role("button", name="Search trials").click()
    page.get_by_role("heading", name="3 matches").wait_for()
    asked = [unquote(path) for path in app.registry.server.state.requests if "/studies?" in path]
    last = asked[-1]
    assert "PHASE3" in last and "RECRUITING" in last and "AREA[StartDate]RANGE[2020-01-01,2022-12-31]" in last, last
    walk.shot("filtered")
