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
    params = {
        "query.cond": cond,
        "query.term": term,
        "query.intr": intr,
        "fields": ",".join(fields) if fields else None,
        **{k.replace("_", "."): v for k, v in extra.items()},
    }

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
