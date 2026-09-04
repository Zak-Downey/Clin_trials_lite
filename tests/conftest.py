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
def fetcher(record):
    """A stub fetcher standing in for the API, recording what it was asked for."""

    def fetch(nct_id: str) -> dict:
        fetch.calls.append(nct_id)
        return record

    fetch.calls = []
    return fetch
