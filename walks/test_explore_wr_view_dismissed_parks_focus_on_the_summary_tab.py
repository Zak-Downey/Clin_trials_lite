"""Explore: View dismissed and Back to new matches leave keyboard focus on the Summary tab.

Data: walks/test_new_matches_walk.py's seed (twelve offered matches, one saved search). Lacks: a screen reader.
Run: .venv/bin/python -m pytest walks/test_explore_wr_view_dismissed_parks_focus_on_the_summary_tab.py -q
"""
import pytest


from walks import test_new_matches_walk as nm


def in_tab_strip(page):
    return page.evaluate("!!document.activeElement.closest('nav.tabs')")



def test_walk_view_dismissed_and_back_to_new_matches_do_not_leave_focus_on_a_tab(make_app, make_walk):
    _, walk = nm.open_tab(make_app, make_walk)
    page = walk.page
    page.locator("#view-dismissed").focus()
    page.keyboard.press("Enter")
    page.locator("#back-to-matches").wait_for()
    page.wait_for_timeout(600)
    walk.shot("view-dismissed")
    assert not in_tab_strip(page), "after View dismissed, focus is on a tab (Enter now leaves the list)"
    page.locator("#back-to-matches").focus()
    page.keyboard.press("Enter")
    page.locator("#view-dismissed").wait_for()
    page.wait_for_timeout(600)
    walk.shot("back")
    assert not in_tab_strip(page), "after Back to new matches, focus is on a tab"
