"""Walk: a trial's address keeps the watchlist and tab it was opened from (trial-address-and-port, ticket 02).

Data: walks/test_trial_page_walk.py's seed ("Myeloma", id 1, holds NCT03412565, NCT00000002
and fourteen fillers; "Elsewhere", id 2, also holds NCT03412565), plus NCT10000001 added to
Elsewhere, so the two watchlists' Needs review queues differ after NCT03412565: Myeloma's
goes on to NCT00000002, Elsewhere's to NCT10000001. Summary links use walks/test_summary_walk.py's
seed. Ticket 03's walks (a stale or deleted watchlist in the address, a trial in no
watchlist) are at the end.
"""

from __future__ import annotations

import re

from walks import test_summary_walk as summary_seed
from walks.test_trial_page_walk import seed_trial_page

MYELOMA, ELSEWHERE = 1, 2


def seed_two_queues(db, registry):
    import monitor
    import storage

    seed_trial_page(db, registry)
    conn = storage.connect(db)
    monitor.add(conn, "NCT10000001", ELSEWHERE, when="2026-11-01T08:00:00+00:00")
    conn.close()


def open_from_elsewhere(make_app, make_walk, tab="needs-review"):
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/watchlists/{ELSEWHERE}/{tab}")
    if tab == "all-trials":
        page.locator('tr[data-nct="NCT03412565"] a').click()
        page.get_by_role("tab", name="Trial details").wait_for()
    else:
        page.locator('li.card[data-nct="NCT03412565"] h3 a').click()
        page.get_by_role("button", name="Mark reviewed").wait_for()
    return app, walk


def test_walk_a_trial_opened_from_its_second_watchlist_keeps_back_and_next_trial_after_a_reload(make_app, make_walk):
    """test_walk_a_trial_opened_from_its_second_watchlist_keeps_back_and_next_trial_after_a_reload"""
    _, walk = open_from_elsewhere(make_app, make_walk)
    page = walk.page
    page.get_by_role("link", name="‹ Back to Elsewhere").wait_for()
    walk.shot("opened-from-elsewhere")
    page.reload()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere"
    walk.shot("after-reload")
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_url(re.compile(rf"#/trials/NCT10000001\?list={ELSEWHERE}$"))
    page.get_by_role("link", name="‹ Back to Elsewhere").wait_for()
    walk.shot("next-trial-in-elsewhere")


def test_walk_a_saved_trial_address_naming_a_watchlist_and_all_trials_goes_back_to_that_tab(make_app, make_walk):
    """test_walk_a_saved_trial_address_naming_a_watchlist_and_all_trials_goes_back_to_that_tab"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT03412565/details?list={ELSEWHERE}&from=all-trials")
    back = page.get_by_role("link", name="‹ Back to Elsewhere")
    back.wait_for()
    walk.shot("saved-address")
    back.click()
    page.get_by_role("table").wait_for()
    assert page.evaluate("location.hash") == f"#/watchlists/{ELSEWHERE}/all-trials"
    assert page.get_by_role("tab", name="All trials").get_attribute("aria-selected") == "true"
    walk.shot("back-on-all-trials")


def test_walk_needs_review_and_all_trials_open_trial_addresses_naming_the_watchlist(make_app, make_walk):
    """test_walk_needs_review_and_all_trials_open_trial_addresses_naming_the_watchlist"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/watchlists/{ELSEWHERE}/needs-review")
    card = page.locator('li.card[data-nct="NCT03412565"]')
    card.wait_for()
    expected = f"#/trials/NCT03412565?list={ELSEWHERE}"
    assert card.locator("h3 a").get_attribute("href") == expected
    assert card.get_by_role("link", name="Review changes").get_attribute("href") == expected
    walk.shot("needs-review-links")
    page.get_by_role("tab", name="All trials").click()
    row = page.locator('tr[data-nct="NCT03412565"] a')
    row.wait_for()
    assert row.get_attribute("href") == f"#/trials/NCT03412565/details?list={ELSEWHERE}&from=all-trials"
    row.click()
    page.wait_for_url(re.compile(rf"#/trials/NCT03412565/details\?list={ELSEWHERE}&from=all-trials$"))
    page.get_by_role("link", name="‹ Back to Elsewhere").wait_for()
    walk.shot("opened-from-all-trials")


def test_walk_summary_trial_headings_open_trial_addresses_naming_the_watchlist_and_summary(make_app, make_walk):
    """test_walk_summary_trial_headings_open_trial_addresses_naming_the_watchlist_and_summary"""
    _, walk = summary_seed.open_summary(make_app, make_walk)
    page = walk.page
    link = page.locator('li.card.trial[data-nct="NCT03412565"] h3 a')
    link.wait_for()
    assert link.get_attribute("href") == "#/trials/NCT03412565?list=1&from=summary"
    link.click()
    page.get_by_role("link", name="‹ Back to Myeloma").click()
    page.locator("#summary-heading").wait_for()
    assert page.get_by_role("tab", name="Summary").get_attribute("aria-selected") == "true"
    walk.shot("back-on-summary")


def test_walk_the_trial_tabs_and_next_trial_keep_the_watchlist_and_tab_in_the_address(make_app, make_walk):
    """test_walk_the_trial_tabs_and_next_trial_keep_the_watchlist_and_tab_in_the_address"""
    _, walk = open_from_elsewhere(make_app, make_walk, tab="all-trials")
    page = walk.page
    query = f"?list={ELSEWHERE}&from=all-trials"
    page.get_by_role("tab", name="History").click()
    page.get_by_role("heading", name="Trial history").wait_for()
    assert page.evaluate("location.hash") == f"#/trials/NCT03412565/history{query}"
    walk.shot("history-keeps-the-watchlist")
    page.get_by_role("tab", name="Trial details").click()
    page.wait_for_url(re.compile(rf"#/trials/NCT03412565/details\?list={ELSEWHERE}&from=all-trials$"))
    page.get_by_role("tab", name=re.compile("^Changes")).click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.evaluate("location.hash") == f"#/trials/NCT03412565{query}"
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_url(re.compile(rf"#/trials/NCT10000001\?list={ELSEWHERE}&from=all-trials$"))
    page.get_by_role("link", name="‹ Back to Elsewhere").click()
    page.get_by_role("table").wait_for()
    assert page.evaluate("location.hash") == f"#/watchlists/{ELSEWHERE}/all-trials"
    walk.shot("back-on-all-trials-after-next")


def test_walk_a_trial_address_with_no_watchlist_uses_the_first_watchlist_as_before(make_app, make_walk):
    """test_walk_a_trial_address_with_no_watchlist_uses_the_first_watchlist_as_before"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT03412565")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Myeloma"
    assert page.locator("a.back").get_attribute("href") == f"#/watchlists/{MYELOMA}/needs-review"
    assert page.get_by_role("tab", name="History").get_attribute("href") == "#/trials/NCT03412565/history"
    walk.shot("no-watchlist-in-address")
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_url(re.compile(r"#/trials/NCT00000002$"))
    page.get_by_role("link", name="‹ Back to Myeloma").wait_for()


# Ticket 03: an address naming a watchlist that does not hold the trial falls back quietly.
# Elsewhere (id 2) holds NCT03412565 and NCT10000001 but not NCT00000002, which only Myeloma holds.


def seed_elsewhere_deleted(db, registry):
    import monitor
    import storage

    seed_two_queues(db, registry)
    conn = storage.connect(db)
    monitor.delete_list(conn, ELSEWHERE)
    conn.close()


def seed_a_trial_in_no_watchlist(db, registry):
    import monitor
    import storage

    seed_two_queues(db, registry)
    conn = storage.connect(db)
    monitor.remove(conn, "NCT00000002", MYELOMA)
    conn.close()


def test_walk_an_address_naming_a_watchlist_that_does_not_hold_the_trial_falls_back_to_its_first(make_app, make_walk):
    """test_walk_an_address_naming_a_watchlist_that_does_not_hold_the_trial_falls_back_to_its_first"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT00000002/details?list={ELSEWHERE}&from=all-trials")
    back = page.get_by_role("link", name="‹ Back to Myeloma")
    back.wait_for()
    assert back.get_attribute("href") == f"#/watchlists/{MYELOMA}/needs-review"
    page.wait_for_url(re.compile(rf"#/trials/NCT00000002/details\?list={MYELOMA}$"))
    assert page.get_by_role("tab", name="History").get_attribute("href") == f"#/trials/NCT00000002/history?list={MYELOMA}"
    walk.shot("stale-watchlist-falls-back-to-myeloma")


def test_walk_the_rewritten_address_adds_no_step_to_the_browsers_back(make_app, make_walk):
    """test_walk_the_rewritten_address_adds_no_step_to_the_browsers_back"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/watchlists/{MYELOMA}/needs-review")
    page.locator('li.card[data-nct="NCT00000002"]').wait_for()
    page.evaluate(f"location.hash = '#/trials/NCT00000002?list={ELSEWHERE}&from=summary'")
    page.get_by_role("link", name="‹ Back to Myeloma").wait_for()
    page.wait_for_url(re.compile(rf"#/trials/NCT00000002\?list={MYELOMA}$"))
    walk.shot("rewritten-in-place")
    page.go_back()
    page.locator('li.card[data-nct="NCT00000002"]').wait_for()
    assert page.evaluate("location.hash") == f"#/watchlists/{MYELOMA}/needs-review"
    walk.shot("back-leaves-the-trial")


def test_walk_an_address_naming_a_deleted_watchlist_falls_back_to_the_trials_first(make_app, make_walk):
    """test_walk_an_address_naming_a_deleted_watchlist_falls_back_to_the_trials_first"""
    app = make_app(seed=seed_elsewhere_deleted)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT03412565?list={ELSEWHERE}&from=all-trials")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Myeloma"
    page.wait_for_url(re.compile(rf"#/trials/NCT03412565\?list={MYELOMA}$"))
    walk.shot("deleted-watchlist-falls-back-to-myeloma")
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_url(re.compile(rf"#/trials/NCT00000002\?list={MYELOMA}$"))
    page.get_by_role("link", name="‹ Back to Myeloma").wait_for()


def test_walk_a_trial_in_no_watchlist_still_goes_back_to_watchlists(make_app, make_walk):
    """test_walk_a_trial_in_no_watchlist_still_goes_back_to_watchlists"""
    app = make_app(seed=seed_a_trial_in_no_watchlist)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/trials/NCT00000002/history?list={MYELOMA}")
    back = page.get_by_role("link", name="‹ Back to watchlists")
    back.wait_for()
    assert back.get_attribute("href") == "#/watchlists"
    page.wait_for_url(re.compile(r"#/trials/NCT00000002/history$"))
    walk.shot("no-watchlist-back-to-watchlists")


# Ticket 04: "Open the trial" on the registry details page carries the watchlist just added to.
# NCT00000002 is held only in Myeloma (id 1), so after adding it to Elsewhere (id 2) Myeloma is still its first.


def test_walk_open_the_trial_after_adding_from_registry_details_goes_back_to_that_watchlist(make_app, make_walk):
    """test_walk_open_the_trial_after_adding_from_registry_details_goes_back_to_that_watchlist"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/registry/NCT00000002")
    page.get_by_role("button", name="Add to watchlist").wait_for()
    page.get_by_label("Add to").select_option(label="Elsewhere")
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text("Added to Elsewhere.").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to results"
    assert page.locator("a.back").get_attribute("href") == "#/find"
    walk.shot("added-to-elsewhere")
    page.get_by_role("link", name="Open the trial").click()
    page.wait_for_url(re.compile(rf"#/trials/NCT00000002\?list={ELSEWHERE}$"))
    back = page.get_by_role("link", name="‹ Back to Elsewhere")
    back.wait_for()
    assert back.get_attribute("href") == f"#/watchlists/{ELSEWHERE}/needs-review"
    walk.shot("opened-with-elsewhere")


# Fixes after the build's review: Remove from this list keeps the watchlist across the trial's own tabs;
# "Back to" Summary keeps the period within one page load.


def test_walk_switching_the_trial_tab_after_removing_it_from_the_list_keeps_that_list(make_app, make_walk):
    """test_walk_switching_the_trial_tab_after_removing_it_from_the_list_keeps_that_list"""
    _, walk = open_from_elsewhere(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="More actions").click()
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.get_by_text("Removed from Elsewhere.").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere"
    walk.shot("removed-from-elsewhere")
    for tab, ready in (("History", "Trial history"), ("Trial details", None)):
        page.get_by_role("tab", name=tab).click()
        if ready:
            page.get_by_role("heading", name=ready).wait_for()
        else:
            page.wait_for_url(re.compile(rf"#/trials/NCT03412565/details\?list={ELSEWHERE}$"))
        assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere"
        assert page.evaluate("location.hash").endswith(f"?list={ELSEWHERE}")
        assert page.get_by_role("button", name="Undo").is_visible()
    walk.shot("details-keeps-elsewhere")
    page.get_by_role("tab", name=re.compile("^Changes")).click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.locator("a.back").inner_text() == "‹ Back to Elsewhere"
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_url(re.compile(rf"#/trials/NCT10000001\?list={ELSEWHERE}$"))
    page.get_by_role("link", name="‹ Back to Elsewhere").wait_for()
    walk.shot("next-trial-in-elsewhere")


def test_walk_back_to_summary_keeps_the_period_chosen_within_the_visit(make_app, make_walk):
    """test_walk_back_to_summary_keeps_the_period_chosen_within_the_visit"""
    _, walk = summary_seed.open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="This month").click()
    page.wait_for_url("**/summary?period=month")
    page.locator('li.card.trial[data-nct="NCT03412565"] h3 a').click()
    page.get_by_role("tab", name="History").click()
    page.get_by_role("heading", name="Trial history").wait_for()
    walk.shot("trial-from-summary-this-month")
    page.get_by_role("link", name="‹ Back to Myeloma").click()
    page.locator("#summary-heading").wait_for()
    assert page.evaluate("location.hash") == "#/watchlists/1/summary?period=month"
    assert page.locator('[aria-label="Period"] [aria-pressed="true"]').inner_text() == "This month"
    walk.shot("back-on-summary-this-month")


def test_walk_an_address_whose_list_is_not_a_watchlist_number_is_rewritten_to_the_one_shown(make_app, make_walk):
    """test_walk_an_address_whose_list_is_not_a_watchlist_number_is_rewritten_to_the_one_shown"""
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    for bad in ("abc", "0", ""):
        page.goto(f"{app.url}#/trials/NCT03412565?list={bad}")
        page.get_by_role("button", name="Mark reviewed").wait_for()
        assert page.locator("a.back").inner_text() == "‹ Back to Myeloma"
        page.wait_for_url(re.compile(rf"#/trials/NCT03412565\?list={MYELOMA}$"))
    walk.shot("bad-list-rewritten")
