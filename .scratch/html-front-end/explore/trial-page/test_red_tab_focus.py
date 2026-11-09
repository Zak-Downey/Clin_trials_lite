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
