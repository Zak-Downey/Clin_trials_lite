"""Walk: the trial page's details, history and watchlist menu (ticket 05).

Data: the ticket 04 seed (NCT03412565 in "Myeloma" and "Elsewhere" with checks at 14:20 and
16:45 UTC on 8 Nov 2026), plus NCT00000003 (acronym "ISA-MM", no unreviewed changes, its
latest check failed), a review of the 14:20 check, a review of the 16:45 check that was
undone, and NCT00000004, taken out of "Myeloma" and put back. Lacks: a trial with no
registry link, a section too long to need scrolling inside, more than two lists.
"""

from __future__ import annotations

import re

from walks import helper
from walks.test_trial_page_walk import seed_trial_page

ACRONYM = "NCT00000003"
GAP = "NCT00000004"


def seed(db: str, registry: helper.Registry) -> None:
    import monitor
    import storage

    seed_trial_page(db, registry)
    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    stamp = "2026-11-01T08:00:00+00:00"

    def fetch(nct):
        record = registry.fetch("NCT03412565")
        ident = record["protocolSection"]["identificationModule"]
        ident["nctId"] = nct
        if nct == ACRONYM:
            ident["acronym"] = "ISA-MM"
        return record

    monitor.add(conn, ACRONYM, first, fetch=fetch, when=stamp)
    storage.mark_check_failed(conn, ACRONYM, "unavailable", "2026-11-08T18:00:00+00:00")
    monitor.add(conn, GAP, first, fetch=fetch, when=stamp)
    storage.remove_member(conn, first, GAP, "2026-11-03T10:00:00+00:00")
    storage.add_member(conn, first, GAP, "2026-11-05T10:00:00+00:00")
    changes = storage.list_changes(conn, "NCT03412565")
    early = [c["id"] for c in changes if c["detected_at"] == "2026-11-08T14:20:00+00:00"]
    late = [c["id"] for c in changes if c["detected_at"] == "2026-11-08T16:45:00+00:00"]
    storage.review_changes(conn, "NCT03412565", early, "2026-11-08T15:10:00+00:00")
    event = storage.review_changes(conn, "NCT03412565", late, "2026-11-08T17:02:00+00:00")
    storage.undo_review(conn, event["id"], "2026-11-08T17:30:00+00:00")
    conn.close()


def open_page(make_app, make_walk, nct, tab="", from_queue=False):
    app = make_app(seed=seed)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.locator('li.card[data-nct="NCT03412565"]').wait_for()
    if from_queue:
        page.locator('li.card[data-nct="NCT03412565"] h3 a').click()
    else:
        page.evaluate(f"location.hash = '#/trials/{nct}{tab}'")
    page.get_by_role("heading", level=1).wait_for()
    return app, walk


def test_walk_the_heading_is_the_acronym_else_the_brief_title_and_identity_is_untruncated(make_app, make_walk):
    """test_walk_the_heading_is_the_acronym_else_the_brief_title_and_identity_is_untruncated"""
    _, walk = open_page(make_app, make_walk, ACRONYM, "/details")
    page = walk.page
    assert page.get_by_role("heading", level=1).inner_text() == "ISA-MM"
    identity = page.locator("section.detail-section", has_text="Identity & study design")
    text = identity.inner_text()
    assert "A Multicenter Phase 2 Study to Evaluate Subcutaneous Daratumumab in C" in text
    official = identity.locator(".detail-field", has_text="Official title").locator("dd")
    assert len(official.inner_text()) > 80 and official.inner_text().strip() in text
    assert page.evaluate("(el) => el.scrollWidth <= el.clientWidth", official.element_handle())
    for ident in ("CR108435", "2017-004203-41", "54767414MMY2040", ACRONYM):
        assert ident in text, ident
    walk.shot("identity")
    page.evaluate("location.hash = '#/trials/NCT03412565/details'")
    page.get_by_role("heading", level=1, name=re.compile("^A Study to Evaluate")).wait_for()


def test_walk_the_header_shows_last_checked_and_a_failed_check_carries_a_labelled_warning(make_app, make_walk):
    """test_walk_the_header_shows_last_checked_and_a_failed_check_carries_a_labelled_warning"""
    _, walk = open_page(make_app, make_walk, ACRONYM)
    page = walk.page
    meta = page.locator(".trial-head .meta")
    assert re.search(r"Last checked .*\b\d{4}\b.*(AM|PM)", meta.inner_text()), meta.inner_text()
    assert page.get_by_text("Latest check failed").is_visible()
    walk.shot("failed")
    page.evaluate("location.hash = '#/trials/NCT03412565'")
    page.get_by_role("heading", level=1, name=re.compile("^A Study to Evaluate")).wait_for()
    assert page.get_by_text("Latest check failed").count() == 0


def test_walk_at_a_glance_shows_status_phase_sponsor_enrolment_link_and_when_monitoring_began(make_app, make_walk):
    """test_walk_at_a_glance_shows_status_phase_sponsor_enrolment_link_and_when_monitoring_began"""
    _, walk = open_page(make_app, make_walk, ACRONYM, "/details")
    glance = walk.page.get_by_label("At a glance")
    glance.wait_for()
    text = glance.inner_text()
    for expected in ("Completed", "Phase 2", "Janssen Research & Development, LLC", "265 · Actual", "1 November 2026"):
        assert expected in text, (expected, text)
    link = glance.get_by_role("link", name=re.compile("registry"))
    assert link.get_attribute("href").endswith(f"/{ACRONYM}")
    walk.shot("glance")


def test_walk_trial_details_has_five_sections_long_ones_expand_and_an_unreviewed_field_is_never_collapsed(make_app, make_walk):
    """test_walk_trial_details_has_five_sections_long_ones_expand_and_an_unreviewed_field_is_never_collapsed"""
    _, walk = open_page(make_app, make_walk, ACRONYM, "/details")
    page = walk.page
    page.locator(".detail-section").nth(4).wait_for()
    titles = page.locator(".detail-section h2").all_inner_texts()
    assert [t.split("\n")[0].strip("+− ").strip() for t in titles] == [
        "Identity & study design", "Conditions & eligibility", "Interventions & arms", "Endpoints", "Dates & results"]
    endpoints = page.get_by_role("button", name=re.compile("^Endpoints"))
    assert endpoints.get_attribute("aria-expanded") == "false"
    assert not page.get_by_text("Up to 2 years 3 months").first.is_visible()
    endpoints.click()
    assert endpoints.get_attribute("aria-expanded") == "true"
    page.get_by_text("Up to 2 years 3 months").first.wait_for()
    # NCT03412565 has unreviewed changes in three sections: those have no collapse control.
    page.evaluate("location.hash = '#/trials/NCT03412565/details'")
    page.get_by_role("heading", level=1, name=re.compile("^A Study to Evaluate")).wait_for()
    page.locator(".detail-section").nth(4).wait_for()
    for locked in ("Interventions & arms", "Dates & results"):
        section = page.locator("section.detail-section", has_text=locked)
        assert section.get_by_role("button").count() == 0
        assert section.locator(".section-body").first.is_visible()
    assert page.get_by_role("button", name=re.compile("^Endpoints")).get_attribute("aria-expanded") == "false"
    walk.shot("sections")


def test_walk_a_field_the_registry_omits_shows_not_reported(make_app, make_walk):
    """test_walk_a_field_the_registry_omits_shows_not_reported"""
    _, walk = open_page(make_app, make_walk, "NCT03412565", "/details")
    page = walk.page
    acronym = page.locator(".detail-field", has_text="Acronym").locator("dd")
    assert acronym.inner_text().strip() == "Not reported"
    assert "Not reported" in page.locator(".detail-field", has_text="Why stopped").inner_text()


def test_walk_history_is_newest_first_with_detections_reviews_undos_and_start_and_expands_every_transition(make_app, make_walk):
    """test_walk_history_is_newest_first_with_detections_reviews_undos_and_start_and_expands_every_transition"""
    _, walk = open_page(make_app, make_walk, "NCT03412565", "/history")
    page = walk.page
    page.locator("li.entry").first.wait_for()
    kinds = page.locator("li.entry").evaluate_all("(rows) => rows.map((r) => r.className.replace('entry ', ''))")
    assert kinds == ["undo", "review", "detection", "review", "detection", "start"], kinds
    text = page.locator("ol.timeline").inner_text()
    assert "Marked 3 changes from the 11:45 check as reviewed" in text
    assert "Marked 2 changes from the 09:20 check as reviewed" in text
    assert "Undid the review of 3 changes" in text
    # A reviewed check still shows every transition once expanded.
    reviewed = page.locator("li.entry.detection").nth(1)
    reviewed.get_by_role("button", name="Show details").click()
    transitions = reviewed.locator(".transitions li").all_inner_texts()
    assert any("Enrollment" in t and "248" in t and "265" in t for t in transitions), transitions
    assert any("Eligibility criteria" in t for t in transitions)
    assert all("Reviewed" in t for t in transitions)
    walk.shot("history")


def test_walk_history_shows_a_period_when_the_trial_was_not_monitored(make_app, make_walk):
    """test_walk_history_shows_a_period_when_the_trial_was_not_monitored"""
    _, walk = open_page(make_app, make_walk, GAP, "/history")
    page = walk.page
    page.locator("li.entry").first.wait_for()
    texts = page.locator("li.entry").evaluate_all("(rows) => rows.map((r) => r.innerText)")
    assert "Resumed monitoring" in texts[0] and "Stopped monitoring" in texts[1] and "Monitoring started" in texts[2], texts
    walk.shot("gap")


def test_walk_the_menu_lists_the_watchlists_and_removing_offers_undo_and_touches_no_other_list(make_app, make_walk):
    """test_walk_the_menu_lists_the_watchlists_and_removing_offers_undo_and_touches_no_other_list"""
    _, walk = open_page(make_app, make_walk, "NCT03412565", "/details", from_queue=True)
    page = walk.page
    page.get_by_role("button", name="More actions").click()
    menu = page.get_by_role("menu")
    assert "Myeloma" in menu.inner_text() and "Elsewhere" in menu.inner_text()
    walk.shot("menu")
    page.get_by_role("menuitem", name="Remove from this list").click()
    page.get_by_text("Removed from Myeloma.").wait_for()
    page.get_by_role("button", name="More actions").click()
    assert "Elsewhere" in page.get_by_role("menu").inner_text() and "Myeloma" not in page.get_by_role("menu").inner_text()
    page.keyboard.press("Escape")
    page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Elsewhere")).locator(".counts").wait_for()
    assert page.get_by_label("Watchlists").get_by_role("link", name=re.compile("^Elsewhere")).locator(".counts").inner_text() == "1 trial"
    page.get_by_role("button", name="Undo").click()
    page.get_by_role("button", name="Undo").wait_for(state="detached")
    page.get_by_role("button", name="More actions").click()
    assert "Myeloma" in page.get_by_role("menu").inner_text()
    walk.shot("undone")
