"""Shared fixtures. Nothing here touches the network."""

from __future__ import annotations

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
