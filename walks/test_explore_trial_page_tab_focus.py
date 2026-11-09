"""Red: focus after a tab switch. Run:
.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/trial-page/test_red_tab_focus.py -q
"""
from __future__ import annotations

from walks.test_trial_page_walk import open_trial


def test_choosing_a_trial_tab_by_keyboard_leaves_focus_in_the_tab_strip(make_app, make_walk):
    """test_choosing_a_trial_tab_by_keyboard_leaves_focus_in_the_tab_strip"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    page.get_by_role("tab", name="History").focus()
    page.keyboard.press("Enter")
    page.get_by_role("heading", name="Trial history").wait_for()
    walk.shot("history")
    assert page.evaluate("document.activeElement.tagName") != "BODY"


def test_opening_a_trial_from_the_queue_by_keyboard_does_not_throw_focus_onto_a_tab(make_app, make_walk):
    """test_opening_a_trial_from_the_queue_by_keyboard_does_not_throw_focus_onto_a_tab"""
    from walks.test_trial_page_walk import seed_trial_page

    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    link = page.locator('li.card[data-nct="NCT03412565"] h3 a')
    link.focus()
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    page.wait_for_timeout(500)
    # Focus is kept across a redraw of the same page, never carried to a control of the page just opened
    # (here the Changes tab shares the title link's address).
    assert page.evaluate("document.activeElement.getAttribute('role')") != "tab"
