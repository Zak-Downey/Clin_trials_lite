"""Explore: a double click on Mark reviewed leaves an Undo that cannot undo.

Data: helper.seed_queue (NCT00000002 has three unreviewed changes). Lacks: a trial in two lists.
Run: .venv/bin/python -m pytest walks/test_explore_wr_double_click_mark_reviewed_leaves_an_undo_that_fails.py -q
"""
from walks import helper


def test_walk_undo_after_a_double_click_on_mark_reviewed_still_undoes_the_review(make_app, make_walk):
    """test_walk_undo_after_a_double_click_on_mark_reviewed_still_undoes_the_review: one request, a working Undo."""
    app = make_app(seed=helper.seed_queue)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/trials/NCT00000002")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    page.get_by_role("button", name="Mark reviewed").dblclick()
    undo = page.get_by_role("button", name="Undo")
    undo.first.wait_for()
    page.wait_for_timeout(500)  # both answers have come back
    undo.first.click()
    page.wait_for_timeout(500)
    walk.shot("after-undo")
    assert "Cannot read properties" not in page.locator("#view").inner_text(), "Undo shows a script error"
    assert page.get_by_role("button", name="Mark reviewed").is_enabled(), "Undo did not undo: the trial is still reviewed"
