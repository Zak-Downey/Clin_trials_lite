"""Shared fixtures. Nothing here touches the network."""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import storage  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def record() -> dict:
    """The real NCT03412565 registry record, captured from the live API."""
    return json.loads((FIXTURES / "NCT03412565.json").read_text(encoding="utf-8"))


@pytest.fixture
def conn(tmp_path):
    """A real SQLite database in a temporary directory.

    Exercised for real rather than mocked: the schema is part of the behaviour
    under test.
    """
    connection = storage.connect(str(tmp_path / "test.db"))
    yield connection
    connection.close()


@pytest.fixture
def make_fetcher():
    """Builds stub fetchers standing in for the API.

    A fetcher serves the record listed for an NCT ID -- or raises the exception
    listed for it, or falls back to `default` -- and records what it was asked
    for, so a test can assert that a fetch never happened.
    """

    def build(records: dict | None = None, failures: dict | None = None, default=None):
        def fetch(nct_id: str) -> dict:
            fetch.calls.append(nct_id)
            if failures and nct_id in failures:
                raise failures[nct_id]
            if records and nct_id in records:
                return records[nct_id]
            if default is None:
                raise KeyError(f"no stub record for {nct_id}")
            return default

        fetch.calls = []
        return fetch

    return build


@pytest.fixture
def fetcher(record, make_fetcher):
    """A stub fetcher serving the captured NCT03412565 record for any ID."""
    return make_fetcher(default=record)


@pytest.fixture
def make_finder():
    """Builds stub registry searches, standing in for the live service.

    A finder returns the studies listed for it -- or raises -- and records the
    arguments it was called with, so a test can assert what was asked for
    without a request leaving the machine.
    """

    def build(studies=None, failure=None):
        def find(**params):
            find.calls.append(params)
            if failure is not None:
                raise failure
            return list(studies or [])

        find.calls = []
        return find

    return build


@pytest.fixture
def restyled():
    """Stands the captured record in for another study, under a new NCT ID.

    A result set or a second list needs more than one study in it, and the one
    real record is the only one that carries every field a profile reads.
    """

    def build(record: dict, nct_id: str) -> dict:
        copied = copy.deepcopy(record)
        copied["protocolSection"]["identificationModule"]["nctId"] = nct_id
        return copied

    return build
