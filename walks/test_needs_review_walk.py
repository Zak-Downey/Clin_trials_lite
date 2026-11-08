"""Walk: the sidebar and the Needs review queue, the thin slice from ticket 01.

Data: the captured NCT03412565 record and two copies (NCT00000002, NCT00000003) in
a long-named watchlist and a quiet one (helper.seed_queue). One trial has a real
revision found at 16:45 UTC on 8 Nov 2026, one a simulated change found at 09:00
UTC. Lacks: an empty watchlist, a saved search, more than three trials, a trial
with an acronym, and any trial whose change was reviewed.
"""

from __future__ import annotations

import re

from walks import helper


def open_app(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("heading", level=1).wait_for()
    return app, walk


def test_walk_sidebar_lists_every_watchlist_with_counts_and_a_long_name_wraps(make_app, make_walk):
    """test_walk_sidebar_lists_every_watchlist_with_counts_and_a_long_name_wraps"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    links = page.get_by_label("Watchlists").get_by_role("link")
    assert links.count() == 2
    long_link = links.nth(0)
    assert helper.LONG_NAME in long_link.inner_text()
    assert "2 to review · 3 trials" in long_link.inner_text()
    quiet = links.nth(1)
    assert quiet.inner_text().startswith("Quiet") and "0 to review · 1 trial" in quiet.inner_text()
    assert "1 trials" not in quiet.inner_text()  # one trial, not "1 trials"
    # Wrapped, not cut: the name's text is whole, it spans several lines, and nothing spills out of the sidebar.
    name = long_link.locator("span").first
    lines = page.evaluate(
        "(el) => Math.round(el.getBoundingClientRect().height / parseFloat(getComputedStyle(el).lineHeight))",
        name.element_handle())
    assert lines >= 3
    assert page.evaluate("(el) => el.scrollWidth <= el.clientWidth", long_link.element_handle())
    assert page.evaluate("(el) => getComputedStyle(el).textOverflow", name.element_handle()) != "ellipsis"
    # The count badge is a pill with room round its words, on one line.
    badge = long_link.locator(".badge")
    box = badge.bounding_box()
    assert box["height"] <= 24 and page.evaluate("(el) => el.scrollWidth <= el.clientWidth", badge.element_handle())
    assert page.evaluate("(el) => parseFloat(getComputedStyle(el).paddingLeft)", badge.element_handle()) >= 8
    assert page.evaluate("(el) => parseFloat(getComputedStyle(el).paddingRight)", badge.element_handle()) >= 8
    walk.shot("sidebar")


def test_walk_a_watchlist_opens_on_needs_review_newest_detection_first(make_app, make_walk):
    """test_walk_a_watchlist_opens_on_needs_review_newest_detection_first"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    assert page.get_by_role("heading", level=1).inner_text() == helper.LONG_NAME
    assert page.get_by_role("tab", name="Needs review").get_attribute("aria-selected") == "true"
    counts = page.locator("#queue-counts").inner_text()
    assert "2 trials need review" in counts
    assert re.search(r"\b6 unreviewed field changes\b", counts), counts
    rows = page.locator("table.queue tbody tr")
    assert rows.count() == 2  # NCT00000003 has nothing unreviewed, so it is not listed
    assert [rows.nth(i).get_attribute("data-nct") for i in range(2)] == ["NCT03412565", "NCT00000002"]
    walk.shot("queue")
    page.get_by_label("Watchlists").get_by_role("link", name="Quiet").click()
    page.get_by_text("All caught up").wait_for()
    assert "0 trials need review" in page.locator("#queue-counts").inner_text()


def test_walk_a_queue_entry_shows_what_the_row_shows_and_labels_simulated_changes(make_app, make_walk):
    """test_walk_a_queue_entry_shows_what_the_row_shows_and_labels_simulated_changes"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    real = page.locator('tr[data-nct="NCT03412565"]')
    text = real.inner_text()
    assert real.locator("td").nth(0).locator("strong").inner_text()  # a heading
    assert "NCT03412565" in text
    # The detected time is the server's wall clock in its zone (New York), not the browser's (Tokyo).
    assert "11:45 AM EST" in text, text
    assert re.search(r"\(\d+\)", text)  # the change count
    for header in ("Trial", "Phase", "Sponsor", "Status", "What changed", "Detected"):
        assert page.get_by_role("columnheader", name=header).count() == 1
    assert page.locator("table.queue input[type=checkbox]").count() == 0
    assert real.get_by_text("Simulated changes").count() == 0
    simulated = page.locator('tr[data-nct="NCT00000002"]')
    assert simulated.get_by_text("Simulated changes").is_visible()
    assert "4:00 AM EST" in simulated.inner_text()
    walk.shot("entries")


def test_walk_the_queue_reads_in_words_not_registry_codes_and_keeps_short_cells_whole(make_app, make_walk):
    """test_walk_the_queue_reads_in_words_not_registry_codes_and_keeps_short_cells_whole"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    row = page.locator('tr[data-nct="NCT03412565"]')
    cells = row.locator("td")
    assert cells.nth(1).inner_text() == "Phase 2"
    assert cells.nth(3).inner_text() == "Completed"  # not the registry's COMPLETED
    changed = cells.nth(4).inner_text()
    for name in ("Completion date", "Enrollment", "Interventions"):
        assert name in changed, changed
    assert not re.search(r"[a-z][A-Z]", changed), changed  # no completionDate-style field names
    # Phase and Status each sit on one line: a word is never broken across lines.
    for column in (1, 3):
        lines = page.evaluate(
            "(td) => { const r = document.createRange(); r.selectNodeContents(td); return r.getClientRects().length }",
            cells.nth(column).element_handle())
        assert lines == 1, (column, lines)
    walk.shot("readable")


def test_walk_a_stale_watchlist_address_shows_not_found_and_the_walk_expects_the_404(make_app, make_walk):
    """test_walk_a_stale_watchlist_address_shows_not_found_and_the_walk_expects_the_404"""
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    walk.expect(404, "/api/watchlists/999/needs-review")
    walk.page.goto(f"{app.url}#/watchlists/999/needs-review")
    walk.page.get_by_text("There is no watchlist 999.").wait_for()
    walk.shot("not-found")


def test_walk_the_heading_and_review_changes_open_the_same_trial_address(make_app, make_walk):
    """test_walk_the_heading_and_review_changes_open_the_same_trial_address"""
    app, walk = open_app(make_app, make_walk)
    page = walk.page
    row = page.locator('tr[data-nct="NCT03412565"]')
    heading = row.locator("strong a")
    review = row.get_by_role("link", name="Review changes")
    assert heading.get_attribute("href") == review.get_attribute("href") == "#/trials/NCT03412565"
    review.click()
    page.wait_for_url(re.compile(r"#/trials/NCT03412565$"))
    page.go_back()
    page.locator('tr[data-nct="NCT03412565"] strong a').click()
    page.wait_for_url(re.compile(r"#/trials/NCT03412565$"))


def test_walk_reload_back_and_forward_keep_the_chosen_watchlist_and_tab(make_app, make_walk):
    """test_walk_reload_back_and_forward_keep_the_chosen_watchlist_and_tab"""
    _, walk = open_app(make_app, make_walk)
    page = walk.page
    sidebar = page.get_by_label("Watchlists")
    sidebar.get_by_role("link", name="Quiet").click()
    page.get_by_text("All caught up").wait_for()
    quiet_url = page.url
    assert quiet_url.endswith("/needs-review")

    def chosen(name):
        page.get_by_role("heading", level=1, name=name).wait_for()
        assert page.get_by_role("tab", name="Needs review").get_attribute("aria-selected") == "true"
        assert sidebar.get_by_role("link", name=name).get_attribute("class") == "active"

    page.reload()
    chosen("Quiet")
    sidebar.get_by_role("link", name=re.compile("Non-small")).click()
    chosen(helper.LONG_NAME)
    page.go_back()
    chosen("Quiet")
    page.go_forward()
    chosen(helper.LONG_NAME)


def test_walk_a_bare_address_is_rewritten_in_place_so_back_leaves_the_app(make_app, make_walk):
    """test_walk_a_bare_address_is_rewritten_in_place_so_back_leaves_the_app"""
    app, walk = open_app(make_app, make_walk)
    page = walk.page
    assert page.url.endswith("#/watchlists/1/needs-review")
    page.go_back()
    assert not page.url.startswith(app.url), page.url
