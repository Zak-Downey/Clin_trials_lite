"""Walk: the Summary tab, its periods, Custom dates, Copy summary and Export CSV (ticket 12).

Data: watchlist "Myeloma" holds NCT03412565 (enrolment moved at two checks this week,
the older one already reviewed, plus one change 45 days ago) and NCT00000002 (simulated
changes found now). The stamps are relative to the clock, so they sit in this week and
this month whenever the walk runs. Lacks: a trial with no checks, a period crossing a
year, a second watchlist with its own changes.
"""

from __future__ import annotations

import csv
import datetime
import io
import re
import zoneinfo

from walks import helper


# NCT03412565's two seeded changes in the period plus the three the simulated check of
# NCT00000002 finds; the 45-day-old change is outside This week and This month.
EXPECTED_CHANGES = 5


def seed_summary(db: str, registry: helper.Registry) -> None:
    import monitor
    import simulate
    import storage

    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.rename_list(conn, first, "Myeloma")
    stamp = "2026-01-01T08:00:00+00:00"
    for nct in ("NCT03412565", "NCT00000002"):
        monitor.add(conn, nct, first, fetch=registry.fetch, when=stamp)
    now = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda delta: (now - delta).isoformat(timespec="seconds")  # noqa: E731
    # The earlier in-period change sits halfway between the later of This week's and This
    # month's start (Monday / the 1st, 00:00 in the server's zone) and now, so it is inside
    # both periods at any hour of the run, including just after midnight on a Monday or the 1st.
    zone = zoneinfo.ZoneInfo("America/New_York")
    today = now.astimezone(zone).date()
    starts = (today - datetime.timedelta(days=today.weekday()), today.replace(day=1))
    period_start = datetime.datetime.combine(max(starts), datetime.time(0), tzinfo=zone)
    midway = now - (now - period_start) / 2
    old = datetime.timedelta(days=45)
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 100, "current": 150}, iso(old))
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 248, "current": 255}, midway.isoformat(timespec="seconds"))
    storage.mark_reviewed(conn, "NCT03412565")
    storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 255, "current": 265}, iso(datetime.timedelta(0)))
    simulate.rewind(conn, "NCT00000002", when="2026-01-02T08:00:00+00:00")
    monitor.check(conn, "NCT00000002", fetch=registry.fetch, when=iso(datetime.timedelta(0)))
    conn.close()


def open_summary(make_app, make_walk):
    app = make_app(seed=seed_summary)
    walk = make_walk(app)
    walk.page.goto(app.url)
    walk.page.get_by_role("tab", name="Summary").click()
    walk.page.locator("#summary-heading").wait_for()
    return app, walk


def numbers(page):
    heading = page.locator("#summary-heading").inner_text()
    m = re.search(r"(\d+) trials? · (\d+) field changes?", heading)
    return heading, int(m.group(1)), int(m.group(2))


def test_walk_summary_offers_three_periods_and_a_heading_with_the_period_counts_and_zone(make_app, make_walk):
    """test_walk_summary_offers_three_periods_and_a_heading_with_the_period_counts_and_zone"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    for name in ("This week", "This month", "Custom dates"):
        page.get_by_role("button", name=name).wait_for()
    assert page.get_by_role("button", name="This week").get_attribute("aria-pressed") == "true"
    heading, trials, changes = numbers(page)
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    assert str(monday.year) in heading and (trials, changes) == (2, EXPECTED_CHANGES)
    counts = page.locator("#summary-counts").inner_text()
    m = re.fullmatch(r"(\d+) awaiting review · (\d+) reviewed · Dates use E[SD]T", counts)
    assert m, counts
    assert int(m.group(1)) + int(m.group(2)) == changes and int(m.group(2)) >= 1
    walk.shot("this-week")
    page.get_by_role("button", name="This month").click()
    page.wait_for_function("() => document.querySelector('.periods button[aria-pressed=true]').innerText === 'This month'")
    assert numbers(page)[1:] == (2, EXPECTED_CHANGES)
    walk.shot("this-month")


def test_walk_custom_dates_keep_the_old_summary_until_apply_and_cancel_changes_nothing(make_app, make_walk):
    """test_walk_custom_dates_keep_the_old_summary_until_apply_and_cancel_changes_nothing"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    before = page.locator("#summary-heading").inner_text()
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").wait_for()
    page.get_by_label("To").wait_for()
    page.get_by_role("button", name="Apply").wait_for()
    page.get_by_label("From").fill("2020-02-01")
    page.get_by_label("To").fill("")
    page.get_by_role("button", name="Apply").click()
    assert "Enter both" in page.get_by_role("alert").inner_text()
    assert page.locator("#summary-heading").inner_text() == before
    page.get_by_label("To").fill("2020-01-01")
    page.get_by_role("button", name="Apply").click()
    assert "must not be after" in page.get_by_role("alert").inner_text()
    assert page.locator("#summary-heading").inner_text() == before
    walk.shot("invalid")
    page.get_by_role("button", name="Cancel").click()
    assert page.get_by_label("From").count() == 0
    assert page.locator("#summary-heading").inner_text() == before
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").fill("2020-02-01")
    page.get_by_label("To").fill("2020-02-29")
    page.get_by_role("button", name="Apply").click()
    page.locator("#summary-empty").wait_for()
    assert page.locator("#summary-heading").inner_text().startswith("1–29 Feb 2020")


def test_walk_the_summary_groups_by_trial_then_check_and_expands_to_every_transition(make_app, make_walk):
    """test_walk_the_summary_groups_by_trial_then_check_and_expands_to_every_transition"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    card = page.locator('li.card[data-nct="NCT03412565"]')
    assert card.get_by_role("heading").inner_text()
    assert "2 changes" in card.locator(".changes").inner_text()
    assert "2 checks with changes" in card.locator(".identity").inner_text()
    assert "Latest:" in card.inner_text() and "enrollment" in card.inner_text().lower()
    assert "Simulated" in page.locator('li.card[data-nct="NCT00000002"]').inner_text()
    assert "Simulated" not in card.inner_text()
    assert card.locator(".move").first.is_hidden()
    card.get_by_text("View 2 changes").click()
    moves = card.locator(".move")
    assert moves.count() == 2  # the field moved twice and is listed twice, not merged
    texts = moves.all_inner_texts()
    assert "255 (Actual) → 265 (Actual)" in texts[0] and "Awaiting review" in texts[0]
    assert "248 (Actual) → 255 (Actual)" in texts[1] and "Reviewed" in texts[1]
    sim = page.locator('li.card[data-nct="NCT00000002"]')
    sim.locator("summary").click()
    assert sim.locator(".move .simulated").count() >= 1
    walk.shot("expanded")


def test_walk_copy_summary_puts_plain_text_with_each_trials_link_on_the_clipboard(make_app, make_walk):
    """test_walk_copy_summary_puts_plain_text_with_each_trials_link_on_the_clipboard"""
    app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=app.url.rstrip("/"))
    page.get_by_role("button", name="Copy summary").click()
    page.locator("#summary-notice").wait_for()
    text = page.evaluate("() => navigator.clipboard.readText()")
    for nct in ("NCT03412565", "NCT00000002"):
        assert f"https://clinicaltrials.gov/study/{nct}" in text
    assert "<" not in text and "Enrollment" in text
    walk.shot("copied")


def test_walk_export_csv_downloads_the_file_for_the_shown_period(make_app, make_walk):
    """test_walk_export_csv_downloads_the_file_for_the_shown_period"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    _heading, _trials, changes = numbers(page)
    with page.expect_download() as info:
        page.get_by_role("button", name="Export CSV").click()
    download = info.value
    assert download.suggested_filename.startswith("myeloma-changes-") and download.suggested_filename.endswith(".csv")
    rows = list(csv.DictReader(io.StringIO(open(download.path(), encoding="utf-8").read())))
    assert len(rows) == changes  # the 45-day-old change is outside the week
    assert {r["NCT ID"] for r in rows} == {"NCT03412565", "NCT00000002"}
    assert {r["Review status"] for r in rows} == {"Reviewed", "Awaiting review"}


def test_walk_an_empty_period_says_so_keeps_the_controls_and_disables_export_with_its_reason(make_app, make_walk):
    """test_walk_an_empty_period_says_so_keeps_the_controls_and_disables_export_with_its_reason"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").fill("2020-01-01")
    page.get_by_label("To").fill("2020-01-31")
    page.get_by_role("button", name="Apply").click()
    page.locator("#summary-empty").wait_for()
    assert "No changes detected in this period." in page.locator("#summary-empty").inner_text()
    for name in ("This week", "This month", "Custom dates"):
        assert page.get_by_role("button", name=name).is_enabled()
    assert page.get_by_role("button", name="Export CSV").is_disabled()
    assert page.get_by_role("button", name="Copy summary").is_disabled()
    assert "no changes were detected" in page.locator("#export-reason").inner_text()
    assert page.locator("#summary-counts").inner_text().startswith("0 awaiting review · 0 reviewed")
    walk.shot("empty")
    page.get_by_role("button", name="Pick other dates").click()
    page.get_by_label("From").wait_for()
    page.get_by_role("button", name="Cancel").click()


def finish_a_check(app, page):
    """Run a check slowly enough to see it start, then wait for it to finish (a second check would otherwise meet the first one's message)."""
    app.registry.set("slow", True, delay=0.8)
    page.get_by_role("button", name="Check for updates").click()
    page.locator("#check-status").get_by_text("Checking for updates…").wait_for()
    page.locator("#check-status").get_by_text("Check complete").wait_for(timeout=30000)


def test_walk_a_finished_check_keeps_summary_period_and_typed_dates(make_app, make_walk):
    """test_walk_a_finished_check_keeps_summary_period_and_typed_dates"""
    app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="This month").click()
    page.wait_for_function("location.hash.includes('period=month')")
    heading = page.locator("#summary-heading").inner_text()
    counts = page.locator("#summary-counts").inner_text()
    finish_a_check(app, page)
    assert page.get_by_role("button", name="This month").get_attribute("aria-pressed") == "true"
    assert page.locator("#summary-heading").inner_text() == heading
    assert page.locator("#summary-counts").inner_text() == counts
    assert page.evaluate("location.hash").endswith("summary?period=month")
    walk.shot("month-kept")
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").fill("2026-01-05")
    finish_a_check(app, page)
    assert page.get_by_label("From").input_value() == "2026-01-05"
    assert page.get_by_role("button", name="Custom dates").get_attribute("aria-pressed") == "true"
    walk.shot("custom-kept")
