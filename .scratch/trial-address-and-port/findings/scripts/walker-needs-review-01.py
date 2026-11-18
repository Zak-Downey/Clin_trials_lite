"""walker-needs-review-01: "Back to" from a trial opened on Summary drops the period the analyst chose.

Data: walks/test_summary_walk.py's seed ("Myeloma", id 1). Before this build the trial page's
"Back to" link returned to the Summary address the analyst left, period included; now it names
the bare Summary tab, which opens on This week.
"""
from walks import test_summary_walk as summary_seed


def test_back_to_from_a_summary_trial_keeps_the_chosen_period(make_app, make_walk):
    _, walk = summary_seed.open_summary(make_app, make_walk)
    page = walk.page
    page.get_by_role("button", name="This month").click()
    page.wait_for_function("location.hash.includes('period=month')")
    page.locator('li.card.trial[data-nct="NCT03412565"] h3 a').click()
    page.get_by_role("link", name="‹ Back to Myeloma").click()
    page.locator("#summary-heading").wait_for()
    walk.shot("summary-after-back")
    assert page.get_by_role("button", name="This month").get_attribute("aria-pressed") == "true", \
        "Summary came back on This week, not the This month the analyst left"
    assert page.evaluate("location.hash").endswith("summary?period=month")
