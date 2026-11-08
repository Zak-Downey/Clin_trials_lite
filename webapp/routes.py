"""The route table: (method, pattern) -> handler. Append new routes at the end."""

from __future__ import annotations

import re

from . import api_trials, api_watchlists

ROUTES = [
    ("GET", r"/api/watchlists", api_watchlists.list_watchlists),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/needs-review", api_watchlists.needs_review),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/changes", api_trials.changes),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})", api_trials.trial),
    ("POST", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/review", api_trials.review),
    ("POST", r"/api/reviews/(?P<event_id>\d+)/undo", api_trials.undo_review),
]

COMPILED = [(m, re.compile(p + r"\Z"), h) for m, p, h in ROUTES]
