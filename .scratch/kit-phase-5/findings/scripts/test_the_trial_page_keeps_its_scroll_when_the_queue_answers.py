from __future__ import annotations

from walks.test_trial_page_walk import QUEUE_ANSWER, seed_trial_page


def open_with_the_queue_held(make_app, make_walk):
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
    return page, held


def release(page, held):
    with page.expect_response(QUEUE_ANSWER):
        for route in held:
            route.continue_()
    page.unroute(QUEUE_ANSWER)
    page.wait_for_function("() => !document.querySelector('.action-bar .buttons button.secondary').title.startsWith('Looking')")


def test_a_person_scrolled_down_stays_where_they_are_when_the_queue_answers(make_app, make_walk):
    page, held = open_with_the_queue_held(make_app, make_walk)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    before = page.evaluate("scrollY")
    assert before > 0
    release(page, held)
    assert page.evaluate("scrollY") == before


def test_the_action_bar_walk_s_reads_hold_when_the_queue_answers_between_its_scroll_and_its_read(make_app, make_walk):
    page, held = open_with_the_queue_held(make_app, make_walk)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    release(page, held)
    bar = page.get_by_role("region", name="Review")
    last = page.locator("article.change").last.bounding_box()
    assert last["y"] + last["height"] <= bar.bounding_box()["y"] + 1
