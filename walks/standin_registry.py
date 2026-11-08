"""A local stand-in for ClinicalTrials.gov: the two calls the app makes.

    GET /api/v2/studies/<NCT ID>      one study
    GET /api/v2/studies               a search: pageSize, pageToken, countTotal

Serves the captured NCT03412565 record (tests/fixtures) and copies of it under
other NCT IDs. Lacks: any record that is not that one study (every study here
has the same conditions, sponsor and arms), filtering (a search returns the same
studies whatever it asks, except the two condition words below), and the
registry's real paging tokens.

A search with query.cond "many" answers 134 studies (NCT10000001 to NCT10000134),
one with "nothing" answers none; every other search answers the three-or-four study set.
totalCount is always the true size of the answer.

Switches, flipped over POST /control/<name> with {"on": true|false}:

    not_found     a lookup answers 404 as the registry does for an unknown study
    server_error  both calls answer 500
    slow          both calls wait `delay` seconds first (POST /control/slow {"on": true, "delay": 3})
    revise        NCT03412565 is served in a later version: a later completion date,
                  other enrolment, one intervention fewer, a later registry update date
    fail          lookups of the listed studies answer 500, the others as usual
                  (POST /control/fail {"on": true, "ids": ["NCT00000002"]})
    register      a further study (REGISTERED_ID) joins the search results

GET /control shows the switches. The app is never asked to flip them.
"""

from __future__ import annotations

import copy
import json
import pathlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "NCT03412565.json"
BASE_ID = "NCT03412565"
REGISTERED_ID = "NCT00000099"
COPY_IDS = ["NCT00000002", "NCT00000003"]
SWITCHES = ("fail", "not_found", "register", "revise", "server_error", "slow")


def _captured() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _copy_as(record: dict, nct_id: str) -> dict:
    copied = copy.deepcopy(record)
    copied["protocolSection"]["identificationModule"]["nctId"] = nct_id
    return copied


def revised(record: dict) -> dict:
    """The later version of a study that **revise** serves."""
    later = copy.deepcopy(record)
    protocol = later["protocolSection"]
    status = protocol["statusModule"]
    status["completionDateStruct"]["date"] = "2026-12-31"
    status["lastUpdatePostDateStruct"]["date"] = "2026-11-06"
    status["lastUpdateSubmitDate"] = "2026-11-05"
    protocol["designModule"]["enrollmentInfo"]["count"] += 17
    interventions = protocol["armsInterventionsModule"]["interventions"]
    protocol["armsInterventionsModule"]["interventions"] = interventions[:-1]
    return later


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.on = {name: False for name in SWITCHES}
        self.delay = 2.0
        self.fail_ids: list[str] = []
        self.requests = []  # (path) of every registry call, for tests

    def snapshot(self) -> dict:
        with self.lock:
            return {**self.on, "delay": self.delay, "fail_ids": list(self.fail_ids)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _reply(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _studies(self) -> dict:
        base = _captured()
        studies = {BASE_ID: revised(base) if self.server.state.on["revise"] else base}
        for nct in COPY_IDS:
            studies[nct] = _copy_as(base, nct)
        if self.server.state.on["register"]:
            studies[REGISTERED_ID] = _copy_as(base, REGISTERED_ID)
        return studies

    def do_GET(self):
        parts = urlsplit(self.path)
        state = self.server.state
        if parts.path == "/control":
            return self._reply(200, state.snapshot())
        if not parts.path.startswith("/api/v2/"):
            return self._reply(404, {"error": "not found"})
        state.requests.append(self.path)
        flags = state.snapshot()
        if flags["slow"]:
            time.sleep(flags["delay"])
        if flags["server_error"]:
            return self._reply(500, {"error": "server error"})
        route = parts.path[len("/api/v2"):]
        studies = self._studies()
        if route.startswith("/studies/"):
            nct = route[len("/studies/"):].upper()
            if flags["fail"] and nct in flags["fail_ids"]:
                return self._reply(500, {"error": f"{nct} failed"})
            if flags["not_found"] or nct not in studies:
                return self._reply(404, {"error": f"{nct} not found"})
            return self._reply(200, studies[nct])
        if route == "/studies":
            query = parse_qs(parts.query)
            size = int(query.get("pageSize", ["10"])[0])
            start = int(query.get("pageToken", ["0"])[0])
            everything = list(studies.values())
            cond = query.get("query.cond", [""])[0].strip().lower()
            if cond == "many":
                base = _captured()
                everything = [_copy_as(base, f"NCT{10000000 + n:08d}") for n in range(1, 135)]
            elif cond == "nothing":
                everything = []
            page = everything[start:start + size]
            body = {"studies": page}
            if start + size < len(everything):
                body["nextPageToken"] = str(start + size)
            if query.get("countTotal", ["false"])[0] == "true":
                body["totalCount"] = len(everything)
            return self._reply(200, body)
        return self._reply(404, {"error": "not found"})

    def do_POST(self):
        parts = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        name = parts.path[len("/control/"):] if parts.path.startswith("/control/") else ""
        state = self.server.state
        if name == "reset":
            with state.lock:
                state.on = {n: False for n in SWITCHES}
                state.fail_ids = []
        elif name in SWITCHES:
            with state.lock:
                state.on[name] = bool(body.get("on", True))
                if "ids" in body:
                    state.fail_ids = [str(i).upper() for i in body["ids"]]
                if "delay" in body:
                    state.delay = float(body["delay"])
        else:
            return self._reply(404, {"error": f"no switch {name!r}"})
        self._reply(200, state.snapshot())


def make_registry(port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.state = State()
    return server


if __name__ == "__main__":
    import sys

    registry = make_registry(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    print(f"http://127.0.0.1:{registry.server_address[1]}", flush=True)
    registry.serve_forever()
