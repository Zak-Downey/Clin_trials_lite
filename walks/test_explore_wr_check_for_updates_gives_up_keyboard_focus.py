"""Explore: pressing Enter on Check for updates moves keyboard focus to Add trials.

Data: helper.seed_queue. Lacks: a screen reader (which may announce the busy state differently).
Run: .venv/bin/python -m pytest walks/test_explore_wr_check_for_updates_gives_up_keyboard_focus.py -q
"""
import pytest


from walks import helper


def focused(page):
    return page.evaluate("document.activeElement.id || document.activeElement.textContent.trim().slice(0, 30)")


@pytest.mark.xfail(strict=True, reason="todo: known defect E-031, fixed by ticket 14 of pr-1-review")
def test_walk_check_for_updates_keeps_keyboard_focus_while_it_runs_and_after(make_app, make_walk):
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/watchlists/1/needs-review")
    button = page.get_by_role("button", name="Check for updates")
    button.wait_for()
    app.registry.set("slow", True, delay=1)
    button.focus()
    page.keyboard.press("Enter")
    page.get_by_text("Checking for updates…").wait_for()
    page.wait_for_timeout(500)
    walk.shot("running")
    assert focused(page) == "check-button", f"focus moved to {focused(page)!r} while the check ran: a second Enter opens it"
    page.get_by_text("Check complete").wait_for()
    page.wait_for_timeout(600)
    walk.shot("complete")
    assert focused(page) == "check-button", f"focus is on {focused(page)!r} after the check finished"
