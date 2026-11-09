"""Explore (find and add): a refused page number is shown as a registry failure with a Retry that cannot succeed.

Run: .venv/bin/python -m pytest walks/test_explore_find_and_add_page_out_of_range_is_not_a_registry_error.py -q
Data: the stand-in's "many" search. Same shape as F11 (a refusal read as registry_error), for the third refusal kind, bad_page.
"""
import pytest



@pytest.mark.xfail(strict=True, reason="todo: known defect E-036, fixed by ticket 17 of pr-1-review")
def test_explore_page_11_is_a_refusal_with_no_retry_and_keeps_the_query_in_the_form(make_app, make_walk):
    """test_explore_page_11_is_a_refusal_with_no_retry_and_keeps_the_query_in_the_form"""
    app = make_app()
    walk = make_walk(app)
    page = walk.page
    walk.expect(400, "/api/search")
    page.goto(app.url + "#/find?cond=many&page=11")
    page.get_by_text("Page must be a number from 1 to 10.").wait_for()
    walk.shot("page-11")
    assert page.get_by_role("button", name="Retry").count() == 0, "Retry re-sends the same refused page"
    assert page.get_by_label("Condition").input_value() == "many", "the form is empty although the address names a query"
