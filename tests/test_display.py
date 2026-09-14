"""Formatting helpers used by the page."""

from __future__ import annotations

import pytest

import display


@pytest.mark.parametrize(
    "key, expected",
    [
        ("leadSponsor", "Lead sponsor"),
        ("primaryCompletionDate", "Primary completion date"),
        ("phases", "Phases"),
    ],
)
def test_keys_render_as_readable_labels(key, expected):
    assert display.label(key) == expected


def test_lists_render_comma_separated():
    assert display.show(["Daratumumab", "Bortezomib"]) == "Daratumumab, Bortezomib"


@pytest.mark.parametrize("value", [None, "", []])
def test_empty_values_render_explicitly_rather_than_blank(value):
    assert display.show(value) == display.EMPTY


@pytest.mark.parametrize("value, expected", [(0, "0"), (False, "False"), (265, "265")])
def test_falsy_but_real_values_are_not_mistaken_for_empty(value, expected):
    assert display.show(value) == expected


# --- marking changed fields in a rendered profile


@pytest.fixture
def row():
    """One marked-up profile row, shaped as the comparison hands it over."""

    def build(field="enrollment", value=265, changed=False, previous=None,
              high_signal=False, synthetic=False, qualifier=None,
              previous_qualifier=None):
        return {
            "field": field,
            "value": value,
            "changed": changed,
            "previous": previous,
            "high_signal": high_signal,
            "synthetic": synthetic,
            # Whether the registry calls the value estimated or actual, for the
            # fields that state it; None for every other field.
            "qualifier": qualifier,
            "previous_qualifier": previous_qualifier,
        }

    return build


def test_an_unchanged_field_renders_plainly(row):
    rendered = display.field_line(row(field="officialTitle", value="A study of things"))

    assert "Official title" in rendered
    assert "A study of things" in rendered
    assert display.HIGHLIGHT not in rendered
    assert display.HIGHLIGHT_HIGH_SIGNAL not in rendered


def test_an_unchanged_high_signal_field_is_not_highlighted(row):
    rendered = display.field_line(row(high_signal=True))

    assert display.HIGHLIGHT_HIGH_SIGNAL not in rendered


def test_a_changed_field_is_highlighted_and_shows_both_values(row):
    rendered = display.field_line(row(changed=True, previous=350))

    assert display.HIGHLIGHT in rendered
    assert "265" in rendered
    assert "350" in rendered


def test_a_changed_high_signal_field_is_more_prominent_than_an_ordinary_one(row):
    ordinary = display.field_line(row(field="acronym", value="X", changed=True, previous="Y"))
    high = display.field_line(row(changed=True, previous=350, high_signal=True))

    assert display.HIGHLIGHT_HIGH_SIGNAL in high
    assert display.HIGHLIGHT_HIGH_SIGNAL not in ordinary
    assert display.HIGHLIGHT in ordinary


def test_a_field_reads_as_one_line_with_its_label_beside_its_value(row):
    """The density of the dossier: a label above its value is a wasted line."""
    rendered = display.field_line(row(field="enrollment", value=265))

    assert len(rendered.splitlines()) == 1
    assert rendered.index("Enrollment") < rendered.index("265")


def test_a_previously_empty_field_shows_its_emptiness_explicitly(row):
    rendered = display.field_line(
        row(field="whyStopped", value="Slow accrual", changed=True, previous=None)
    )

    assert display.EMPTY in rendered
    assert "Slow accrual" in rendered


def test_a_synthetic_change_is_marked_on_the_field(row):
    """The mark alone: a card line is too narrow to spell the word out."""
    fake = display.field_line(row(changed=True, previous=350, synthetic=True))
    real = display.field_line(row(changed=True, previous=350))

    assert display.SYNTHETIC_MARK in fake
    assert display.SYNTHETIC_MARK not in real


def test_a_results_url_renders_as_a_link(row):
    rendered = display.field_line(
        row(field="resultsUrl", value="https://clinicaltrials.gov/study/NCT1?tab=results")
    )

    assert "](https://clinicaltrials.gov/study/NCT1?tab=results)" in rendered


def test_no_elapsed_time_is_calculated_for_a_date_change(row):
    rendered = display.field_line(
        row(field="completionDate", value="2024-04-18", changed=True,
            previous="2023-04-18", high_signal=True)
    )

    assert "2024-04-18" in rendered
    assert "2023-04-18" in rendered
    for word in ("days", "months", "years", "later", "earlier", "ago"):
        assert word not in rendered.lower()


# --- the two columns of the watchlist table that carry the news


@pytest.fixture
def line():
    """One watchlist row, shaped as monitor.watchlist hands it over."""

    def build(
        fields=(),
        at="2026-09-05T10:00:00+00:00",
        unreviewed=0,
        synthetic=False,
        registry_updated="2026-08-24",
    ):
        change = (
            {"at": at, "fields": list(fields), "synthetic": synthetic} if fields else None
        )
        return {
            "change": change,
            "unreviewed": unreviewed,
            "registry_updated": registry_updated,
        }

    return build


def test_a_trial_that_has_never_changed_says_so_rather_than_looking_blank(line):
    assert display.changed_fields(line()) == display.EMPTY
    assert display.detected_on(line()) is None
    assert display.registry_updated(line()) is None


def test_the_fields_that_moved_are_named_readably(line):
    rendered = display.changed_fields(line(fields=["completionDate", "enrollment"]))

    assert "Completion date" in rendered
    assert "Enrollment" in rendered


def test_a_long_list_of_fields_is_capped_with_an_overflow_count(line):
    rendered = display.changed_fields(
        line(fields=["completionDate", "enrollment", "acronym", "officialTitle", "sex"]),
        cap=3,
    )

    assert "+2 more" in rendered
    assert "Sex" not in rendered


def test_a_list_within_the_cap_gets_no_overflow_count(line):
    rendered = display.changed_fields(line(fields=["enrollment"]), cap=3)

    assert "more" not in rendered


def test_a_trial_with_something_unread_is_distinguishable_from_one_without(line):
    unread = display.changed_fields(line(fields=["enrollment"], unreviewed=1))
    read = display.changed_fields(line(fields=["enrollment"]))

    assert display.UNREVIEWED in unread
    assert display.UNREVIEWED not in read


def test_the_field_names_survive_being_marked_as_read(line):
    read = display.changed_fields(line(fields=["enrollment"]))

    assert "Enrollment" in read


def test_a_simulated_change_is_marked_on_the_line(line):
    fake = display.changed_fields(line(fields=["enrollment"], synthetic=True))
    real = display.changed_fields(line(fields=["enrollment"]))

    assert display.SYNTHETIC_MARK in fake
    assert display.SYNTHETIC_MARK not in real


def test_the_date_is_a_real_date_so_the_column_sorts_chronologically(line):
    import datetime

    assert display.detected_on(line(fields=["enrollment"])) == datetime.date(2026, 9, 5)


def test_when_the_sponsor_revised_is_told_apart_from_when_we_noticed(line):
    """A list checked weekly must not show a fortnight-old revision as though
    it landed this morning."""
    import datetime

    row = line(fields=["enrollment"])

    assert display.registry_updated(row) == datetime.date(2026, 8, 24)
    assert display.detected_on(row) == datetime.date(2026, 9, 5)


def test_a_record_the_registry_gives_no_revision_date_for_renders_empty(line):
    assert display.registry_updated(line(fields=["enrollment"], registry_updated=None)) is None


def test_the_date_column_spells_the_month_out(line):
    # A momentJS pattern, rendered client-side: MMMM is the month's name, and
    # an all-numeric date would need a numeric month token instead.
    assert "MMMM" in display.DATE_FORMAT.split()
    assert not {"M", "MM"} & set(display.DATE_FORMAT.split())


# --- the remaining columns


@pytest.mark.parametrize(
    "phases, expected",
    [
        (["PHASE2"], "Phase 2"),
        (["PHASE1", "PHASE2"], "Phase 1/Phase 2"),
        (["EARLY_PHASE1"], "Early Phase 1"),
        (["NA"], "N/A"),
        ([], display.EMPTY),
    ],
)
def test_registry_phase_codes_render_as_readable_phases(phases, expected):
    assert display.phase_label(phases) == expected


@pytest.mark.parametrize(
    "status, expected",
    [
        ("COMPLETED", "Completed"),
        ("ACTIVE_NOT_RECRUITING", "Active not recruiting"),
        (None, display.EMPTY),
    ],
)
def test_registry_status_codes_render_as_readable_statuses(status, expected):
    assert display.status_label(status) == expected


# --- the dossier: the profile's fields dealt into cards


@pytest.fixture
def profile_rows(row):
    """Marked rows for a whole profile, as the comparison hands them over."""

    def build(fields, **marks):
        return [row(field=f, value=f"value of {f}", **marks) for f in fields]

    return build


def test_every_profile_field_lands_in_exactly_one_card(profile_rows, record):
    import diff
    import medical_affairs

    # Every field the marked-up rows carry: a qualifier is folded into the
    # value it qualifies before the cards are dealt, so it is never one of them.
    fields = [f for f in medical_affairs.profile(record) if f not in diff.QUALIFIES]
    cards = display.group_fields(profile_rows(fields))

    dealt = [r["field"] for _, rows in cards for r in rows]
    assert sorted(dealt) == sorted(fields)
    # In a named card, not swept into the fallback.
    assert display.OTHER not in [title for title, _ in cards]


def test_the_cards_arrive_in_a_fixed_order(profile_rows):
    """The reader learns where the dates are, so they must not move."""
    fields = ["completionDate", "nctId", "hasResults", "leadSponsor"]
    titles = [title for title, _ in display.group_fields(profile_rows(fields))]

    assert titles == ["Identity", "Sponsor", "Status and dates", "Results"]


def test_an_unrecognised_field_falls_into_a_card_rather_than_vanishing(profile_rows):
    cards = display.group_fields(profile_rows(["nctId", "somethingAddedLater"]))

    assert cards[-1][0] == display.OTHER
    assert [r["field"] for r in cards[-1][1]] == ["somethingAddedLater"]


def test_a_card_with_none_of_its_fields_present_is_not_rendered(profile_rows):
    titles = [title for title, _ in display.group_fields(profile_rows(["nctId"]))]

    assert titles == ["Identity"]


def test_a_card_is_one_block_holding_every_field_it_was_given(profile_rows):
    """One block is the density win: Streamlit puts a margin around each one."""
    card = display.render_card("Identity", profile_rows(["nctId", "acronym"]))

    assert "IDENTITY" in card
    assert "Nct id" in card
    assert "Acronym" in card
    # A markdown line break, not a paragraph: one block, three lines in it.
    assert card.count("  \n") == 2


def test_a_card_holding_unreviewed_changes_says_how_many_in_its_title(row):
    rows = [
        row(field="enrollment", changed=True, previous=350),
        row(field="completionDate", value="2027-01-01", changed=True, previous="2026-01-01"),
        row(field="acronym", value="X"),
    ]
    title = display.card_title("Design and scale", rows)

    assert display.UNREVIEWED in title
    assert "2" in title


def test_a_card_with_nothing_unreviewed_carries_no_count(row):
    title = display.card_title("Identity", [row(field="acronym", value="X")])

    assert display.UNREVIEWED not in title
    assert "IDENTITY" in title


# --- a value and whether the registry calls it estimated or actual


def test_a_date_is_shown_beside_whether_it_is_estimated_or_actual(row):
    rendered = display.field_line(
        row(field="completionDate", value="2024-04-18", qualifier="ACTUAL")
    )

    assert "2024-04-18" in rendered
    assert "Actual" in rendered


def test_a_date_becoming_actual_reads_as_one_entry_alongside_its_value(row):
    """One event, not a date move and an unexplained type move beside it."""
    rendered = display.field_line(
        row(
            field="primaryCompletionDate",
            value="2024-04-18",
            qualifier="ACTUAL",
            previous="2024-04-18",
            previous_qualifier="ESTIMATED",
            changed=True,
            high_signal=True,
        )
    )

    assert "Estimated" in rendered
    assert "Actual" in rendered
    assert rendered.count("Previously") == 1
    assert "Primary completion date type" not in rendered


def test_a_field_with_no_type_to_state_is_rendered_as_it_always_was(row):
    assert display.field_line(row(field="acronym", value="PLEIADES")) == (
        "**Acronym** · PLEIADES"
    )


# --- eligibility criteria
#
# Forty lines of bullets in a card a third of the page wide, so what is shown
# is an excerpt and the exact wording is one registry link away.


@pytest.fixture
def criteria() -> str:
    return "Inclusion Criteria:\n\n" + "\n".join(
        f"* Documented multiple myeloma, condition {n}" for n in range(40)
    )


def test_the_criteria_render_as_a_short_single_line_excerpt(row, criteria):
    rendered = display.field_line(row(field="eligibilityCriteria", value=criteria))

    assert len(rendered.splitlines()) == 1
    assert len(rendered) < len(criteria)
    assert "Inclusion Criteria:" in rendered
    assert rendered.endswith("…")  # cut off, rather than running on


def test_short_criteria_are_not_cut(row):
    rendered = display.field_line(
        row(field="eligibilityCriteria", value="Inclusion Criteria: aged 18 or over")
    )

    assert "aged 18 or over" in rendered
    assert "…" not in rendered


def test_the_excerpt_drops_the_registrys_bullet_markers(criteria):
    """A bulleted list inside a one-block card reads as emphasis, not bullets."""
    assert "*" not in display.excerpt(criteria)
    assert "Documented multiple myeloma" in display.excerpt(criteria)


def test_a_study_stating_no_criteria_is_not_given_a_link_to_them(row):
    """Nothing to follow the link to, so it renders as any empty field does."""
    rendered = display.field_line(
        row(field="eligibilityCriteria", value=None), nct_id="NCT03412565"
    )

    assert display.EMPTY in rendered
    assert display.CRITERIA_LINK not in rendered


def test_the_full_criteria_are_one_registry_link_away(row, criteria):
    rendered = display.field_line(
        row(field="eligibilityCriteria", value=criteria), nct_id="NCT03412565"
    )

    assert "](https://clinicaltrials.gov/study/NCT03412565)" in rendered


def test_an_amendment_says_the_criteria_moved_rather_than_printing_both(row, criteria):
    """A full before-and-after would swamp the card and every other change on
    the page with it."""
    rendered = display.field_line(
        row(
            field="eligibilityCriteria",
            value=criteria,
            changed=True,
            previous=criteria.replace("multiple myeloma", "smouldering myeloma"),
            high_signal=True,
        )
    )

    assert display.HIGHLIGHT_HIGH_SIGNAL in rendered
    assert display.AMENDED in rendered
    assert "smouldering myeloma" not in rendered
    assert len(rendered) < len(criteria)


def test_an_amendment_does_not_grow_the_card_it_sits_in(row, criteria):
    plain = display.field_line(row(field="eligibilityCriteria", value=criteria))
    amended = display.field_line(
        row(field="eligibilityCriteria", value=criteria, changed=True, previous="x")
    )

    assert len(amended.splitlines()) == len(plain.splitlines()) + 1


# --- the narrowing axes read back
#
# A list's remembered search is the one place an analyst checks whether it is
# still watching for the right thing, so a sponsor class has to read as a kind
# of organisation and a date window as a sentence -- never as the registry's
# own codes.


def test_a_sponsor_class_reads_as_a_kind_of_organisation():
    assert display.sponsor_type_label(["INDUSTRY"]) == "Industry"
    # Not "Academic or other": a company funding an academic centre's trial is
    # a collaborator on it and lands in OTHER, so the bucket is mixed and the
    # label must not promise that the companies are all in Industry.
    assert display.sponsor_type_label(["OTHER"]) == "Other (incl. academic)"
    assert display.sponsor_type_label(["OTHER_GOV"]) == "Other government"


def test_several_sponsor_classes_read_as_a_list():
    assert display.sponsor_type_label(["INDUSTRY", "NIH"]) == "Industry/NIH"


def test_a_start_window_reads_as_a_sentence():
    assert display.started_label("2024-01-01", "2024-12-31") == (
        "started 1 January 2024 to 31 December 2024"
    )


def test_a_start_window_open_at_one_end_says_which_end():
    assert display.started_label("2024-01-01", "") == "started on or after 1 January 2024"
    assert display.started_label("", "2024-12-31") == "started on or before 31 December 2024"


def test_no_start_window_reads_as_nothing_at_all():
    assert display.started_label("", "") == ""


def test_a_search_line_names_every_axis_that_was_set():
    line = display.search_line(
        {
            "cond": "cll",
            "intr": "",
            "spons": "",
            "phases": ["PHASE3"],
            "sponsor_types": ["INDUSTRY"],
            "statuses": ["RECRUITING"],
            "started_from": "2024-01-01",
            "started_to": "",
        }
    )

    assert line == (
        "Condition cll · Phase 3 · Sponsor type Industry · Status Recruiting · "
        "started on or after 1 January 2024"
    )


def test_a_search_line_for_a_query_stored_before_the_narrowing_axes_still_reads():
    """The four-key shape a list saved under ticket 13 still has to render."""
    line = display.search_line(
        {"cond": "cll", "intr": "", "spons": "Janssen", "phases": ["PHASE3"]}
    )

    assert line == "Condition cll · Sponsor Janssen · Phase 3"


def test_a_coded_axis_is_named_so_a_bare_code_word_is_not_ambiguous():
    """"Network" alone does not say which box it was typed in."""
    assert display.search_line({"cond": "cll", "sponsor_types": ["NETWORK"]}) == (
        "Condition cll · Sponsor type Network"
    )
    assert display.search_line({"cond": "cll", "statuses": ["UNKNOWN"]}) == (
        "Condition cll · Status Unknown"
    )


def test_a_date_reads_the_same_in_a_search_line_as_in_a_briefing():
    """One prose date format, or the two screens spell the same day differently."""
    assert display.long_date("2024-01-01") in display.started_label("2024-01-01", "")


def test_a_registry_code_nobody_gave_a_word_to_still_renders():
    """A class the registry adds tomorrow must not render as a blank."""
    assert display.sponsor_type_label(["AMBIG"]) == "Ambig"
