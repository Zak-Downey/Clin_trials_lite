"""The shared walk helper: the stand-in registry, the app, the guards.

Every walk goes through this (via the fixtures in conftest.py), so the guards
are one copy. Nothing here touches the network beyond 127.0.0.1.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from walks import standin_registry  # noqa: E402

FEATURE = os.environ.get("WALK_FEATURE", "html-front-end")
SHOTS = ROOT / ".scratch" / FEATURE / "walks"
VIEWPORTS = {"1440x900": (1440, 900), "1024x768": (1024, 768)}


class Registry:
    """The stand-in registry on a free port, with its control endpoint."""

    def __init__(self):
        self.server = standin_registry.make_registry()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def set(self, switch: str, on: bool = True, **extra) -> dict:
        """Flip a switch over the stand-in's own control endpoint (never the app's)."""
        body = json.dumps({"on": on, **extra}).encode()
        request = urllib.request.Request(
            f"{self.url}/control/{switch}", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as reply:
            return json.load(reply)

    def fetch(self, nct_id: str) -> dict:
        with urllib.request.urlopen(f"{self.url}/api/v2/studies/{nct_id}", timeout=10) as reply:
            return json.load(reply)

    def close(self):
        self.server.shutdown()
        self.server.server_close()


LONG_NAME = (
    "Non-small cell lung cancer: PD-1 and PD-L1 combination therapy competitors "
    "sponsored by industry, phase 2 and 3, tracked for the quarterly review"
)


def seed_queue(db: str, registry: Registry) -> None:
    """A database as an analyst's would be after a few checks.

    Watchlist 1 (long name) holds NCT03412565 (a real revision found by a check at
    16:45 UTC on 8 Nov 2026), NCT00000002 (a simulated change found at 09:00 UTC on
    8 Nov, so it is second) and NCT00000003 (nothing changed). Watchlist "Quiet" holds
    NCT00000003 too and needs no review. Lacks: a saved search, failures, many lists.
    """
    import monitor
    import simulate
    import storage

    conn = storage.connect(db)
    first = storage.list_lists(conn)[0]["id"]  # a new database already has one default list
    monitor.rename_list(conn, first, LONG_NAME)
    quiet = monitor.create_list(conn, "Quiet", when="2026-11-01T08:00:00+00:00")
    stamp = "2026-11-01T08:00:00+00:00"
    for nct in ("NCT03412565", "NCT00000002", "NCT00000003"):
        monitor.add(conn, nct, first, fetch=registry.fetch, when=stamp)
    monitor.add(conn, "NCT00000003", quiet, fetch=registry.fetch, when=stamp)

    simulate.rewind(conn, "NCT00000002", when="2026-11-02T08:00:00+00:00")
    monitor.check(conn, "NCT00000002", fetch=registry.fetch, when="2026-11-08T09:00:00+00:00")

    registry.set("revise", True)
    monitor.check(conn, "NCT03412565", fetch=registry.fetch, when="2026-11-08T16:45:00+00:00")
    registry.set("revise", False)
    conn.close()


class App:
    """The real server in a subprocess, on a free port, over a fresh database."""

    def __init__(self, tmp: pathlib.Path, registry: Registry, seed=None):
        self.registry = registry
        self.db = str(tmp / "walk.db")
        if seed:
            seed(self.db, registry)
        self.log = open(tmp / "server.log", "w")
        env = {k: v for k, v in os.environ.items() if k not in ("MONITOR_DB",)}
        env["TZ"] = "America/New_York"  # the server's zone; the browser is put elsewhere
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "walks" / "serve.py"), self.db, registry.url],
            stdout=subprocess.PIPE, stderr=self.log, text=True, env=env,
        )
        self.url = self.proc.stdout.readline().strip()
        if not self.url.startswith("http://127.0.0.1:"):
            self.close()
            raise RuntimeError(f"the app did not start: {(tmp / 'server.log').read_text()}")

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc.stdout.close()
        self.log.close()


class Guards:
    """What fails a walk without being asked: console and page errors, failed
    requests (including any to somewhere but the app), sideways scrolling.

    A guard means "unexpected failure". A walk that proves how the app handles an
    error response declares it first, with `expect(status, path)`; that response
    (and the console line the browser writes for it) is then not a failure, and a
    walk that declared one that never came fails.
    """

    def __init__(self, page, origin: str):
        self.page, self.origin, self.found = page, origin, []
        self.expected, self.seen = [], set()
        page.on("console", self._console)
        page.on("pageerror", lambda err: self.found.append(f"page error: {err}"))
        page.on("requestfailed", lambda r: self.found.append(f"failed request: {r.url} ({r.failure})"))
        page.on("request", self._foreign)
        page.on("response", self._status)

    def expect(self, status: int, path: str) -> None:
        """This walk expects the app's server to answer `path` (a URL path, no query) with `status`."""
        self.expected.append((status, path))

    def _path(self, url: str) -> str:
        return url[len(self.origin):].split("?", 1)[0] if url.startswith(self.origin) else url

    def _console(self, message):
        if message.type != "error":
            return
        url = (message.location or {}).get("url", "")
        for status, path in self.expected:
            if self._path(url) == path and str(status) in message.text:
                return
        self.found.append(f"console error: {message.text}")

    def _foreign(self, request):
        own = request.url == self.origin or request.url.startswith(self.origin + "/")
        if not own and not request.url.startswith("data:"):
            self.found.append(f"failed request: {request.url} (not the app's own server)")

    def _status(self, response):
        if response.status >= 400:
            if (response.status, self._path(response.url)) in self.expected:
                self.seen.add((response.status, self._path(response.url)))
                return
            self.found.append(f"failed request: {response.url} (status {response.status})")

    def measure(self) -> None:
        """Record sideways scrolling now: of the page, or of a region inside it."""
        if self.page.is_closed():
            return
        wide, regions = self.page.evaluate(
            """() => [
              document.documentElement.scrollWidth - document.documentElement.clientWidth,
              [...document.querySelectorAll('body *')].filter((el) => {
                const x = getComputedStyle(el).overflowX;
                return (x === 'auto' || x === 'scroll') && el.scrollWidth > el.clientWidth;
              }).map((el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')),
            ]""")
        if wide > 0:
            self.found.append(f"horizontal scrolling: the page is {wide}px wider than the window")
        for region in regions:
            self.found.append(f"horizontal scrolling: {region} scrolls sideways inside the page")

    def problems(self) -> list[str]:
        self.measure()
        missing = [f"expected response never came: {status} {path}"
                   for status, path in self.expected if (status, path) not in self.seen]
        return list(dict.fromkeys(self.found + missing))


def shot_name(nodeid: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", nodeid.split("::", 1)[-1]).strip("-")
