"""Minimal client for the ClinicalTrials.gov v2 API.

No API key, no auth, no third-party dependencies (stdlib only, plus `truststore`
where the machine needs it).
Docs: https://clinicaltrials.gov/data-api/api
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request


BASE = "https://clinicaltrials.gov/api/v2"

try:
    import truststore

    _SSL_CTX = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:
    _SSL_CTX = ssl.create_default_context()

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


TIMEOUT = 30


def _get(path: str, params: dict) -> dict:
    """GET a JSON endpoint. Params with a None value are dropped.

    The one place the whole app reaches the registry, and so the one place that
    reaches it, over a socket, raising `urllib` errors that callers turn into
    sentences.
    """
    query = {k: v for k, v in params.items() if v is not None}
    url = f"{BASE}{path}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
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



PHASE_CODES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"]

SPONSOR_CLASSES = ["INDUSTRY", "OTHER", "NIH", "FED", "OTHER_GOV", "NETWORK", "INDIV"]

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

EARLIEST = "MIN"
LATEST = "MAX"


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


def find_page(
    cond: str | None = None,
    intr: str | None = None,
    spons: str | None = None,
    phases=(),
    sponsor_types=(),
    statuses=(),
    started_from: str | None = None,
    started_to: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """One page of full study records, and the registry's total for the same query.

    The registry pages by token, so page N is read as the first N pages in one
    request and sliced: a page is never more than the cap the caller allows.
    """
    params = search_params(
        cond, intr, spons, phases, sponsor_types, statuses, started_from, started_to
    )
    answer = _get(
        "/studies",
        {**params, "pageSize": page * page_size, "countTotal": "true"},
    )
    studies = answer.get("studies", [])
    return {
        "studies": studies[(page - 1) * page_size : page * page_size],
        "total": answer.get("totalCount", len(studies)),
    }


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
    df.columns = [c.split("Module.")[-1] for c in df.columns]
    return df
