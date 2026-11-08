"""Walk: the All trials tab (ticket 06).

Data: watchlist "Inventory" (the first, so the default) holds NCT03412565 (a real
revision, 3 changes), NCT00000002 (one simulated change), NCT00000003 (a change that was
reviewed), NCT00000004 (never changed, "Active not recruiting"), NCT00000005 (a long
title; its latest check failed, its last success was earlier) and fourteen fillers
with no changes, so the table is taller than the window. Every trial has its own title
and sponsor. Lacks: a trial that has never been checked, an empty watchlist, a second
watchlist with trials.
"""

from __future__ import annotations

from walks import helper

LONG_TITLE = ("Alpha-numeric long titled study of a combination regimen in adults with relapsed or "
              "refractory multiple myeloma who have received at least two prior lines of therapy "
              "including a proteasome inhibitor and an immunomodulatory agent")
TITLES = {
    "NCT03412565": "Zeta daratumumab study",
    "NCT00000002": "Beta simulated study",
    "NCT00000003": "Alpha reviewed study",
    "NCT00000004": "Delta quiet study",
    "NCT00000005": LONG_TITLE,
}
FILLERS = [f"NCT100000{n:02d}" for n in range(1, 15)]


def seed_all_trials(db: str, registry: helper.Registry) -> None:
    import monitor
    import simulate
    import storage

    def fetch(nct):
        record = registry.fetch(nct if nct in ("NCT03412565", "NCT00000002", "NCT00000003") else "NCT03412565")
        protocol = record["protocolSection"]
        protocol["identificationModule"]["nctId"] = nct
        protocol["identificationModule"]["briefTitle"] = TITLES.get(nct, f"Mid filler {nct[-2:]}")
        if nct == "NCT00000002":
            protocol["identificationModule"].pop("acronym", None)
        if nct == "NCT00000004":
            protocol["statusModule"]["overallStatus"] = "ACTIVE_NOT_RECRUITING"
        if nct == "NCT00000005":
            protocol["sponsorCollaboratorsModule"]["leadSponsor"]["name"] = "Wrapping Sponsor Ltd"
        return record

    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.rename_list(conn, first, "Inventory")
    stamp = "2026-11-01T08:00:00+00:00"
    for nct in ("NCT03412565", "NCT00000002", "NCT00000003", "NCT00000004", "NCT00000005", *FILLERS):
        monitor.add(conn, nct, first, fetch=fetch, when=stamp)
    storage.add_change(conn, "NCT00000003", {"field": "enrollment", "previous": 1, "current": 2},
                       "2026-11-03T08:00:00+00:00")
    storage.mark_reviewed(conn, "NCT00000003", "2026-11-04T08:00:00+00:00")
    simulate.rewind(conn, "NCT00000002", when="2026-11-02T08:00:00+00:00")
    monitor.check(conn, "NCT00000002", fetch=fetch, when="2026-11-08T09:00:00+00:00")
    registry.set("revise", True)
    monitor.check(conn, "NCT03412565", fetch=fetch, when="2026-11-08T16:45:00+00:00")
    registry.set("revise", False)
    storage.mark_checked(conn, "NCT00000005", "2026-11-07T10:00:00+00:00")
    storage.mark_check_failed(conn, "NCT00000005", "unreachable", "2026-11-08T17:00:00+00:00")
    conn.close()


def open_all_trials(make_app, make_walk):
    app = make_app(seed=seed_all_trials)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("tab", name="All trials").click()
    walk.page.get_by_role("table").wait_for()
    return app, walk


def titles(page):
    return page.locator("table.trials tbody tr td:first-child a").all_inner_texts()


def test_walk_all_trials_lists_every_trial_with_its_facts_headers_stay_and_titles_wrap(make_app, make_walk):
    """test_walk_all_trials_lists_every_trial_with_its_facts_headers_stay_and_titles_wrap"""
    _, walk = open_all_trials(make_app, make_walk)
    page = walk.page
    assert page.get_by_role("tab", name="All trials").get_attribute("aria-selected") == "true"
    heads = page.locator("table.trials thead th").all_text_contents()
    assert [h.strip() for h in heads] == ["Trial", "Trial status", "Review", "Last successful check"], heads
    assert page.locator("table.trials tbody tr").count() == 19
    row = page.locator('tr[data-nct="NCT03412565"]')
    cells = row.locator("td")
    assert row.locator("td a").first.inner_text() == "Zeta daratumumab study"
    assert "Phase 2" in cells.nth(0).inner_text() and "Janssen Research & Development, LLC" in cells.nth(0).inner_text()
    assert cells.nth(1).inner_text() == "Completed"
    assert cells.nth(2).inner_text() == "3 changes"
    assert cells.nth(3).inner_text().startswith("Nov 8, 2026, 11:45 AM EST"), cells.nth(3).inner_text()
    assert page.get_by_text("19 trials").first.is_visible()
    walk.shot("table")
    # A long title wraps onto a taller row and nothing runs sideways.
    long_row = page.locator('tr[data-nct="NCT00000005"]')
    assert long_row.locator("td a").first.inner_text() == LONG_TITLE
    assert long_row.bounding_box()["height"] > 2 * page.locator('tr[data-nct="NCT00000004"]').bounding_box()["height"] * 0.9
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    # Headers stay visible while the page scrolls.
    head = page.locator("table.trials thead th").first
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    assert page.evaluate("window.scrollY") > 100
    box = head.bounding_box()
    assert 0 <= box["y"] < 80 and head.is_visible()
    walk.shot("scrolled")


def test_walk_the_review_state_is_separate_from_the_registry_status(make_app, make_walk):
    """test_walk_the_review_state_is_separate_from_the_registry_status"""
    _, walk = open_all_trials(make_app, make_walk)
    page = walk.page

    def pair(nct):
        cells = page.locator(f'tr[data-nct="{nct}"] td')
        return cells.nth(1).inner_text(), cells.nth(2).inner_text()

    assert pair("NCT03412565") == ("Completed", "3 changes")
    assert pair("NCT00000002") == ("Completed", "3 changes")
    assert pair("NCT00000003") == ("Completed", "Reviewed")
    assert pair("NCT00000004") == ("Active not recruiting", "No changes")


def test_walk_a_failed_check_is_labelled_and_keeps_the_earlier_success_time(make_app, make_walk):
    """test_walk_a_failed_check_is_labelled_and_keeps_the_earlier_success_time"""
    _, walk = open_all_trials(make_app, make_walk)
    page = walk.page
    cell = page.locator('tr[data-nct="NCT00000005"] td').nth(3)
    assert "Nov 7, 2026, 5:00 AM EST" in cell.inner_text(), cell.inner_text()
    assert cell.get_by_role("note").inner_text().startswith("⚠ Latest check failed")
    assert page.locator('tr[data-nct="NCT00000004"]').get_by_role("note").count() == 0
    walk.shot("failed")


def test_walk_the_filter_searches_only_this_watchlist_and_says_so(make_app, make_walk):
    """test_walk_the_filter_searches_only_this_watchlist_and_says_so"""
    _, walk = open_all_trials(make_app, make_walk)
    page = walk.page
    box = page.get_by_label("Filter by title, NCT ID or sponsor")
    assert "not ClinicalTrials.gov" in page.locator("#filter-note").inner_text()
    box.fill("delta")
    assert titles(page) == ["Delta quiet study"]
    box.fill("NCT00000005")
    assert titles(page) == [LONG_TITLE]
    box.fill("wrapping sponsor")
    assert titles(page) == [LONG_TITLE]
    assert page.get_by_text("1 of 19 trials").is_visible()
    box.fill("nothing like this")
    assert titles(page) == []
    assert page.get_by_text("No trials in this watchlist match").is_visible()
    walk.shot("filtered")


def test_walk_sorting_by_title_latest_change_and_trial_status_reorders_the_table(make_app, make_walk):
    """test_walk_sorting_by_title_latest_change_and_trial_status_reorders_the_table"""
    _, walk = open_all_trials(make_app, make_walk)
    page = walk.page
    sort = page.get_by_label("Sort")
    assert sort.input_value() == "title"
    by_title = titles(page)
    assert by_title[0] == "Alpha reviewed study" or by_title[0].startswith("Alpha")
    assert by_title == sorted(by_title, key=str.lower)
    sort.select_option(label="Latest change")
    by_change = titles(page)
    assert by_change[:3] == ["Zeta daratumumab study", "Beta simulated study", "Alpha reviewed study"], by_change[:4]
    assert by_change != by_title
    sort.select_option(label="Trial status")
    statuses = page.locator("table.trials tbody tr td:nth-child(2)").all_inner_texts()
    assert statuses[0] == "Active not recruiting"
    assert statuses == sorted(statuses)
    assert titles(page) != by_change
    walk.shot("sorted")


def test_walk_a_title_opens_trial_details_with_changes_one_click_away(make_app, make_walk):
    """test_walk_a_title_opens_trial_details_with_changes_one_click_away"""
    _, walk = open_all_trials(make_app, make_walk)
    page = walk.page
    page.get_by_role("link", name="Zeta daratumumab study").click()
    page.get_by_role("heading", level=1, name="Zeta daratumumab study").wait_for()
    assert page.get_by_role("tab", name="Trial details").get_attribute("aria-selected") == "true"
    assert page.get_by_role("tab", name="Changes").is_visible()
    page.get_by_role("link", name="Back to Inventory").click()
    page.get_by_role("table").wait_for()
    assert page.get_by_role("tab", name="All trials").get_attribute("aria-selected") == "true"


def test_walk_a_watchlist_opens_on_needs_review_and_remembers_all_trials(make_app, make_walk):
    """test_walk_a_watchlist_opens_on_needs_review_and_remembers_all_trials"""
    app = make_app(seed=seed_all_trials)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("heading", name="2 trials need review").wait_for()
    assert page.get_by_role("tab", name="Needs review").get_attribute("aria-selected") == "true"
    page.get_by_role("tab", name="All trials").click()
    page.get_by_role("table").wait_for()
    # Leave for Find trials and come back through the sidebar: All trials is kept.
    page.get_by_role("link", name="Find trials").click()
    page.get_by_role("heading", name="Find trials").first.wait_for()
    page.get_by_role("link", name="Watchlists", exact=True).click()
    page.get_by_role("table").wait_for()
    assert page.get_by_role("tab", name="All trials").get_attribute("aria-selected") == "true"
    page.get_by_label("Watchlists").get_by_role("link", name="Inventory").click()
    page.get_by_role("table").wait_for()
    # A check that changes the counts does not switch the tab.
    before = page.locator('tr[data-nct="NCT03412565"] td').nth(2).inner_text()
    page.get_by_role("button", name="Check for updates").click()
    page.wait_for_function(
        "(b) => document.querySelector('tr[data-nct=\"NCT03412565\"] td:nth-child(3)').innerText !== b", arg=before, timeout=30000)
    assert page.get_by_role("tab", name="All trials").get_attribute("aria-selected") == "true"
    walk.shot("after-check")
