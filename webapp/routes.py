"""The route table: (method, pattern) -> handler. Append new routes at the end."""

from __future__ import annotations

import re

from . import api_checks, api_trials, api_watchlists

ROUTES = [
    ("GET", r"/api/watchlists", api_watchlists.list_watchlists),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/needs-review", api_watchlists.needs_review),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/changes", api_trials.changes),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/check", api_checks.progress),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/check", api_checks.start),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/check/retry", api_checks.retry),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/recheck", api_checks.recheck),
]

COMPILED = [(m, re.compile(p + r"\Z"), h) for m, p, h in ROUTES]
