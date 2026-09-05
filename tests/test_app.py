"""The page itself, driven through Streamlit's app-test harness.

The database is seeded through the fetching seam first, so rendering the page
never touches the network.
"""

from __future__ import annotations

import pathlib
import urllib.error

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


def test_checking_a_clean_watchlist_reports_no_changes(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="check_all").click().run()

    assert not app.exception
    assert any("no changes" in msg.value for msg in app.success)


def test_a_trial_that_fails_to_check_is_reported_inline(app, fetcher, make_fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(
        monitor,
        "_default_fetch",
        make_fetcher(failures={"NCT03412565": urllib.error.URLError("connection refused")}),
    )

    app.run()
    app.button(key="check_all").click().run()

    assert not app.exception
    assert any("connection refused" in err.value for err in app.error)
    assert not app.success


def test_an_empty_watchlist_offers_no_check_control(app):
    app.run()

    assert not app.exception
    assert not [b for b in app.button if b.label == "Check all"]


# --- the developer-only simulator


def test_the_developer_tools_are_labelled_as_synthetic(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    labels = " ".join(exp.label for exp in app.expander).lower()
    assert "developer" in labels
    assert "synthetic" in labels


def test_simulating_a_change_and_checking_shows_it_in_the_feed(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    assert "3 fields changed" in rendered


def test_simulated_data_is_badged_wherever_it_appears(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()

    # Badged on the watchlist row while the stored profile is the fabricated one.
    row = [exp.label for exp in app.expander if "NCT03412565" in exp.label]
    assert row and display.SYNTHETIC in row[0]

    app.button(key="check_all").click().run()

    # And on the feed entry for the change it caused.
    assert display.SYNTHETIC in " ".join(m.value for m in app.markdown)


def test_deleting_synthetic_data_clears_it_from_the_page(app, fetcher, monkeypatch):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    app.button(key="delete_synthetic").click().run()

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    assert "fields changed" not in rendered
    assert display.SYNTHETIC not in rendered
    # The trial itself is real, and stays.
    assert any("NCT03412565" in exp.label for exp in app.expander)


def test_simulating_is_offered_only_once_a_trial_is_watched(app):
    app.run()

    assert not app.exception
    assert not [b for b in app.button if b.key == "simulate"]
