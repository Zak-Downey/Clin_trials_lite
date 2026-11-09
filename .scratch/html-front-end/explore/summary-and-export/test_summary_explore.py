"""Exploration of Summary and export. Each test is red because of one defect.

Run from the repo root:  .venv/bin/python -m pytest .scratch/html-front-end/explore/summary-and-export/test_summary_explore.py -q
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import zoneinfo

from walks import helper
from walks.test_summary_walk import seed_summary, open_summary

NY = zoneinfo.ZoneInfo("America/New_York")
LONGWORD = "Supercalifragilisticexpialidocious" * 8


def _retitle(db, nct, title, acronym=None):
    import storage
    conn = storage.connect(db)
    for row in conn.execute("SELECT id, record FROM snapshots WHERE nct_id = ?", (nct,)).fetchall():
        rec = json.loads(row["record"]) if isinstance(row["record"], str) else row["record"]
        ident = rec["protocolSection"]["identificationModule"]
        ident["officialTitle"] = title
        ident["briefTitle"] = title
        if acronym is not None:
            ident["acronym"] = acronym
        conn.execute("UPDATE snapshots SET record = ? WHERE id = ?", (json.dumps(rec), row["id"]))
    conn.commit()
    conn.close()


def seed_formula(db, registry):
    seed_summary(db, registry)
    _retitle(db, "NCT03412565", "=HYPERLINK(\"http://evil.example\",\"click\")")


def seed_long(db, registry):
    seed_summary(db, registry)
    _retitle(db, "NCT03412565", LONGWORD, acronym=LONGWORD)


def seed_boundary(db, registry):
    import monitor
    import storage
    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT03412565", first, fetch=registry.fetch, when="2026-01-01T08:00:00+00:00")
    today = datetime.datetime.now(NY).date()
    monday = today - datetime.timedelta(days=today.weekday())
    at = lambda d, h, m, s: datetime.datetime(d.year, d.month, d.day, h, m, s, tzinfo=NY).astimezone(datetime.timezone.utc).isoformat(timespec="seconds")  # noqa: E731
    sunday = monday + datetime.timedelta(days=6)
    for value, stamp in ((1001, at(monday - datetime.timedelta(days=1), 23, 59, 50)),
                         (1002, at(monday, 0, 0, 10)),
                         (1003, at(sunday, 23, 59, 50)),
                         (1004, at(sunday + datetime.timedelta(days=1), 0, 0, 10))):
        storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": 1, "current": value}, stamp)
    conn.close()


def seed_many(db, registry):
    import monitor
    import storage
    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]
    monitor.add(conn, "NCT03412565", first, fetch=registry.fetch, when="2026-01-01T08:00:00+00:00")
    now = datetime.datetime.now(datetime.timezone.utc)
    for i in range(400):
        stamp = (now - datetime.timedelta(minutes=i)).isoformat(timespec="seconds")
        storage.add_change(conn, "NCT03412565", {"field": "enrollment", "previous": i, "current": i + 1}, stamp)
    conn.close()


def focus_desc(page):
    return page.evaluate("() => { const a = document.activeElement; return a ? a.tagName + ':' + (a.innerText || a.id || '').slice(0, 30) : 'none'; }")


def test_csv_cell_that_begins_with_equals_is_not_left_as_a_spreadsheet_formula(make_app, make_walk):
    """test_csv_cell_that_begins_with_equals_is_not_left_as_a_spreadsheet_formula"""
    _app, walk = open_summary(lambda seed: make_app(seed=seed_formula), make_walk)
    page = walk.page
    with page.expect_download() as info:
        page.get_by_role("button", name="Export CSV").click()
    rows = list(csv.DictReader(io.StringIO(open(info.value.path(), encoding="utf-8").read())))
    walk.shot("formula-title")
    titles = {r["Title"] for r in rows if r["NCT ID"] == "NCT03412565"}
    assert titles and not any(t[:1] in "=+-@" for t in titles), titles


def test_a_long_unbroken_title_does_not_push_the_summary_sideways(make_app, make_walk):
    """test_a_long_unbroken_title_does_not_push_the_summary_sideways"""
    _app, walk = open_summary(lambda seed: make_app(seed=seed_long), make_walk)
    walk.shot("long-title")  # the sideways-scroll guard measures here


def test_keyboard_user_keeps_focus_on_the_period_button_they_pressed(make_app, make_walk):
    """test_keyboard_user_keeps_focus_on_the_period_button_they_pressed"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="This month").focus()
    page.keyboard.press("Enter")
    page.wait_for_function("() => document.querySelector('.periods button[aria-pressed=true]').innerText === 'This month'")
    walk.shot("after-month")
    assert focus_desc(page) == "BUTTON:This month", focus_desc(page)


def test_focus_after_copy_summary_stays_on_the_button(make_app, make_walk):
    """test_focus_after_copy_summary_stays_on_the_button"""
    app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=app.url.rstrip("/"))
    page.get_by_role("button", name="Copy summary").focus()
    page.keyboard.press("Enter")
    page.locator("#summary-notice").wait_for()
    walk.shot("after-copy")
    assert focus_desc(page) == "BUTTON:Copy summary", focus_desc(page)


def test_copy_summary_does_not_collapse_the_open_trial(make_app, make_walk):
    """test_copy_summary_does_not_collapse_the_open_trial"""
    app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=app.url.rstrip("/"))
    card = page.locator('li.card[data-nct="NCT03412565"]')
    card.get_by_text("View 2 changes").click()
    page.get_by_role("button", name="Copy summary").click()
    page.locator("#summary-notice").wait_for()
    walk.shot("after-copy")
    assert card.locator(".move").first.is_visible(), "the expanded trial collapsed"


def test_copy_summary_does_not_wipe_dates_typed_in_the_open_form(make_app, make_walk):
    """test_copy_summary_does_not_wipe_dates_typed_in_the_open_form"""
    app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=app.url.rstrip("/"))
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").fill("2026-02-01")
    page.get_by_role("button", name="Copy summary").click()
    page.locator("#summary-notice").wait_for()
    walk.shot("after-copy-with-form")
    assert page.get_by_label("From").input_value() == "2026-02-01", "the typed From date was wiped"


def test_opening_custom_dates_puts_the_keyboard_in_the_form(make_app, make_walk):
    """test_opening_custom_dates_puts_the_keyboard_in_the_form"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Custom dates").focus()
    page.keyboard.press("Enter")
    page.get_by_label("From").wait_for()
    walk.shot("custom-opened")
    assert focus_desc(page).startswith(("INPUT", "BUTTON:Custom")), focus_desc(page)


def test_cancel_and_apply_leave_the_keyboard_somewhere_sensible(make_app, make_walk):
    """test_cancel_and_apply_leave_the_keyboard_somewhere_sensible"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_role("button", name="Cancel").focus()
    page.keyboard.press("Enter")
    page.wait_for_function("() => !document.querySelector('#summary-from')")
    walk.shot("after-cancel")
    assert focus_desc(page) != "BODY" and not focus_desc(page).startswith("BODY"), focus_desc(page)


def test_empty_period_offer_keeps_the_keyboard_on_the_page(make_app, make_walk):
    """test_empty_period_offer_keeps_the_keyboard_on_the_page"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").fill("2020-01-01")
    page.get_by_label("To").fill("2020-01-31")
    page.get_by_role("button", name="Apply").focus()
    page.keyboard.press("Enter")
    page.locator("#summary-empty").wait_for()
    walk.shot("after-apply")
    assert not focus_desc(page).startswith("BODY"), focus_desc(page)


def test_a_hand_edited_address_with_bad_custom_dates_still_opens_the_summary(make_app, make_walk):
    """test_a_hand_edited_address_with_bad_custom_dates_still_opens_the_summary"""
    app = make_app(seed=seed_summary)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("tab", name="Summary").click()
    page.locator("#summary-heading").wait_for()
    url = page.url.split("#")[0]
    walk.expect(400, "/api/watchlists/1/summary")
    page.goto(url + "#/watchlists/1/summary?period=custom&from=abc&to=def")
    page.reload()
    page.wait_for_timeout(1500)
    walk.shot("bad-hash")
    assert page.locator("#summary-heading").count() == 1, page.inner_text("body")[:300]


def test_two_quick_period_clicks_end_on_the_last_one_clicked(make_app, make_walk):
    """test_two_quick_period_clicks_end_on_the_last_one_clicked"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    delays = iter([800, 0])

    def slow(route):
        import time
        time.sleep(next(delays, 0) / 1000)
        route.continue_()
    # the first request to leave is the slow one, the second is quick
    page.route("**/summary?period=month", lambda r: (__import__("time").sleep(0.8), r.continue_()))
    page.get_by_role("button", name="This month").click()
    page.get_by_role("button", name="This week").click()
    page.wait_for_timeout(2000)
    walk.shot("after-race")
    pressed = page.locator(".periods button[aria-pressed=true]").inner_text()
    heading = page.locator("#summary-heading").inner_text()
    assert pressed == "This week" and not heading.startswith("1–30 Nov"), (pressed, heading)


def test_custom_dates_pressed_state_is_one_choice_not_two(make_app, make_walk):
    """test_custom_dates_pressed_state_is_one_choice_not_two"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Custom dates").click()
    page.get_by_label("From").wait_for()
    walk.shot("custom-open")
    assert page.locator(".periods button[aria-pressed=true]").count() == 1


def test_week_runs_monday_to_sunday_in_the_machines_zone_to_the_second(make_app, make_walk):
    """test_week_runs_monday_to_sunday_in_the_machines_zone_to_the_second"""
    app = make_app(seed=seed_boundary)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("tab", name="Summary").click()
    page.locator("#summary-heading").wait_for()
    walk.shot("boundary")
    with page.expect_download() as info:
        page.get_by_role("button", name="Export CSV").click()
    rows = list(csv.DictReader(io.StringIO(open(info.value.path(), encoding="utf-8").read())))
    assert sorted(r["New value"].split(" ")[0] for r in rows) == ["1002", "1003"], [(r["New value"], r["Detected"]) for r in rows]


def test_four_hundred_changes_draw_and_export_all_of_them(make_app, make_walk):
    """test_four_hundred_changes_draw_and_export_all_of_them"""
    app = make_app(seed=seed_many)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.get_by_role("tab", name="Summary").click()
    page.locator("#summary-heading").wait_for()
    walk.shot("many")
    heading = page.locator("#summary-heading").inner_text()
    with page.expect_download() as info:
        page.get_by_role("button", name="Export CSV").click()
    rows = list(csv.DictReader(io.StringIO(open(info.value.path(), encoding="utf-8").read())))
    assert f"{len(rows)} field changes" in heading, (heading, len(rows))


def test_server_gone_mid_action_says_so_and_keeps_the_page(make_app, make_walk):
    """test_server_gone_mid_action_says_so_and_keeps_the_page"""
    app, walk = open_summary(make_app, make_walk)
    page = walk.page
    app.proc.terminate()
    app.proc.wait(timeout=5)
    page.get_by_role("button", name="This month").click()
    page.wait_for_timeout(1500)
    walk.shot("server-gone")
    assert page.locator("#summary-heading").count() == 1 and page.locator("#summary-notice").count() == 1


def test_copy_refused_by_the_browser_gives_a_way_forward(make_app, make_walk):
    """test_copy_refused_by_the_browser_gives_a_way_forward"""
    _app, walk = open_summary(make_app, make_walk)
    page = walk.page
    page.evaluate("() => { Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('denied'))}, configurable: true}); }")
    page.get_by_role("button", name="Copy summary").click()
    page.locator("#summary-notice").wait_for()
    walk.shot("copy-refused")
    note = page.locator("#summary-notice").inner_text()
    # the advice must point at something that exists on the page
    assert "Select it from the export" not in note, note
