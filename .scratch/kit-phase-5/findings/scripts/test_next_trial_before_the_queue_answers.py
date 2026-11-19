from __future__ import annotations

import re

from walks.test_trial_page_walk import QUEUE_ANSWER, seed_trial_page


def test_an_enabled_next_trial_clicked_before_the_queue_answers_still_opens_the_next_trial(make_app, make_walk):
    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.locator('li.card[data-nct="NCT03412565"]').wait_for()
    held = []
    page.route(QUEUE_ANSWER, lambda route: held.append(route))
    page.locator('li.card[data-nct="NCT03412565"] h3 a').click()
    page.get_by_role("button", name="Mark reviewed").wait_for()
    assert held
    following = page.get_by_role("button", name="Next trial")
    if following.is_enabled():
        following.click()
    with page.expect_response(QUEUE_ANSWER):
        for route in held:
            route.continue_()
    page.unroute(QUEUE_ANSWER)
    if not following.is_enabled():
        return
    page.wait_for_url(re.compile(r"#/trials/NCT00000002\?list=1$"), timeout=3000)
