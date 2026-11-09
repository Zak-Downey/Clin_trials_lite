"""Explore (find trials): where keyboard focus is after each redraw of the page.

Run: .venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/find-trials/test_focus_lost_after_redraw.py -q
Data: the stand-in's default three studies and "many" (134). Keyboard only: focus a control, press Enter.
A control that redraws itself away must leave focus on something in the page, not on <body>.
"""


def on_body(page):
    return page.evaluate("() => document.activeElement === document.body || document.activeElement === null")


def open_find(make_app, make_walk, hash_="#/find"):
    app = make_app()
    walk = make_walk(app)
    walk.page.goto(app.url + hash_)
    walk.page.get_by_role("heading", level=1, name="Find trials").wait_for()
    return walk


def test_explore_focus_stays_in_the_page_after_a_search_with_none_of_the_four_fields(make_app, make_walk):
    walk = open_find(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="Search trials").focus()
    page.keyboard.press("Enter")
    page.get_by_role("alert").wait_for()
    walk.shot("after-error")
    assert not on_body(page), "focus fell to the top of the page; the error is beside a field the user cannot reach by Shift+Tab from here"


def test_explore_focus_stays_in_the_page_after_next_and_previous(make_app, make_walk):
    walk = open_find(make_app, make_walk, "#/find?cond=many")
    page = walk.page
    page.get_by_text("Page 1 of 10").wait_for()
    page.get_by_role("button", name="Next").focus()
    page.keyboard.press("Enter")
    page.get_by_text("Page 2 of 10").wait_for()
    walk.shot("after-next")
    assert not on_body(page), "paging with the keyboard drops focus to the top of the page"


def test_explore_focus_stays_in_the_page_after_clear_in_the_action_bar(make_app, make_walk):
    walk = open_find(make_app, make_walk, "#/find?cond=lung")
    page = walk.page
    page.get_by_label("Select 3 on this page").focus()
    page.keyboard.press("Space")
    page.get_by_role("button", name="Clear", exact=True).focus()
    page.keyboard.press("Enter")
    page.get_by_text("selected").wait_for(state="detached")
    walk.shot("after-clear")
    assert not on_body(page), "Clear removes the action bar and drops focus to the top of the page"


def test_explore_focus_stays_in_the_page_after_add_to_a_watchlist(make_app, make_walk):
    walk = open_find(make_app, make_walk, "#/find?cond=lung")
    page = walk.page
    page.get_by_label("Select 3 on this page").focus()
    page.keyboard.press("Space")
    page.get_by_role("button", name="Add 3 trials").focus()
    page.keyboard.press("Enter")
    page.get_by_role("status").filter(has_text="added").wait_for()
    walk.shot("after-add")
    assert not on_body(page), "after Add the bar is redrawn and focus drops to the top of the page"
