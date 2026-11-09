"""Walk: the New matches tab: add, dismiss, undo, view dismissed, restore (ticket 11).

Data: "Myeloma" holding NCT03412565 with a saved search; the offer is seeded as found rows
(NCT00000002, NCT00000003 and ten of the "many" copies) so selecting needs no check first;
"Quiet" holds NCT00000003 with no search; "Bare" has a saved search and no trials. The
stand-in's register switch and its 134-study "many" search drive the checks. Lacks: distinct
titles (every study is the same captured one) and a registry failure while adding.
"""

from __future__ import annotations

import re

STAMP = "2026-11-01T08:00:00+00:00"
MANY = [f"NCT{10000000 + n:08d}" for n in range(1, 11)]


def seed(db, registry, offered=True):
    import monitor
    import storage

    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.rename_list(conn, first, "Myeloma")
    monitor.add(conn, "NCT03412565", first, fetch=registry.fetch, when=STAMP)
    monitor.remember_search(conn, first, monitor.as_query(cond="myeloma"))
    quiet = monitor.create_list(conn, "Quiet", when=STAMP)
    monitor.add(conn, "NCT00000003", quiet, fetch=registry.fetch, when=STAMP)
    bare = monitor.create_list(conn, "Bare", when=STAMP)
    monitor.remember_search(conn, bare, monitor.as_query(cond="myeloma"))
    if offered:
        for nct in ["NCT00000002", "NCT00000003"] + MANY:
            storage.add_found(conn, first, nct, registry.fetch(nct), STAMP)
        storage.add_found(conn, quiet, "NCT00000002", registry.fetch("NCT00000002"), STAMP)
    conn.close()


def seed_empty(db, registry):
    seed(db, registry, offered=False)


def seed_many(db, registry):
    """Myeloma watches the "many" search (134 matches) and holds one of them."""
    import monitor
    import storage

    seed_empty(db, registry)
    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT10000002", first, fetch=registry.fetch, when=STAMP)
    monitor.remember_search(conn, first, monitor.as_query(cond="many"))
    conn.close()


def open_tab(make_app, make_walk, seed=seed, tab="new-matches", watchlist=None):
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", level=1, name="Myeloma").wait_for()
    if watchlist:
        page.get_by_label("Watchlists").get_by_role("link", name=re.compile(f"^{watchlist}")).click()
        page.get_by_role("heading", level=1, name=watchlist).wait_for()
    if tab:
        page.get_by_role("tab", name=re.compile("^New matches")).click()
        page.get_by_role("heading", level=2, name=re.compile("new match|No new matches")).wait_for()
    return app, walk


def box(page, nct):
    return page.locator(f'li.card[data-nct="{nct}"] input[type=checkbox]')


def bar(page):
    return page.get_by_role("region", name="New matches actions")


def test_walk_new_matches_is_its_own_tab_with_a_count_and_never_called_a_change(make_app, make_walk):
    """test_walk_new_matches_is_its_own_tab_with_a_count_and_never_called_a_change"""
    _, walk = open_tab(make_app, make_walk)
    page = walk.page
    tabs = page.get_by_role("tablist", name="Watchlist views")
    assert [t.strip() for t in tabs.get_by_role("tab").all_inner_texts()] == ["Needs review 0", "All trials 1", "New matches 12", "Summary"]
    assert page.get_by_role("tab", name="New matches").get_attribute("aria-selected") == "true"
    assert page.get_by_role("heading", level=2, name="12 new matches").is_visible()
    assert page.get_by_text("Not monitored yet. Select the trials you want to add.").is_visible()
    text = page.locator("#queue").inner_text().lower()
    assert "registration" not in text and "registered" not in text and "changed" not in text
    assert page.locator("li.card.match").count() == 12
    assert page.get_by_role("button", name="View dismissed").is_visible()
    assert bar(page).is_hidden()  # nothing selected, no bar
    walk.shot("tab")


def test_walk_after_the_register_switch_a_check_adds_the_new_study_to_new_matches_and_needs_review_is_unaffected(make_app, make_walk):
    """test_walk_after_the_register_switch_a_check_adds_the_new_study_to_new_matches_and_needs_review_is_unaffected"""
    app, walk = open_tab(make_app, make_walk, seed=seed_empty, tab=None)
    page = walk.page
    page.get_by_role("tab", name=re.compile("^New matches")).click()
    page.get_by_role("heading", level=2, name="No new matches").wait_for()  # nothing offered before a check
    app.registry.set("register", True)
    page.get_by_role("button", name="Check for updates").click()
    page.locator("#check-status").get_by_text("Check complete").wait_for(timeout=30000)
    page.get_by_role("heading", level=2, name="3 new matches").wait_for()
    page.locator('li.card[data-nct="NCT00000099"]').wait_for()
    assert page.locator("#check-status").get_by_text("Saved search succeeded: 3 new trials found.").is_visible()
    assert page.get_by_role("tab", name=re.compile("^New matches")).inner_text().strip() == "New matches 3"
    page.get_by_role("tab", name=re.compile("^Needs review")).click()
    page.get_by_text("All caught up").wait_for()  # the queue is unaffected
    assert page.get_by_role("tab", name=re.compile("^Needs review")).inner_text().strip() == "Needs review 0"
    walk.shot("registered")


def test_walk_selecting_matches_shows_an_action_bar_that_never_covers_the_last_match_and_adding_takes_baselines(make_app, make_walk):
    """test_walk_selecting_matches_shows_an_action_bar_that_never_covers_the_last_match_and_adding_takes_baselines"""
    app, walk = open_tab(make_app, make_walk)
    page = walk.page
    box(page, "NCT00000002").check()
    box(page, "NCT00000003").check()
    region = bar(page)
    region.wait_for()
    assert "2 selected" in region.inner_text()
    region.get_by_role("button", name="Dismiss 2").wait_for()
    region.get_by_role("button", name="Add 2 to watchlist").wait_for()
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    last = page.locator("li.card.match").last.bounding_box()
    top = region.bounding_box()
    assert last["y"] + last["height"] <= top["y"] + 1, (last, top)  # the bar does not cover the last match
    walk.shot("selected")
    region.get_by_role("button", name="Add 2 to watchlist").click()
    region.get_by_text("2 added").wait_for()
    assert region.get_by_role("link", name="View All trials").is_visible()
    page.get_by_role("heading", level=2, name="10 new matches").wait_for()
    assert page.get_by_role("tab", name=re.compile("^All trials")).inner_text().strip() == "All trials 3"
    walk.shot("added")
    region.get_by_role("link", name="View All trials").click()
    page.locator('tr[data-nct="NCT00000002"]').wait_for()
    row = page.locator('tr[data-nct="NCT00000002"]')
    assert "No changes" in row.inner_text()  # a baseline, not a change
    assert "Not checked yet" not in row.inner_text()


def test_walk_dismiss_states_the_consequence_before_committing_and_then_offers_undo(make_app, make_walk):
    """test_walk_dismiss_states_the_consequence_before_committing_and_then_offers_undo"""
    app, walk = open_tab(make_app, make_walk)
    page = walk.page
    box(page, "NCT00000002").check()
    region = bar(page)
    region.get_by_role("button", name="Dismiss 1").click()
    region.get_by_text("These trials will not be suggested again for this list.").wait_for()
    assert page.locator("li.card.match").count() == 12  # nothing was dismissed yet
    walk.shot("consequence")
    region.get_by_role("button", name="Cancel").click()
    region.get_by_role("button", name="Dismiss 1").wait_for()
    region.get_by_role("button", name="Dismiss 1").click()
    region.get_by_role("button", name="Yes, dismiss 1").click()
    region.get_by_text("1 trial dismissed.").wait_for()
    page.get_by_role("heading", level=2, name="11 new matches").wait_for()
    assert page.locator('li.card[data-nct="NCT00000002"]').count() == 0
    walk.shot("dismissed")
    region.get_by_role("button", name="Undo").click()
    page.get_by_role("heading", level=2, name="12 new matches").wait_for()
    page.locator('li.card[data-nct="NCT00000002"]').wait_for()
    # dismissing in one watchlist changes nothing in another: Quiet still offers it
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Quiet")).click()
    page.get_by_role("heading", level=1, name="Quiet").wait_for()
    page.get_by_role("tab", name=re.compile("^New matches")).click()
    page.locator('li.card[data-nct="NCT00000002"]').wait_for()


def test_walk_view_dismissed_lists_dismissed_matches_with_restore_and_a_restored_one_returns(make_app, make_walk):
    """test_walk_view_dismissed_lists_dismissed_matches_with_restore_and_a_restored_one_returns"""
    app, walk = open_tab(make_app, make_walk)
    page = walk.page
    box(page, "NCT00000002").check()
    box(page, "NCT00000003").check()
    region = bar(page)
    region.get_by_role("button", name="Dismiss 2").click()
    region.get_by_role("button", name="Yes, dismiss 2").click()
    page.get_by_role("heading", level=2, name="10 new matches").wait_for()
    page.get_by_role("button", name="View dismissed").click()
    page.get_by_role("heading", level=2, name="2 dismissed matches").wait_for()
    assert page.locator("li.card.match").count() == 2
    walk.shot("dismissed-list")
    page.locator('li.card[data-nct="NCT00000002"]').get_by_role("button", name=re.compile("^Restore")).click()
    page.get_by_role("heading", level=2, name="1 dismissed match").wait_for()
    page.get_by_role("button", name="Back to new matches").click()
    page.get_by_role("heading", level=2, name="11 new matches").wait_for()
    page.locator('li.card[data-nct="NCT00000002"]').wait_for()
    assert page.locator('li.card[data-nct="NCT00000003"]').count() == 0  # still dismissed


def test_walk_a_watchlist_with_a_saved_search_and_no_trials_offers_check_for_new_matches(make_app, make_walk):
    """test_walk_a_watchlist_with_a_saved_search_and_no_trials_offers_check_for_new_matches"""
    app, walk = open_tab(make_app, make_walk, tab=None, watchlist="Bare")
    page = walk.page
    assert page.get_by_role("heading", name="Monitor your first trial").count() == 0
    assert page.get_by_role("button", name="Check for updates").count() == 0
    page.get_by_role("button", name="Check for new matches").click()
    status = page.locator("#check-status")
    status.get_by_text("Check complete").wait_for(timeout=30000)
    assert "Saved search succeeded: 3 new trials found." in status.inner_text()
    assert "0 of 0" not in status.inner_text()
    page.get_by_role("tab", name=re.compile("^New matches")).click()
    page.get_by_role("heading", level=2, name="3 new matches").wait_for()
    walk.shot("bare")


def test_walk_a_search_that_found_more_than_a_hundred_says_so_on_the_tab_and_in_the_check_result(make_app, make_walk):
    """test_walk_a_search_that_found_more_than_a_hundred_says_so_on_the_tab_and_in_the_check_result"""
    _, walk = open_tab(make_app, make_walk, seed=seed_many, tab=None)
    page = walk.page
    page.get_by_role("button", name="Check for updates").click()
    status = page.locator("#check-status")
    status.get_by_text("Check complete").wait_for(timeout=60000)
    assert "more than 100" in status.inner_text(), status.inner_text()
    page.get_by_role("tab", name=re.compile("^New matches")).click()
    page.get_by_role("heading", level=2, name="99 new matches").wait_for()  # 100 offered, one already held
    note = page.get_by_role("note").filter(has_text="more than 100")
    assert note.is_visible()
    walk.shot("capped")


def finish_a_check(app, page):
    """Run a check slowly enough to see it start, then wait for it to finish (a second check would otherwise meet the first one's message)."""
    app.registry.set("slow", True, delay=0.8)
    page.get_by_role("button", name="Check for updates").click()
    page.locator("#check-status").get_by_text("Checking for updates…").wait_for()
    page.locator("#check-status").get_by_text("Check complete").wait_for(timeout=30000)


def test_walk_a_finished_check_keeps_the_tick_and_the_action_bar(make_app, make_walk):
    """test_walk_a_finished_check_keeps_the_tick_and_the_action_bar"""
    app, walk = open_tab(make_app, make_walk)
    page = walk.page
    box(page, "NCT00000002").check()
    bar(page).get_by_text("1 selected").wait_for()
    finish_a_check(app, page)
    assert box(page, "NCT00000002").is_checked()
    assert bar(page).get_by_text("1 selected").is_visible()
    walk.shot("tick-kept")


def test_walk_a_finished_check_keeps_a_pending_dismiss_and_the_dismissed_list(make_app, make_walk):
    """test_walk_a_finished_check_keeps_a_pending_dismiss_and_the_dismissed_list"""
    app, walk = open_tab(make_app, make_walk)
    page = walk.page
    box(page, "NCT00000002").check()
    bar(page).get_by_role("button", name="Dismiss 1").click()
    page.get_by_role("button", name="Yes, dismiss 1").wait_for()
    finish_a_check(app, page)
    assert page.get_by_role("button", name="Yes, dismiss 1").is_visible()
    page.get_by_role("button", name="Cancel").click()
    box(page, "NCT00000002").uncheck()
    page.get_by_role("button", name="View dismissed").click()
    page.locator("#back-to-matches").wait_for()
    finish_a_check(app, page)
    assert page.locator("#back-to-matches").is_visible()
    walk.shot("dismissed-kept")
