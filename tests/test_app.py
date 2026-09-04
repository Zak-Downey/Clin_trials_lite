"""The page itself, driven through Streamlit's app-test harness.

The database is seeded through the fetching seam first, so rendering the page
never touches the network.
"""

from __future__ import annotations

import pathlib

import pytest
from streamlit.testing.v1 import AppTest

import display
import monitor
import storage

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", str(tmp_path / "app.db"))
    return AppTest.from_file(APP, default_timeout=30)


def test_the_page_renders_an_empty_watchlist(app):
    app.run()

    assert not app.exception
    assert "Trial Change Monitor" in app.title[0].value
    assert any("Nothing monitored yet" in info.value for info in app.info)


def test_a_watched_trial_renders_with_its_headline_facts(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    assert not app.exception
    labels = " ".join(exp.label for exp in app.expander)
    assert "NCT03412565" in labels
    assert "Janssen Research & Development, LLC" in labels
    assert "COMPLETED" in labels


def test_the_expanded_row_shows_every_monitored_field(app, fetcher):
    conn = storage.connect()
    monitor.add(conn, "NCT03412565", fetch=fetcher)
    expected = monitor.profile_of(conn, "NCT03412565")

    app.run()

    rendered = " ".join(m.value for m in app.markdown)
    missing = [k for k in expected if display.label(k) not in rendered]
    assert not missing


def test_the_feed_shows_the_started_monitoring_entry(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    rendered = " ".join(m.value for m in app.markdown)
    assert "started monitoring" in rendered


def test_an_empty_submission_is_reported_inline(app):
    app.run()
    app.button[0].click().run()

    assert not app.exception
    assert any("Paste an NCT ID" in err.value for err in app.error)
