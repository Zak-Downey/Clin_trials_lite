"""Walk: the trial page, its Changes tab and the review action bar (ticket 04).

Data: watchlist "Myeloma" holds NCT03412565 (three real moves from a check at 16:45
UTC on 8 Nov 2026, an earlier check at 14:20 that moved enrolment too, and a
long eligibility text), NCT00000002 (a simulated change, from the simulator's
rewind) and fourteen filler trials with one change each, so the queue is taller
than the window. "Elsewhere" also holds NCT03412565. Lacks: a trial in no
watchlist, an acronym, a failed check, and changes that arrive while the page is open.
"""

from __future__ import annotations

import re

from walks import helper

LONG_TEXT = ("Inclusion: adults with relapsed or refractory multiple myeloma who have received at least "
             "two prior lines of therapy including a proteasome inhibitor and an immunomodulatory agent, "
             "with measurable disease and adequate organ function; ") * 8
FILLERS = [f"NCT100000{n:02d}" for n in range(1, 15)]


def seed_trial_page(db: str, registry: helper.Registry) -> None:
    import monitor
    import simulate
    import storage

    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.rename_list(conn, first, "Myeloma")
    elsewhere = monitor.create_list(conn, "Elsewhere", when="2026-11-01T08:00:00+00:00")
    stamp = "2026-11-01T08:00:00+00:00"
    base = registry.fetch("NCT03412565")

    def fetch(nct):
        record = registry.fetch("NCT03412565")
        record["protocolSection"]["identificationModule"]["nctId"] = nct
        return record

    for nct in ("NCT03412565", "NCT00000002"):
        monitor.add(conn, nct, first, fetch=registry.fetch, when=stamp)
    monitor.add(conn, "NCT03412565", elsewhere, fetch=registry.fetch, when=stamp)
    for n, nct in enumerate(FILLERS):
        monitor.add(conn, nct, first, fetch=fetch, when=stamp)
        storage.add_change(conn, nct, {"field": "enrollment", "previous": 10, "current": 20 + n},
                           f"2026-11-07T{8 + n % 10:02d}:00:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 248, "current": 265},
                       "2026-11-08T14:20:00+00:00")
    storage.add_change(conn, "NCT03412565", {"field": "eligibilityCriteria", "previous": "Adults.", "current": LONG_TEXT},
                       "2026-11-08T14:20:00+00:00")
    simulate.rewind(conn, "NCT00000002", when="2026-11-02T08:00:00+00:00")
    monitor.check(conn, "NCT00000002", fetch=registry.fetch, when="2026-11-08T09:00:00+00:00")
    registry.set("revise", True)
    monitor.check(conn, "NCT03412565", fetch=registry.fetch, when="2026-11-08T16:45:00+00:00")
    registry.set("revise", False)
    del base
    conn.close()


def open_trial(make_app, make_walk, nct="NCT03412565"):
    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.locator(f'li.card[data-nct="{nct}"]').wait_for()
    walk.page.locator(f'li.card[data-nct="{nct}"] h3 a').click()
    walk.page.get_by_role("heading", level=1).wait_for()
    walk.page.get_by_role("button", name="Mark reviewed").wait_for()
    return app, walk


def to_review(page, name):
    """The needs-review count the sidebar's badge shows for a watchlist (its title says "N to review")."""
    link = page.get_by_label("Watchlists").get_by_role("link", name=re.compile(f"^{name}"))
    return link.locator(".badge").get_attribute("title")


def wait_for_count(page, name, text):
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile(f"^{name}")).locator(
        f'.badge[title="{text}"]').wait_for(state="attached")


def test_walk_a_trial_opens_on_changes_with_the_other_tabs_near_and_back_keeps_the_queue_position(make_app, make_walk):
    """test_walk_a_trial_opens_on_changes_with_the_other_tabs_near_and_back_keeps_the_queue_position"""
    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.locator("ul.queue > li.card").nth(10).wait_for()
    page.evaluate("window.scrollTo(0, 400)")
    before = page.evaluate("window.scrollY")
    assert before > 100
    visible = page.locator("ul.queue > li.card").evaluate_all(
        "(rows) => rows.filter((r) => { const b = r.getBoundingClientRect(); return b.top > 60 && b.bottom < innerHeight })"
        ".map((r) => r.dataset.nct)")
    nct = visible[0]
    page.locator(f'li.card[data-nct="{nct}"] h3 a').click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.get_by_role("tab", name=re.compile("^Changes")).get_attribute("aria-selected") == "true"
    for name in ("Trial details", "History"):
        assert page.get_by_role("tab", name=name).is_visible()
    walk.shot("trial")
    page.get_by_role("link", name="‹ Back to Myeloma").click()
    page.locator("ul.queue > li.card").nth(10).wait_for()
    page.wait_for_function("(y) => Math.abs(scrollY - y) < 3", arg=before)
    assert abs(page.evaluate("window.scrollY") - before) < 3
    walk.shot("back")


def test_walk_each_change_has_labelled_previously_and_now_and_a_long_value_stacks_and_wraps(make_app, make_walk):
    """test_walk_each_change_has_labelled_previously_and_now_and_a_long_value_stacks_and_wraps"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    cards = page.locator("article.change")
    assert cards.count() == 5
    short = page.locator("article.change", has_text="Completion date")
    assert short.get_by_text("Previously").count() == 1 and short.get_by_text("Now", exact=True).count() == 1
    prev, now = (short.locator(f".{c}").bounding_box() for c in ("previously", "now"))
    assert now["x"] > prev["x"] + prev["width"] - 1  # short values sit side by side
    long = page.locator("article.change", has_text="Eligibility criteria")
    prev, now = (long.locator(f".{c}").bounding_box() for c in ("previously", "now"))
    assert now["y"] >= prev["y"] + prev["height"] - 1 and abs(now["x"] - prev["x"]) < 2  # stacked, Previously first
    assert page.evaluate("(el) => el.scrollWidth <= el.clientWidth", long.element_handle())
    assert long.locator(".now p").bounding_box()["height"] > 60  # wrapped over lines, not cut
    assert "Inclusion: adults" in long.locator(".now p").inner_text()
    walk.shot("changes")


def test_walk_each_check_group_shows_both_dates_and_a_field_that_moved_twice_shows_both_transitions(make_app, make_walk):
    """test_walk_each_check_group_shows_both_dates_and_a_field_that_moved_twice_shows_both_transitions"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    dates = page.locator(".group-dates").all_inner_texts()
    assert len(dates) == 2
    # Detected times are the server's wall clock in its zone (New York), not the browser's (Tokyo).
    assert re.fullmatch(r"Registry updated \d+ \w+ \d{4} · Detected .*11:45 AM EST", dates[0]), dates
    assert re.fullmatch(r"Registry updated \d+ \w+ \d{4} · Detected .*9:20 AM EST", dates[1]), dates
    moves = page.locator("article.change", has_text="Enrollment")
    assert moves.count() == 2
    texts = [moves.nth(i).inner_text() for i in range(2)]
    assert "265" in texts[0] and "282" in texts[0]  # the newer check: 265 to 282
    assert "248" in texts[1] and "265" in texts[1]  # the earlier one: 248 to 265


def test_walk_the_action_bar_states_its_scope_stays_visible_and_leaves_the_last_change_clear(make_app, make_walk):
    """test_walk_the_action_bar_states_its_scope_stays_visible_and_leaves_the_last_change_clear"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    bar = page.get_by_role("region", name="Review")
    assert "Review covers all 5 changes shown above." in bar.inner_text()
    assert "Also clears these changes in: Elsewhere." in bar.inner_text()
    height = page.evaluate("innerHeight")
    assert page.evaluate("document.documentElement.scrollHeight") > height  # there is something to scroll
    assert bar.bounding_box()["y"] + bar.bounding_box()["height"] <= height + 1  # visible before any scrolling
    page.evaluate("window.scrollTo(0, 200)")
    box = bar.bounding_box()
    assert box["y"] + box["height"] <= height + 1 and box["y"] >= 0
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    last = page.locator("article.change").last.bounding_box()
    assert last["y"] + last["height"] <= bar.bounding_box()["y"] + 1  # the bar never covers the last change
    walk.shot("action-bar")


def test_walk_marking_reviewed_keeps_the_page_labels_each_change_drops_the_counts_and_holds_the_scroll(make_app, make_walk):
    """test_walk_marking_reviewed_keeps_the_page_labels_each_change_drops_the_counts_and_holds_the_scroll"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    assert to_review(page, "Myeloma") == "16 to review" and to_review(page, "Elsewhere") == "1 to review"
    page.evaluate("window.scrollTo(0, 150)")
    before = page.evaluate("window.scrollY")
    page.get_by_role("button", name="Mark reviewed").click()
    page.get_by_text("5 changes marked reviewed. This trial stays open.").wait_for()
    assert page.locator(".reviewed-label:visible").count() == 5
    assert page.get_by_role("tab", name=re.compile("^Changes")).get_attribute("aria-selected") == "true"
    assert page.get_by_role("button", name="Undo").is_visible()
    wait_for_count(page, "Myeloma", "15 to review")
    assert to_review(page, "Elsewhere") == "0 to review"
    assert abs(page.evaluate("window.scrollY") - before) < 3
    walk.shot("reviewed")


def test_walk_undo_restores_the_changes_and_counts_and_is_gone_after_leaving(make_app, make_walk):
    """test_walk_undo_restores_the_changes_and_counts_and_is_gone_after_leaving"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Mark reviewed").click()
    page.get_by_role("button", name="Undo").click()
    page.get_by_role("button", name="Undo").wait_for(state="detached")
    assert page.locator(".reviewed-label:visible").count() == 0
    assert page.get_by_role("button", name="Mark reviewed").is_enabled()
    wait_for_count(page, "Myeloma", "16 to review")
    # Review again, then take another action (a tab): Undo is gone and stays gone on return.
    page.get_by_role("button", name="Mark reviewed").click()
    page.get_by_role("button", name="Undo").wait_for()
    page.get_by_role("tab", name="History").click()
    page.get_by_role("heading", name="Trial history").wait_for()
    assert page.get_by_role("button", name="Undo").count() == 0
    page.get_by_role("tab", name=re.compile("^Changes")).click()
    page.get_by_text("No unreviewed changes").wait_for()
    assert page.get_by_role("button", name="Undo").count() == 0


def test_walk_next_trial_opens_the_next_in_needs_review_and_marks_nothing(make_app, make_walk):
    """test_walk_next_trial_opens_the_next_in_needs_review_and_marks_nothing"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Next trial").click()
    page.wait_for_url(re.compile(r"#/trials/NCT00000002$"))
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert to_review(page, "Myeloma") == "16 to review"
    page.get_by_role("link", name="‹ Back to Myeloma").click()
    page.locator('li.card[data-nct="NCT03412565"]').wait_for()  # still in the queue, unreviewed


def test_walk_a_trial_with_simulated_changes_carries_the_simulated_label_on_its_changes_tab(make_app, make_walk):
    """test_walk_a_trial_with_simulated_changes_carries_the_simulated_label_on_its_changes_tab"""
    _, walk = open_trial(make_app, make_walk, "NCT00000002")
    page = walk.page
    assert page.get_by_text("Simulated changes").is_visible()
    walk.shot("simulated")
    page.goto(page.url.replace("NCT00000002", "NCT03412565"))
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert page.get_by_text("Simulated changes").count() == 0
