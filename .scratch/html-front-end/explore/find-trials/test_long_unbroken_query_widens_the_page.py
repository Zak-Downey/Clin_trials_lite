"""Explore (find trials): the longest query, one word with no spaces (a pasted code or URL).

Run: .venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/find-trials/test_long_unbroken_query_widens_the_page.py -q
Data: the stand-in's default studies. Red through the walk guard (sideways scrolling of the page).
"""


def test_explore_a_600_character_condition_does_not_scroll_the_page_sideways(make_app, make_walk):
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/find")
    page.get_by_label("Condition").fill("x" * 600)
    page.get_by_label("Condition").press("Enter")
    page.get_by_role("button", name="Edit search").wait_for()
    walk.shot("long-summary")
    wide = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert wide <= 0, f"the page is {wide}px wider than the window"
