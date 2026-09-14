"""Minimal client for the ClinicalTrials.gov v2 API.

No API key, no auth, no dependencies (stdlib only).
Docs: https://clinicaltrials.gov/data-api/api
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request

BASE = "https://clinicaltrials.gov/api/v2"

# This machine sits behind a TLS-intercepting proxy whose CA lives in the Windows
# certificate store, which Python ignores by default. `truststore` points SSL at
# the OS store so verification still happens properly. Falls back to the stdlib
# default anywhere that isn't needed.
try:
    import truststore

    _SSL_CTX = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:  # pragma: no cover
    _SSL_CTX = ssl.create_default_context()

# A useful default slice. Field names are the API's PascalCase ones.
# Drop `fields=` entirely to get the full (large) study record.
DEFAULT_FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "Phase",
    "StudyType",
    "EnrollmentCount",
    "StartDate",
    "CompletionDate",
    "LeadSponsorName",
    "Condition",
    "InterventionName",
]


def _get(path: str, params: dict) -> dict:
    """GET a JSON endpoint. Params with a None value are dropped."""
    query = {k: v for k, v in params.items() if v is not None}
    url = f"{BASE}{path}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        return json.load(resp)


def version() -> dict:
    """API version and the date the data snapshot was taken."""
    return _get("/version", {})


def _collect(params: dict, limit: int) -> list[dict]:
    """Studies matching `params`, following pagination until `limit` are collected."""
    studies: list[dict] = []
    token = None
    while len(studies) < limit:
        page = _get(
            "/studies",
            {**params, "pageSize": min(1000, limit - len(studies)), "pageToken": token},
        )
        studies.extend(page.get("studies", []))
        token = page.get("nextPageToken")
        if not token:
            break
    return studies[:limit]


def search(
    cond: str | None = None,
    term: str | None = None,
    intr: str | None = None,
    limit: int = 50,
    fields: list[str] | None = DEFAULT_FIELDS,
    **extra,
) -> list[dict]:
    """Search studies, following pagination until `limit` studies are collected.

    cond  -- condition/disease, e.g. "lung cancer"
    term  -- free-text search across the whole record
    intr  -- intervention/treatment, e.g. "pembrolizumab"
    extra -- any other API param, e.g. filter_overallStatus="RECRUITING"
             (underscores become dots: query_locn -> query.locn)
    """
    return _collect(
        {
            "query.cond": cond,
            "query.term": term,
            "query.intr": intr,
            "fields": ",".join(fields) if fields else None,
            **{k.replace("_", "."): v for k, v in extra.items()},
        },
        limit,
    )


# --- the axes a competitor search is built on
#
# Four that name the studies wanted -- condition, intervention, sponsor and
# phase: what somebody covering a therapy area actually says when they describe
# what they want to watch. Three more that narrow them -- sponsor class, status
# and start date: which of those studies are worth reading.
#
# Only the first three are plain query parameters. Everything else goes through
# `filter.advanced`, which is one parameter however many things it constrains,
# so the whole expression has to be assembled in one place rather than at each
# call site.

# The API's phase codes, in the order a reader expects to see them offered.
PHASE_CODES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"]

# How the registry classifies a lead sponsor, commercial first: that class is
# the whole difference between competitor intelligence and everything else.
#
# AMBIG and UNKNOWN are real codes the registry still returns, and are left out
# deliberately: fewer than a hundred studies carry either, and offering them
# would cost a line of the picker for a case nobody searches on.
SPONSOR_CLASSES = ["INDUSTRY", "OTHER", "NIH", "FED", "OTHER_GOV", "NETWORK", "INDIV"]

# Where a study has got to, in lifecycle order rather than alphabetically,
# because that is the order somebody reads a pipeline in.
#
# The expanded-access states (AVAILABLE, NO_LONGER_AVAILABLE,
# TEMPORARILY_NOT_AVAILABLE, APPROVED_FOR_MARKETING) and WITHHELD are omitted:
# they describe a drug-supply record rather than a trial in progress, which is
# not what this tool watches.
STATUS_CODES = [
    "NOT_YET_RECRUITING",
    "RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
    "SUSPENDED",
    "TERMINATED",
    "COMPLETED",
    "WITHDRAWN",
    "UNKNOWN",
]

# What the registry calls an open end of a date range. A window with one end
# left blank is still a range, running to the beginning or the end of the data.
EARLIEST = "MIN"
LATEST = "MAX"


# A registry code is a bare word: letters, digits and underscores. Anything
# else cannot be one, and must not be interpolated into a filter expression --
# a stray bracket would close the AREA clause early and leave the rest of the
# expression to be read as a separate condition, which *widens* the search.
# Queries are stored as JSON and re-run for months, so this is checked at the
# point of use rather than trusted to whatever assembled the query.
CODE = re.compile(r"^[A-Z0-9_]+$", re.IGNORECASE)


def _any_of(area: str, codes) -> str:
    """One AREA clause matching any of these codes, the way Essex spells it."""
    unknown = [c for c in codes if not CODE.match(str(c))]
    if unknown:
        raise ValueError(f"not registry codes for {area}: {unknown}")
    return f"AREA[{area}](" + " OR ".join(codes) + ")"


def search_params(
    cond: str | None = None,
    intr: str | None = None,
    spons: str | None = None,
    phases=(),
    sponsor_types=(),
    statuses=(),
    started_from: str | None = None,
    started_to: str | None = None,
) -> dict:
    """The seven search axes as the v2 API's own query parameters.

    A blank axis is left out altogether rather than sent empty, so an empty box
    does not narrow the search to studies whose condition is the empty string.
    An empty result therefore means the reader filled nothing in, which is the
    one query that must not be run.

    The four advanced-filter axes are joined with AND, not concatenated: each
    one has to narrow what the others left, and a clause that overwrote the
    previous one would silently *widen* the search -- the one failure here that
    looks like a working query.
    """
    params = {}
    for key, value in (
        ("query.cond", cond),
        ("query.intr", intr),
        ("query.spons", spons),
    ):
        if (value or "").strip():
            params[key] = value.strip()

    clauses = []
    if phases:
        clauses.append(_any_of("Phase", phases))
    if sponsor_types:
        clauses.append(_any_of("LeadSponsorClass", sponsor_types))
    if statuses:
        clauses.append(_any_of("OverallStatus", statuses))
    # A window with one end open is still a range: the registry's own MIN and
    # MAX stand in for the end the reader did not give.
    if (started_from or "").strip() or (started_to or "").strip():
        start = (started_from or "").strip() or EARLIEST
        end = (started_to or "").strip() or LATEST
        clauses.append(f"AREA[StartDate]RANGE[{start},{end}]")
    if clauses:
        params["filter.advanced"] = " AND ".join(clauses)
    return params


def find(
    cond: str | None = None,
    intr: str | None = None,
    spons: str | None = None,
    phases=(),
    sponsor_types=(),
    statuses=(),
    started_from: str | None = None,
    started_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Full study records matching the axes given.

    Whole records, not a field subset: what comes back is turned into the same
    profile a monitored trial gets, so the same code reads both.
    """
    return _collect(
        search_params(
            cond, intr, spons, phases, sponsor_types, statuses, started_from, started_to
        ),
        limit,
    )


def count(cond: str | None = None, term: str | None = None, **extra) -> int:
    """How many studies match, without downloading them."""
    params = {
        "query.cond": cond,
        "query.term": term,
        **{k.replace("_", "."): v for k, v in extra.items()},
    }
    return _get("/studies", {**params, "pageSize": 1, "countTotal": "true"})["totalCount"]


def get(nct_id: str) -> dict:
    """Fetch one full study record by NCT number."""
    return _get(f"/studies/{nct_id}", {})


def flatten(study: dict) -> dict:
    """Collapse a nested study record into flat `dotted.key -> scalar` pairs.

    Lists of scalars are joined with "|"; lists of objects are indexed.
    """
    out: dict = {}

    def walk(node, prefix=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(node, list):
            if all(not isinstance(i, (dict, list)) for i in node):
                out[prefix] = "|".join(str(i) for i in node)
            else:
                for i, item in enumerate(node):
                    walk(item, f"{prefix}[{i}]")
        else:
            out[prefix] = node

    walk(study)
    return out


def to_frame(studies: list[dict]):
    """Flattened studies as a pandas DataFrame. Requires `pip install pandas`."""
    import pandas as pd

    df = pd.DataFrame([flatten(s) for s in studies])
    # Strip the long, uniform `protocolSection.<x>Module.` prefixes for readability.
    df.columns = [c.split("Module.")[-1] for c in df.columns]
    return df
