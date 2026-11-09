"""The route table: (method, pattern) -> handler. Append new routes at the end."""

from __future__ import annotations

import re

from . import api_checks, api_membership, api_new_matches, api_saved_search, api_search, api_summary, api_trials, api_watchlists

ROUTES = [
    ("GET", r"/api/watchlists", api_watchlists.list_watchlists),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/needs-review", api_watchlists.needs_review),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/changes", api_trials.changes),
    ("GET", r"/api/search", api_search.search),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/check", api_checks.progress),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/check", api_checks.start),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/check/retry", api_checks.retry),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/recheck", api_checks.recheck),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})", api_trials.trial),
    ("POST", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/review", api_trials.review),
    ("POST", r"/api/reviews/(?P<event_id>\d+)/undo", api_trials.undo_review),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/details", api_trials.details),
    ("GET", r"/api/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/history", api_trials.history),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})/remove", api_trials.remove),
    ("POST", r"/api/removals/undo", api_trials.undo_removal),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/summary", api_summary.summary),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/trials", api_membership.add_trials),
    ("GET", r"/api/registry/trials/(?P<nct_id>[Nn][Cc][Tt]\d{8})", api_membership.registry_trial),
    ("POST", r"/api/watchlists", api_watchlists.create_watchlist),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/lookup", api_membership.lookup),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/all-trials", api_watchlists.all_trials),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/saved-search", api_saved_search.read),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/saved-search", api_saved_search.save),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/saved-search/off", api_saved_search.turn_off),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/new-matches", api_new_matches.read),
    ("GET", r"/api/watchlists/(?P<list_id>\d+)/new-matches/dismissed", api_new_matches.dismissed),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/new-matches/dismiss", api_new_matches.dismiss),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/new-matches/restore", api_new_matches.restore),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/new-matches/undo", api_new_matches.undo),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/rename", api_watchlists.rename_watchlist),
    ("POST", r"/api/watchlists/(?P<list_id>\d+)/delete", api_watchlists.delete_watchlist),
]

COMPILED = [(m, re.compile(p + r"\Z"), h) for m, p, h in ROUTES]
