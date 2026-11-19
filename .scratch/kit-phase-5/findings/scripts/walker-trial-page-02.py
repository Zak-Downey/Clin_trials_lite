from __future__ import annotations

from walks.test_trial_page_walk import seed_trial_page


def test_undo_on_a_tab_left_open_while_another_tab_reviewed_the_trial_shows_no_script_error(make_app, make_walk):
    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + "#/trials/NCT03412565?list=1")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    other = page.context.new_page()
    other.goto(app.url + "#/trials/NCT03412565?list=1")
    other.get_by_role("button", name="Mark reviewed").click()
    other.get_by_text("5 changes marked reviewed. This trial stays open.").wait_for()
    other.close()
    page.get_by_role("button", name="Mark reviewed").click()
    undo = page.get_by_role("button", name="Undo")
    undo.wait_for()
    undo.click()
    page.wait_for_function("() => { const b = document.querySelector('.banner'); return b.hidden || !/marked reviewed/.test(b.textContent); }")
    walk.shot("after-undo")
    assert "Cannot read properties" not in page.locator("#view").inner_text(), "Undo shows a script error"
