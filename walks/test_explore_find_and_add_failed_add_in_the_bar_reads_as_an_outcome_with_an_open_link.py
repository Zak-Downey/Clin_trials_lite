"""Explore (find and add): every add failing is reported as a status with an "Open <list>" link and no reason.

Run: .venv/bin/python -m pytest walks/test_explore_find_and_add_failed_add_in_the_bar_reads_as_an_outcome_with_an_open_link.py -q
Data: ticket 08's seed (Myeloma, Elsewhere), the stand-in's "many" search and its server_error switch.
F9 made Add by NCT ID and trial details show a failed add as an error beside the control. The results bar
still shows "0 added; 1 could not be added (NCT...)" in role=status, with a link inviting the analyst to
open a watchlist that gained nothing, no reason, and no Add button until Dismiss.
"""
import pytest

from walks.test_find_select_walk import box, results


@pytest.mark.xfail(strict=True, reason="todo: known defect E-034, fixed by ticket 16 of pr-1-review")
def test_explore_a_wholly_failed_add_in_the_bar_is_an_error_with_a_reason_and_no_open_link(make_app, make_walk):
    """test_explore_a_wholly_failed_add_in_the_bar_is_an_error_with_a_reason_and_no_open_link"""
    app, walk = results(make_app, make_walk)
    page = walk.page
    app.registry.set("server_error", True)
    box(page, "NCT10000001").check()
    page.get_by_role("button", name="Add 1 trial").click()
    page.get_by_text("could not be added").wait_for()
    walk.shot("all-failed")
    bar = page.get_by_role("region", name="Add selected trials")
    assert bar.get_by_role("link", name="Open Myeloma").count() == 0, "an Open link to a list that gained nothing"
    assert bar.get_by_role("alert").count() == 1, "a failure is announced as a status, not an error"
    assert "500" in bar.inner_text() or "error" in bar.inner_text().lower(), "no reason is given"
