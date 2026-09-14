"""Reaching ClinicalTrials.gov from inside a browser.

The app is published as a static page that runs its Python as WebAssembly,
where there are no sockets and no certificate store: the only way out is to
ask the browser to make the request on the page's behalf.

This module is that transport, and it exists to keep one promise. Every
registry call in the app funnels through `ctgov._get`, and everything above it
reads failure in the vocabulary `urllib` raises -- a 404 becomes "was not found
on ClinicalTrials.gov", an unreachable host becomes "Could not reach
ClinicalTrials.gov". A transport that reported failure its own way would leave
an analyst reading a stack trace instead of a sentence, so this one raises the
same two exceptions the socket transport does.
"""

from __future__ import annotations

import json
import sys
import urllib.error

# WebAssembly is what Python calls the platform it compiles to for the browser,
# and is the one place where the transport below is both possible and needed.
IN_BROWSER = sys.platform == "emscripten"


def _new_request():
    """The browser's own request object. Only importable inside the browser."""
    # Imported here rather than at the top: `js` exists only under
    # WebAssembly, and this module is imported everywhere the app runs.
    import js

    return js.XMLHttpRequest.new()


def _set_deadline(call, timeout: float) -> None:
    """Give the request a deadline, where the browser allows one.

    A blocking request may only carry a timeout off the main thread, which is
    where stlite runs Python; on the main thread the browser refuses to set one
    rather than ignoring it. A registry that answers slowly is not worth
    failing the whole request over, so the browser's own network timeout stands
    in wherever ours is refused.
    """
    # Worked out before the assignment is attempted, so the guard below covers
    # the browser refusing a deadline and nothing else: a deadline this module
    # could not compute is a bug here, and should say so rather than leaving an
    # unbounded request behind.
    deadline = int(timeout * 1000)
    try:
        call.timeout = deadline
    except Exception:
        # A refusal to carry a deadline says nothing about whether the registry
        # is reachable, so it must not travel on as though it did.
        pass


def get_json(url: str, timeout: float = 30, request=None) -> dict:
    """GET a JSON document using the browser's networking."""
    call = (request or _new_request)()
    try:
        # Synchronously: the app above this is written straight through, and
        # stlite runs it off the main thread, where a blocking request is
        # allowed.
        call.open("GET", url, False)
        _set_deadline(call, timeout)
        call.setRequestHeader("Accept", "application/json")
        call.send(None)
    except Exception as exc:
        # A refused connection, a DNS failure, a request the page was not
        # allowed to make. The browser reports all of them by throwing, and
        # none of them distinguish themselves further.
        raise urllib.error.URLError(f"the browser could not make the request ({exc})") from exc

    status = int(call.status)
    if status == 0:
        # Not a status the registry sends: the browser saying the exchange
        # never happened at all, which is an unreachable host and not an
        # answer from one.
        raise urllib.error.URLError("the browser blocked the request")
    if status >= 400:
        raise urllib.error.HTTPError(url, status, str(call.statusText), None, None)
    return json.loads(call.responseText)
