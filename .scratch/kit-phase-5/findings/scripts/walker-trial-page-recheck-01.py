from __future__ import annotations

from walks.test_trial_page_walk import FILLERS, seed_trial_page

ONE = FILLERS[0]

REVIEW_IN_ANOTHER_TAB = """async (nct) => {
  const trial = await (await fetch(`/api/trials/${nct}`)).json();
  const ids = trial.groups.flatMap((g) => g.changes).flatMap((c) => c.ids);
  await fetch(`/api/trials/${nct}/review`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids }) });
}"""


def test_mark_reviewed_on_one_change_another_tab_already_reviewed_says_it_in_the_singular(make_app, make_walk):
    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url + f"#/trials/{ONE}?list=1")
    page.get_by_role("button", name="Mark reviewed").wait_for()
    other = page.context.new_page()
    other.goto(app.url)
    other.evaluate(REVIEW_IN_ANOTHER_TAB, ONE)
    other.close()
    page.get_by_role("button", name="Mark reviewed").click()
    banner = page.locator(".banner")
    page.wait_for_function("() => /already reviewed/.test(document.querySelector('.banner').textContent)")
    walk.shot("one-already-reviewed")
    text = banner.inner_text()
    assert "These 1 changes" not in text, f"the page says: {text!r}"
    assert "1 change" in text or "This change" in text, f"the page says: {text!r}"
