"""Running inside the browser: reaching the registry, and pausing between calls.

When the app runs as WebAssembly there is no socket layer underneath it: the
page has to ask the browser to make the request. What must survive the move is
not the mechanism but the vocabulary of failure -- the app turns one exception
into "was not found" and another into "Could not reach ClinicalTrials.gov", and
an analyst reads those sentences rather than a stack trace.

So the browser's own request object is the seam, stubbed here the way the
fetching seam is stubbed elsewhere: nothing in this file touches the network.
And nothing in it waits, either -- the clock is a seam for the same reason.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

import browser
import ctgov
import monitor


class FakeRequest:
    """Stands in for the browser's XMLHttpRequest, in its own JS spelling."""

    def __init__(self, status=200, body="", status_text="OK", refuses=None):
        self.status = status
        self.statusText = status_text
        self.responseText = body
        self.timeout = 0
        self._refuses = refuses
        self.opened = None
        self.headers = {}
        self.sent = False

    def open(self, method, url, is_async):
        self.opened = (method, url, is_async)

    def setRequestHeader(self, name, value):
        self.headers[name] = value

    def send(self, body=None):
        if self._refuses is not None:
            raise self._refuses
        self.sent = True


def serving(**kwargs):
    """A request factory handing out one prepared response, every time."""
    request = FakeRequest(**kwargs)
    return lambda: request


# --- the happy path


def test_a_json_body_comes_back_parsed():
    payload = {"studies": [{"nctId": "NCT03412565"}]}

    assert browser.get_json(
        "https://clinicaltrials.gov/api/v2/studies",
        request=serving(body=json.dumps(payload)),
    ) == payload


# --- failure, in the vocabulary the app already reads
#
# `urllib.error.HTTPError` carries a status code and `urllib.error.URLError` a
# reason, and monitor.py tells a missing study from a broken connection by
# which of the two it catches. Both have to arrive from here unchanged.


def test_a_missing_study_arrives_as_a_404_the_way_urllib_reports_one():
    with pytest.raises(urllib.error.HTTPError) as raised:
        browser.get_json(
            "https://clinicaltrials.gov/api/v2/studies/NCT99999999",
            request=serving(status=404, status_text="Not Found", body="not found"),
        )

    assert raised.value.code == 404


def test_a_refused_request_arrives_as_an_unreachable_host():
    with pytest.raises(urllib.error.URLError):
        browser.get_json(
            "https://clinicaltrials.gov/api/v2/studies",
            request=serving(refuses=RuntimeError("NetworkError: failed to fetch")),
        )


def test_a_request_the_browser_blocked_is_unreachable_rather_than_an_error_code():
    """A blocked or aborted request answers with no status at all.

    Zero is not a status the registry ever sends; it is the browser saying the
    exchange never happened. Reading it as an HTTP error would tell an analyst
    the registry replied when nothing replied.
    """
    with pytest.raises(urllib.error.URLError) as raised:
        browser.get_json(
            "https://clinicaltrials.gov/api/v2/studies",
            request=serving(status=0, status_text="", body=""),
        )

    assert not isinstance(raised.value, urllib.error.HTTPError)


# --- what is actually asked of the browser
#
# This module is an adapter, so the request it builds is its behaviour: an
# asynchronous request would hand back an empty body that reads as a registry
# with nothing in it.


def test_the_registry_is_asked_for_json_over_a_blocking_get():
    call = FakeRequest(body="{}")

    browser.get_json("https://clinicaltrials.gov/api/v2/version", request=lambda: call)

    assert call.opened == ("GET", "https://clinicaltrials.gov/api/v2/version", False)
    assert call.headers == {"Accept": "application/json"}
    assert call.sent


def test_the_request_carries_a_deadline_in_the_browsers_own_milliseconds():
    call = FakeRequest(body="{}")

    browser.get_json("https://clinicaltrials.gov/api/v2/version", timeout=5, request=lambda: call)

    assert call.timeout == 5000


def test_a_browser_that_refuses_the_deadline_still_gets_the_request():
    """Some browsers refuse a deadline on a blocking request rather than ignoring it.

    That refusal says nothing about whether the registry is reachable, so
    letting it travel on as "could not reach ClinicalTrials.gov" would report
    an outage that is not happening -- and report it for every request.
    """

    class RefusesDeadlines(FakeRequest):
        def __setattr__(self, name, value):
            if name == "timeout" and getattr(self, "opened", None):
                raise RuntimeError("InvalidAccessError")
            super().__setattr__(name, value)

    call = RefusesDeadlines(body='{"version": "2.0.0"}')

    assert browser.get_json("https://clinicaltrials.gov/api/v2/version", request=lambda: call) == {
        "version": "2.0.0"
    }


# --- the app's single exit to the registry
#
# Everything above `ctgov._get` is untouched by the move to the browser, and
# these are the tests that say so: the analyst reads the same two sentences
# whichever transport is underneath.


@pytest.fixture
def in_browser(monkeypatch):
    """Run the registry client as it runs inside the browser."""
    monkeypatch.setattr(browser, "IN_BROWSER", True)

    def answering(**kwargs):
        prepared = serving(**kwargs)
        monkeypatch.setattr(browser, "_new_request", prepared)
        return prepared()

    return answering


def test_the_browser_makes_the_registry_call(in_browser):
    call = in_browser(body='{"apiVersion": "2.0.0"}')

    assert ctgov.version() == {"apiVersion": "2.0.0"}
    assert call.opened[1] == "https://clinicaltrials.gov/api/v2/version?"


def test_a_search_comes_back_from_the_browser_as_studies(in_browser, record):
    in_browser(body=json.dumps({"studies": [record]}))

    assert ctgov.find(cond="multiple myeloma", limit=1) == [record]


def test_a_study_that_does_not_exist_still_reads_as_was_not_found(conn, in_browser):
    in_browser(status=404, status_text="Not Found", body='{"message": "not found"}')

    with pytest.raises(monitor.MonitorError, match="NCT99999999 was not found on ClinicalTrials.gov"):
        monitor.add(conn, "NCT99999999")


def test_a_registry_that_cannot_be_reached_still_reads_as_could_not_reach(conn, in_browser):
    in_browser(refuses=RuntimeError("NetworkError"))

    with pytest.raises(monitor.MonitorError, match="Could not reach ClinicalTrials.gov"):
        monitor.add(conn, "NCT03412565")


def test_a_search_against_an_unreachable_registry_still_reads_as_could_not_reach(in_browser):
    in_browser(refuses=RuntimeError("NetworkError"))

    with pytest.raises(monitor.MonitorError, match="Could not reach ClinicalTrials.gov"):
        monitor.search(cond="multiple myeloma")


# --- pausing, where there is no sleep to do it
#
# Working through a watchlist puts a deliberate gap between registry calls
# because the registry is a free public service. `browser.wait` carries the
# reason; what these hold to is that the gap is the app's own and is real in
# both places -- because the way it could be lost is silently, with the call
# still there and still made.


class FakeClock:
    """A monotonic clock that only moves when it is read."""

    def __init__(self, step):
        self.now = 0.0
        self.step = step
        self.reads = 0

    def __call__(self):
        self.reads += 1
        now = self.now
        self.now += self.step
        return now


def test_locally_the_pause_is_the_standard_librarys_own_sleep(monkeypatch):
    """Nothing changes off the browser: a real sleep costs nothing to wait in."""
    monkeypatch.setattr(browser, "IN_BROWSER", False)
    slept = []
    monkeypatch.setattr(browser.time, "sleep", slept.append)

    browser.wait(0.5)

    assert slept == [0.5]


def test_in_the_browser_the_pause_actually_takes_the_time_asked_for(monkeypatch):
    monkeypatch.setattr(browser, "IN_BROWSER", True)
    # Whatever the runtime's own sleep does, the pause here must be this
    # module's doing -- otherwise there is nothing for a test to hold on to.
    monkeypatch.setattr(browser.time, "sleep", lambda seconds: pytest.fail("the pause must be ours"))
    clock = FakeClock(step=0.1)
    monkeypatch.setattr(browser.time, "monotonic", clock)

    browser.wait(0.5)

    # It read the clock until half a second had passed, rather than returning
    # on the first read the way `time.sleep` does under WebAssembly.
    assert clock.now >= 0.5


def test_a_pause_of_nothing_returns_at_once_in_the_browser(monkeypatch):
    """Tests pass `pause=0` to mean "no waiting", and must not spin instead."""
    monkeypatch.setattr(browser, "IN_BROWSER", True)
    clock = FakeClock(step=0.0)
    monkeypatch.setattr(browser.time, "monotonic", clock)

    browser.wait(0)

    assert clock.reads <= 2
