"""Red: the trial page's actions menu and the keyboard. Run:
.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/trial-page/test_red_menu_keyboard.py -q
"""
from __future__ import annotations

from walks.test_trial_page_walk import open_trial


def open_menu_by_keyboard(page):
    page.get_by_role("button", name="More actions").focus()
    page.keyboard.press("Enter")
    page.get_by_role("menu").wait_for()


def test_escape_closes_the_menu_while_focus_is_still_on_its_button(make_app, make_walk):
    """test_escape_closes_the_menu_while_focus_is_still_on_its_button"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    open_menu_by_keyboard(page)
    walk.shot("open")
    page.keyboard.press("Escape")
    walk.shot("after-escape")
    assert not page.get_by_role("menu").is_visible()


def test_tabbing_out_of_the_open_menu_closes_it(make_app, make_walk):
    """test_tabbing_out_of_the_open_menu_closes_it"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    open_menu_by_keyboard(page)
    for _ in range(4):
        page.keyboard.press("Tab")
    walk.shot("tabbed-away")
    assert not page.get_by_role("menu").is_visible()


def test_focus_is_not_dropped_to_the_page_after_remove_from_this_list(make_app, make_walk):
    """test_focus_is_not_dropped_to_the_page_after_remove_from_this_list"""
    _, walk = open_trial(make_app, make_walk)
    page = walk.page
    open_menu_by_keyboard(page)
    page.get_by_role("menuitem", name="Remove from this list").focus()
    page.keyboard.press("Enter")
    page.get_by_text("Removed from Myeloma.").wait_for()
    walk.shot("removed")
    assert page.evaluate("document.activeElement.tagName") != "BODY"
