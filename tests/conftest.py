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


@pytest.fixture
def api(tmp_path, fetcher, make_finder):
    """The local server, running in-process on a free port over a temporary database.

    Built by the same factory `run.py` uses, with the suite's stub fetcher and
    finder, so nothing here reaches the live registry. Returns a client whose
    `get`/`post` give back (status, parsed JSON body).
    """
    import json as _json
    import threading
    import urllib.error
    import urllib.request

    from webapp.server import make_server

    db = str(tmp_path / "api.db")
    find = make_finder()
    server = make_server(db, fetch=fetcher, find=find)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class Client:
        path = db
        fetch = fetcher
        finder = find
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def fetch_override(self, fn):
            """Serve registry lookups from `fn` from now on (the server reads it per call)."""
            server.ctx.fetch = fn

        def request(self, method, route, body=None):
            data = None if body is None else _json.dumps(body).encode()
            req = urllib.request.Request(self.base + route, data=data, method=method)
            if method == "POST":
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw, status = resp.read(), resp.status
            except urllib.error.HTTPError as err:
                raw, status = err.read(), err.code
            return status, _json.loads(raw)

        def get(self, route):
            return self.request("GET", route)

        def post(self, route, body=None):
            return self.request("POST", route, body)

    yield Client()
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
