"""Explore (find and add): an address for a page past the last one draws an empty result list.

Run: .venv/bin/python -m pytest walks/test_explore_find_and_add_page_beyond_the_last.py -q
Data: the stand-in's default three studies ("lung"): one page. Reached by a bookmark or an edited address.
"""
import pytest



@pytest.mark.xfail(strict=True, reason="todo: known defect E-037, fixed by ticket 17 of pr-1-review")
def test_explore_page_two_of_a_one_page_search_does_not_draw_an_empty_list(make_app, make_walk):
    """test_explore_page_two_of_a_one_page_search_does_not_draw_an_empty_list"""
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/find?cond=lung&page=2")
    page.get_by_role("heading", name="3 matches").wait_for()
    walk.shot("page-2-of-1")
    text = page.locator("#view").inner_text()
    assert "11–10 of 3" not in text and "Page 2 of 1" not in text, "reads '11–10 of 3 matches', 'Select 0 on this page', 'Page 2 of 1' over no results"
    assert page.locator("li.card").count() > 0, "no result is drawn although 3 match"
