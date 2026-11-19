from __future__ import annotations

from walks.test_trial_page_walk import open_trial_with_the_queue_held, release

NEXT_SETTLED = "() => document.querySelector('.action-bar .buttons button.secondary').title !== 'Looking for the next trial to review'"


def test_the_page_stays_where_the_reader_scrolled_when_the_watchlist_s_queue_answers(make_app, make_walk):
    walk, held = open_trial_with_the_queue_held(make_app, make_walk)
    page = walk.page
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_function("() => window.scrollY > 0")
    page.get_by_role("button", name="Mark reviewed").click()
    page.get_by_text("5 changes marked reviewed. This trial stays open.").wait_for()
    where = page.evaluate("window.scrollY")
    release(page, held)
    page.wait_for_function(NEXT_SETTLED)
    walk.shot("after-the-queue")
    assert page.evaluate("window.scrollY") == where, "the page jumped to the top when the watchlist's queue answered"
