from __future__ import annotations

from walks.test_trial_page_walk import QUEUE_ANSWER, seed_trial_page


def test_next_trial_does_not_say_no_trial_needs_review_when_the_queue_could_not_be_loaded(make_app, make_walk):
    app = make_app(seed=seed_trial_page)
    walk = make_walk(app)
    page = walk.page
    page.goto(app.url)
    page.locator('li.card[data-nct="NCT03412565"]').wait_for()
    walk.expect(500, "/api/watchlists/1/needs-review")
    page.route(QUEUE_ANSWER, lambda route: route.fulfill(status=500, content_type="application/json",
                                                         body='{"error": {"message": "The server failed.", "kind": "server_error"}}'))
    page.locator('li.card[data-nct="NCT03412565"] h3 a').click()
    page.wait_for_function("() => { const b = document.querySelector('.action-bar .buttons button.secondary');"
                           " return b && b.title !== 'Looking for the next trial to review'; }")
    walk.shot("queue-failed")
    following = page.get_by_role("region", name="Review").get_by_role("button", name="Next trial")
    assert following.get_attribute("title") != "No other trial needs review", \
        "the page says no other trial needs review, though it could not load the list"
