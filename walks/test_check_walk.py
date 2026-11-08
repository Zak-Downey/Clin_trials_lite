"""Walk: the watchlist header and Check for updates (design pages 1, 12).

Data: helper.seed_queue plus a saved search and one finished check (16:45 UTC, 8 Nov 2026)
on the first watchlist; the registry serves the revised NCT03412565 only when a walk
switches `revise` on, so a check finds nothing unless the walk says otherwise. Lacks: a
saved search that finds something, a watchlist with no trials, and a check that is stopped.
"""

from __future__ import annotations

import re

from walks import helper


def seed_checked(db, registry):
    import monitor
    import storage

    helper.seed_queue(db, registry)
    conn = storage.connect(db)
    monitor.remember_search(conn, 1, monitor.as_query(cond="lung cancer"))
    storage.finish_check_run(conn, 1, [], "2026-11-08T16:45:00+00:00")
    conn.close()


def seed_baseline(db, registry):
    """Two trials added at the registry's original version; nothing to review, never checked."""
    import monitor
    import storage

    conn = storage.connect(db)
    for nct in ("NCT03412565", "NCT00000002"):
        monitor.add(conn, nct, 1, fetch=registry.fetch, when="2026-11-01T08:00:00+00:00")
    conn.close()


def open_app(make_app, make_walk, seed=seed_checked):
    app = make_app(seed=seed)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("heading", level=1).wait_for()
    return app, walk


def test_walk_the_header_names_the_watchlist_and_offers_only_a_manual_check(make_app, make_walk):
    """test_walk_the_header_names_the_watchlist_and_offers_only_a_manual_check"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    assert page.get_by_role("heading", level=1).inner_text() == helper.LONG_NAME
    meta = page.locator("#watchlist-meta").inner_text()
    assert meta == "3 trials monitored · Last checked Nov 8, 2026, 11:45 AM EST", meta
    buttons = page.get_by_role("main").get_by_role("button")
    assert [buttons.nth(i).inner_text() for i in range(buttons.count())] == ["Check for updates"]
    add = page.get_by_role("link", name="Add trials")
    assert add.get_attribute("href") == "#/find/1"
    text = page.get_by_role("main").inner_text().lower()
    for word in ("scheduled", "automatic", "real-time", "real time", "continuous", "daily", "hourly", "live"):
        assert word not in text, word
    page.get_by_label("Watchlists").get_by_role("link", name="Quiet").click()
    page.get_by_text("1 trial monitored · Not checked yet").wait_for()
    walk.shot("header")


def test_walk_during_a_check_progress_shows_and_the_queue_and_a_trial_stay_usable(make_app, make_walk):
    """test_walk_during_a_check_progress_shows_and_the_queue_and_a_trial_stay_usable"""
    app, walk = open_app(make_app, make_walk)
    page = walk.page
    app.registry.set("revise", True)
    app.registry.set("slow", True, delay=1.5)
    button = page.get_by_role("button", name="Check for updates")
    button.click()
    status = page.get_by_role("status")
    status.get_by_text("Checking for updates…").wait_for()
    assert re.search(r"\d of 3 trials checked · (Checking NCT\d{8}|Searching for new matches) next", status.inner_text()), status.inner_text()
    assert status.get_by_role("progressbar").count() == 1 or status.locator("progress").count() == 1
    # A second check cannot be started: the button is disabled and says why.
    assert button.is_disabled()
    assert page.locator("#check-reason").inner_text() == "A check is already running."
    walk.shot("checking")
    # The queue is readable and a trial opens while the check runs.
    assert page.locator("ul.queue > li.card").count() == 2
    page.locator('li.card[data-nct="NCT03412565"] h3 a').click()
    page.get_by_role("link", name="Open ClinicalTrials.gov").wait_for()  # the real trial page now
    page.go_back()
    page.get_by_role("status").get_by_text("Checking for updates…").wait_for()
    assert page.get_by_role("button", name="Check for updates").is_disabled()
    page.get_by_text("Check complete").wait_for(timeout=30000)
    assert page.get_by_role("button", name="Check for updates").is_enabled()
    assert page.locator("#check-reason").inner_text() == ""
    walk.shot("done")


def test_walk_a_check_with_one_failed_trial_is_incomplete_and_never_an_all_clear(make_app, make_walk):
    """test_walk_a_check_with_one_failed_trial_is_incomplete_and_never_an_all_clear"""
    app, walk = open_app(make_app, make_walk)
    page = walk.page
    app.registry.set("revise", True)
    app.registry.set("fail", True, ids=["NCT00000002"])
    page.get_by_role("button", name="Check for updates").click()
    status = page.get_by_role("status")
    status.get_by_role("heading", name="Check incomplete").wait_for(timeout=30000)
    text = status.inner_text()
    assert "2 of 3 trials checked · 1 trial could not be checked" in text, text
    # The saved search's outcome is its own line.
    assert status.locator(".search-line").inner_text() == "Saved search succeeded: Nothing new matched."
    assert "Check complete" not in text and "No new changes" not in text
    assert status.get_by_role("button", name="Retry failed").is_visible()
    assert page.get_by_text("Check complete").count() == 0
    # The failed trial keeps its previous data: the queue is as it was.
    assert page.locator("ul.queue > li.card").count() == 2
    status.get_by_role("button", name="Show details").click()
    assert "NCT00000002" in status.locator(".details").inner_text()
    walk.shot("incomplete")
    # Retry failed re-checks only that trial, once the registry is back.
    app.registry.set("fail", False)
    count_before = len(app.registry.server.state.requests)
    status.get_by_role("button", name="Retry failed").click()
    page.get_by_role("status").get_by_text("Check complete").wait_for(timeout=30000)
    lookups = [r for r in app.registry.server.state.requests[count_before:] if "/studies/" in r]
    assert [r.rsplit("/", 1)[-1].rstrip("?") for r in lookups] == ["NCT00000002"], lookups
    walk.shot("retried")


def test_walk_a_check_that_finds_nothing_says_so_and_keeps_earlier_entries_in_the_queue(make_app, make_walk):
    """test_walk_a_check_that_finds_nothing_says_so_and_keeps_earlier_entries_in_the_queue"""
    app, walk = open_app(make_app, make_walk)
    page = walk.page
    app.registry.set("revise", True)
    page.get_by_role("button", name="Check for updates").click()
    status = page.get_by_role("status")
    status.get_by_text("Check complete · No new changes detected").wait_for(timeout=30000)
    text = status.inner_text()
    assert re.search(r"3 of 3 checked at .*EST", text), text
    assert "2 trials still need review from earlier checks" in text, text
    assert [page.locator("ul.queue > li.card").nth(i).get_attribute("data-nct") for i in range(2)] == ["NCT03412565", "NCT00000002"]
    assert re.search(r"Last checked .*", page.locator("#watchlist-meta").inner_text())
    assert "11:45 AM EST" not in page.locator("#watchlist-meta").inner_text()  # moved on from the seeded check
    walk.shot("nothing-new")


def test_walk_with_nothing_to_review_the_queue_says_all_caught_up_and_stays_on_its_tab(make_app, make_walk):
    """test_walk_with_nothing_to_review_the_queue_says_all_caught_up_and_stays_on_its_tab"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    page.get_by_label("Watchlists").get_by_role("link", name="Quiet").click()
    page.get_by_text("All caught up").wait_for()
    page.get_by_role("button", name="Check for updates").click()
    status = page.get_by_role("status")
    status.get_by_text("Check complete").wait_for(timeout=30000)
    url = page.url
    caught_up = page.locator(".caught-up")
    text = caught_up.inner_text()
    assert "All caught up" in text and re.search(r"No changes awaiting review\. Last checked .*EST\.", text), text
    assert caught_up.get_by_role("link", name="View all trials").is_visible()
    assert page.get_by_role("tab", name="Needs review").get_attribute("aria-selected") == "true"
    page.wait_for_timeout(800)
    assert page.url == url  # nothing switched tabs by itself
    walk.shot("caught-up")


def test_walk_a_revised_trial_joins_needs_review_after_a_check_without_a_tab_change(make_app, make_walk):
    """test_walk_a_revised_trial_joins_needs_review_after_a_check_without_a_tab_change"""
    app, walk = open_app(make_app, make_walk, seed=seed_baseline)
    page = walk.page
    sidebar = page.get_by_label("Watchlists")
    assert "2 trials\n0" in sidebar.inner_text(), sidebar.inner_text()
    page.get_by_text("All caught up").wait_for()
    app.registry.set("revise", True)
    page.get_by_role("button", name="Check for updates").click()
    page.get_by_role("status").get_by_text("Check complete · 1 trial changed").wait_for(timeout=30000)
    page.locator('li.card[data-nct="NCT03412565"]').wait_for()
    page.wait_for_function("() => document.getElementById('sidebar').innerText.includes('2 trials\\n1')")
    assert "2 trials\n1" in sidebar.inner_text(), sidebar.inner_text()
    assert page.url.endswith("/needs-review")
    assert page.get_by_role("tab", name="Needs review").get_attribute("aria-selected") == "true"
    assert page.get_by_text("All caught up").count() == 0
    walk.shot("revised")
