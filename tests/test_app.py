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


def watchlist(app) -> list[dict]:
    """The rendered watchlist table, one dict per line."""
    return app.dataframe[0].value.to_dict("records")


def open_profile(app, index: int = 0):
    """Select a watchlist line so its profile renders below the table.

    The harness clears the table's selection at the start of every run, so the
    selection is set once for the run that opens the profile and again for
    whatever run follows, which is how a control inside the profile stays
    clickable.
    """

    def hold():
        app.session_state["watchlist"] = {"selection": {"rows": [index], "columns": []}}

    hold()
    app.run()
    hold()
    return app


def test_the_page_renders_an_empty_watchlist(app):
    app.run()

    assert not app.exception
    assert "Trial Change Monitor" in app.title[0].value
    assert any("Nothing monitored yet" in info.value for info in app.info)


def test_a_watched_trial_gets_one_line_carrying_what_identifies_the_study(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    assert not app.exception
    lines = watchlist(app)
    assert len(lines) == 1
    assert lines[0]["NCT ID"] == "NCT03412565"
    assert lines[0]["Sponsor"] == "Janssen Research & Development, LLC"
    assert lines[0]["Trial status"] == "Completed"
    assert lines[0]["Official title"]
    assert lines[0]["Phase"] == "Phase 2"
    assert lines[0]["Conditions"]
    assert lines[0]["Interventions"]


def test_a_trial_that_has_never_changed_says_so_on_its_line(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    line = watchlist(app)[0]
    assert line["What changed"] == display.EMPTY
    assert line["Changed on"] is None


def test_the_selected_row_shows_every_monitored_field(app, fetcher):
    conn = storage.connect()
    monitor.add(conn, "NCT03412565", fetch=fetcher)
    expected = monitor.profile_of(conn, "NCT03412565")

    app.run()
    open_profile(app)

    rendered = " ".join(m.value for m in app.markdown)
    missing = [k for k in expected if display.label(k) not in rendered]
    assert not missing


def test_an_opened_trial_reads_as_titled_cards(app, fetcher):
    """The dossier: every card the profile fills is on the page, titled."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()
    open_profile(app)

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    for title, _ in display.CARDS:
        assert title.upper() in rendered


def test_each_card_costs_the_page_a_single_block(app, fetcher):
    """The density win. A card drawn field by field would be as tall as the
    stack it replaces, because Streamlit margins every block it draws."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()
    open_profile(app)

    titles = [t.upper() for t, _ in display.CARDS]
    cards = [m.value for m in app.markdown if m.value.startswith(tuple(f"**{t}" for t in titles))]
    assert len(cards) == len(titles)
    # Every field of the profile is inside one of those blocks, not beside them.
    fields = monitor.profile_of(storage.connect(), "NCT03412565")
    dossier = " ".join(cards)
    assert not [k for k in fields if display.label(k) not in dossier]


def test_reviewing_clears_the_counts_from_the_card_titles(app, fetcher, monkeypatch):
    """The bell counts what is unread, not what has ever moved."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    open_profile(app)
    assert display.UNREVIEWED in " ".join(m.value for m in app.markdown)

    app.button(key="review_NCT03412565").click().run()
    open_profile(app)

    assert not app.exception
    titles = [m.value for m in app.markdown if m.value.startswith("**")]
    assert titles
    assert not [t for t in titles if display.UNREVIEWED in t]


def test_no_profile_is_shown_until_a_row_is_selected(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()

    assert "Enrollment" not in " ".join(m.value for m in app.markdown)


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

    # Badged on the watchlist line while the stored profile is the fabricated one.
    assert display.SYNTHETIC_MARK in watchlist(app)[0]["NCT ID"]

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
    assert display.SYNTHETIC_MARK not in rendered
    # The trial itself is real, and stays.
    assert watchlist(app)[0]["NCT ID"] == "NCT03412565"


def test_simulating_is_offered_only_once_a_trial_is_watched(app):
    app.run()

    assert not app.exception
    assert not [b for b in app.button if b.key == "simulate"]


# --- seeing what moved


def test_a_changed_trial_shows_the_moved_field_highlighted_in_its_profile(
    app, fetcher, monkeypatch
):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)

    app.run()
    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    open_profile(app)

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    # The whole profile is still there, with the moved fields marked up.
    assert "Official title" in rendered
    assert display.HIGHLIGHT_HIGH_SIGNAL in rendered
    assert "Previously" in rendered


def test_an_unchanged_trial_opens_to_a_plain_profile(app, fetcher):
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)

    app.run()
    open_profile(app)

    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    assert "Enrollment" in rendered
    assert display.HIGHLIGHT not in rendered
    assert display.HIGHLIGHT_HIGH_SIGNAL not in rendered


# --- marking a trial reviewed


@pytest.fixture
def live(app, fetcher, monkeypatch):
    """The page with one watched trial, and the check button wired to the stub."""
    monitor.add(storage.connect(), "NCT03412565", fetch=fetcher)
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()
    return app


def highlighted(app) -> bool:
    rendered = " ".join(m.value for m in app.markdown)
    return display.HIGHLIGHT_HIGH_SIGNAL in rendered or display.HIGHLIGHT in rendered


def test_a_trial_with_no_unreviewed_changes_offers_no_review_control(live):
    open_profile(live)

    assert not [b for b in live.button if b.key == "review_NCT03412565"]


def test_the_whole_loop_from_adding_to_reviewing_and_changing_again_is_walkable(
    app, fetcher, monkeypatch
):
    """Every step taken through the page, as the analyst takes them."""
    monkeypatch.setattr(monitor, "_default_fetch", fetcher)
    app.run()

    app.text_input[0].set_value("NCT03412565")
    app.button[0].click().run()
    assert any("Now monitoring NCT03412565" in msg.value for msg in app.success)

    app.button(key="check_all").click().run()
    assert watchlist(app)[0]["What changed"] == display.EMPTY

    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()

    # What moved is read off the table itself, before anything is opened.
    line = watchlist(app)[0]
    assert display.UNREVIEWED in line["What changed"]
    assert "Enrollment" in line["What changed"]
    assert line["Changed on"] is not None

    open_profile(app)
    assert highlighted(app)

    app.button(key="review_NCT03412565").click().run()
    open_profile(app)
    assert not highlighted(app)

    # Read, but not forgotten: the names stay on the line, the bell clears.
    line = watchlist(app)[0]
    assert "Enrollment" in line["What changed"]
    assert display.UNREVIEWED not in line["What changed"]

    app.button(key="simulate").click().run()
    app.button(key="check_all").click().run()
    open_profile(app)

    assert not app.exception
    assert highlighted(app)


def test_reviewing_marks_the_feed_entry_as_read_without_removing_it(live):
    live.button(key="simulate").click().run()
    live.button(key="check_all").click().run()
    assert "unreviewed" in " ".join(m.value for m in live.markdown)

    open_profile(live)
    live.button(key="review_NCT03412565").click().run()

    rendered = " ".join(m.value for m in live.markdown)
    assert "3 fields changed" in rendered
    assert "unreviewed" not in rendered
