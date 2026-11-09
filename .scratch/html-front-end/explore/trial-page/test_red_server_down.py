"""Red: the server stops, then the analyst marks reviewed. Run:
.venv/bin/python -m pytest -p walks.conftest .scratch/html-front-end/explore/trial-page/test_red_server_down.py -q
NB the helper has no way to declare an expected network failure, so the guards also trip here; the
assertion that matters is the wording.
"""
from __future__ import annotations

from walks.test_trial_page_walk import open_trial


def test_a_stopped_server_is_told_in_words_not_failed_to_fetch(make_app, make_walk):
    """test_a_stopped_server_is_told_in_words_not_failed_to_fetch"""
    app, walk = open_trial(make_app, make_walk)
    page = walk.page
    app.proc.terminate()
    app.proc.wait(timeout=5)
    page.get_by_role("button", name="Mark reviewed").click()
    page.locator(".banner:not([hidden])").wait_for()
    walk.shot("down")
    assert "fetch" not in page.locator(".banner").inner_text().lower()
