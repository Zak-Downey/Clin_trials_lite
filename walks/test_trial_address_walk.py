"""Walk: a trial's address keeps the watchlist and tab it was opened from (trial-address-and-port, ticket 02).

Data: walks/test_trial_page_walk.py's seed ("Myeloma", id 1, holds NCT03412565, NCT00000002
and fourteen fillers; "Elsewhere", id 2, also holds NCT03412565), plus NCT10000001 added to
Elsewhere, so the two watchlists' Needs review queues differ after NCT03412565: Myeloma's
goes on to NCT00000002, Elsewhere's to NCT10000001. Summary links use walks/test_summary_walk.py's
seed. Lacks: a trial in no watchlist, a stale watchlist in the address (ticket 03).
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
