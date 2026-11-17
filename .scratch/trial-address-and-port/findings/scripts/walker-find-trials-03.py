"""walker-find-trials-03: pressing "Add to watchlist" from the keyboard moves focus back to the "Add to" picker.

Red now: the button is disabled while the add is saved, focus falls off it, and the page's
focus keeper puts it on the picker beside it. Green once focus is on the button (or on
"Open the trial") after the outcome appears.
"""
from walks.test_trial_address_walk import seed_two_queues


def test_focus_stays_on_add_after_adding_by_keyboard(make_app, make_walk):
    app = make_app(seed=seed_two_queues)
    walk = make_walk(app)
    page = walk.page
    page.goto(f"{app.url}#/registry/NCT00000003")
    add = page.get_by_role("button", name="Add to watchlist")
    add.wait_for()
    add.focus()
    page.keyboard.press("Enter")
    page.get_by_text("Added to").wait_for()
    page.wait_for_timeout(300)
    walk.shot("after-add")
    where = page.evaluate("document.activeElement.textContent.trim().slice(0, 40)")
    assert where in ("Add to watchlist", "Open the trial"), f"focus is on {where!r}"
