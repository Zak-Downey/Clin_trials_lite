"""Explore (find and add): the failure sentence of Add by NCT ID stays after the ID is changed.

Run: .venv/bin/python -m pytest walks/test_explore_find_and_add_error_after_a_failed_add_by_id_outlives_the_edit.py -q
Data: a fresh database and the stand-in's NCT00000002. Cosmetic.
"""
import pytest



@pytest.mark.xfail(strict=True, reason="todo: known defect E-035, fixed by ticket 16 of pr-1-review")
def test_explore_the_add_error_is_cleared_when_the_id_is_edited(make_app, make_walk):
    """test_explore_the_add_error_is_cleared_when_the_id_is_edited"""
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/find/id")
    page.get_by_label("NCT ID").fill("NCT00000002")
    page.get_by_role("button", name="Look up trial").click()
    page.get_by_role("button", name="Add to watchlist").wait_for()
    app.registry.set("server_error", True)
    page.get_by_role("button", name="Add to watchlist").click()
    page.get_by_text("ClinicalTrials.gov returned an error for NCT00000002").wait_for()
    page.get_by_label("NCT ID").fill("NCT0000000")
    walk.shot("edited")
    assert page.get_by_text("returned an error for NCT00000002").count() == 0, "the sentence about NCT00000002 stays beside a different ID"
