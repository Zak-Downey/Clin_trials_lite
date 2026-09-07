"""Minimal client for the ClinicalTrials.gov v2 API.

No API key, no auth, no dependencies (stdlib only).
Docs: https://clinicaltrials.gov/data-api/api
"""

from __future__ import annotations

import json
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


# --- the four axes a competitor search is built on
#
# Condition, intervention, sponsor and phase: what somebody covering a therapy
# area actually names when they describe the studies they want to watch. Three
# of them are plain query parameters; phase is not, and has to go through the
# advanced filter, which is why the four are assembled here rather than at each
# call site.

# The API's phase codes, in the order a reader expects to see them offered.
PHASE_CODES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"]


def search_params(
    cond: str | None = None,
    intr: str | None = None,
    spons: str | None = None,
    phases=(),
) -> dict:
    """The four search axes as the v2 API's own query parameters.

    A blank axis is left out altogether rather than sent empty, so an empty box
    does not narrow the search to studies whose condition is the empty string.
    An empty result therefore means the reader filled nothing in, which is the
    one query that must not be run.
    """
    params = {}
    for key, value in (
        ("query.cond", cond),
        ("query.intr", intr),
        ("query.spons", spons),
    ):
        if (value or "").strip():
            params[key] = value.strip()
    if phases:
        # Phase has no query parameter of its own; AREA[Phase] is how the
        # advanced filter expresses "any one of these".
        params["filter.advanced"] = "AREA[Phase](" + " OR ".join(phases) + ")"
    return params


def find(
    cond: str | None = None,
    intr: str | None = None,
    spons: str | None = None,
    phases=(),
    limit: int = 50,
) -> list[dict]:
    """Full study records matching the four axes.

    Whole records, not a field subset: what comes back is turned into the same
    profile a monitored trial gets, so the same code reads both.
    """
    return _collect(search_params(cond, intr, spons, phases), limit)


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
