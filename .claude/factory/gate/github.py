"""The repository's GitHub Actions usage and storage (`gate.py github`).

Endpoints, all through `gh api`. Read against GitHub's documentation on 2026-11-08, API version 2026-03-10
(https://docs.github.com/en/rest/billing/usage and its automating-usage-reporting tutorial):

- `GET /users/{owner}` for the owner's `type` ("Organization" selects the organisation form).
- `GET /users/{owner}/settings/billing/usage?year=Y&month=M`, or
  `GET /organizations/{owner}/settings/billing/usage?year=Y&month=M` for an organisation: the billing usage
  report, `usageItems` with date, product, sku, quantity, unitType, pricePerUnit, grossAmount, discountAmount,
  netAmount and repositoryName. Sent with the header `X-GitHub-Api-Version: 2026-03-10`. The docs say it takes
  a personal access token (classic), not a fine-grained one, and access is by role: the account holder for a
  user, an organisation owner or billing manager for an organisation. The user form needs the enhanced billing
  platform, and a 404 can mean that. `repositoryName` is matched as `repo` or `owner/repo`.
- `GET /repos/{owner}/{repo}/actions/artifacts?per_page=100&page=N`: the summed `size_in_bytes` of the
  artifacts that have not expired, every page followed until one holds fewer than 100.
- `GET /repos/{owner}/{repo}/actions/cache/usage`: `active_caches_size_in_bytes`.

Every failure is soft: one line printed, exit 0. The whole step has a deadline (DEADLINE seconds); `gh` not
answering is said as such, not as being signed out.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import time

from gate.dashboard import read_jsonl
from gate.git import run_git

API_VERSION = "2026-03-10"
LOCAL = os.path.join("docs", "agents", "local")
REMOTE = re.compile(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")
USAGE_FIELDS = ("date", "product", "sku", "quantity", "unitType", "netAmount", "repositoryName")
DEADLINE = 120
CALL_TIMEOUT = 60
AUTH_TIMEOUT = 20
CLASSIC = ("github: billing usage was refused (403): it needs a personal access token (classic), not a fine-grained one, "
           "from the account holder, or an organisation owner or billing manager; storage only")
_started = [0.0]


def _timeout(limit: float) -> float:
    """The call's timeout: its limit, or what is left of the deadline (at least a second)."""
    return max(1.0, min(limit, _started[0] + DEADLINE - time.monotonic()))


def gh(*args: str):
    """Run `gh`; (parsed JSON or None, error text)."""
    try:
        result = subprocess.run(["gh"] + list(args), capture_output=True, text=True, timeout=_timeout(CALL_TIMEOUT))
    except subprocess.TimeoutExpired:
        return None, "gh did not answer"
    except Exception as err:
        return None, str(err)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip()
    try:
        return json.loads(result.stdout), ""
    except ValueError:
        return None, "unreadable answer"


def api(path: str, *extra: str):
    return gh("api", "-H", "X-GitHub-Api-Version: " + API_VERSION, *extra, path)


def billing_note(error: str, owner: str) -> str:
    """The one line for a billing call that failed."""
    status = re.search(r"\b(40[13])\b", error)
    if status or "Resource not accessible" in error:
        return CLASSIC.replace("(403)", "(%s)" % (status.group(1) if status else "403"))
    if "404" in error:
        return "github: the billing report is not available for %s; storage only" % owner
    return "github: billing usage not read (%s)" % (error.splitlines() or ["no answer"])[0][:100]


def cmd_github(root: str, config: dict, year: int, month: int) -> int:
    """Fetch and record the usage for the month (year and month None: the current one)."""
    match = REMOTE.search(run_git(root, "remote", "get-url", "origin") or "")
    if not match:
        print("github: no GitHub remote (origin); nothing recorded")
        return 0
    if not shutil.which("gh"):
        print("github: gh is not on PATH; nothing recorded")
        return 0
    _started[0] = time.monotonic()
    try:
        auth = subprocess.run(["gh", "auth", "status", "--hostname", "github.com"], capture_output=True, text=True,
                              timeout=float(os.environ.get("GATE_GH_AUTH_TIMEOUT") or AUTH_TIMEOUT))
    except subprocess.TimeoutExpired:
        print("github: gh did not answer; nothing recorded")
        return 0
    if auth.returncode != 0:
        said = (auth.stderr or auth.stdout).strip()
        if not said or re.search(r"not logged in", said, re.I):
            print("github: gh is signed out (run gh auth login); nothing recorded")
        else:
            lines = [l.strip() for l in said.splitlines() if l.strip()]
            cause = next((l for l in lines if l.startswith("X")), lines[0]).removeprefix("X").strip()
            print("github: gh auth status failed (%s); nothing recorded" % cause[:100])
        return 0
    owner, repo = match.group(1), match.group(2)
    if year is None:
        today = datetime.date.today()
        year, month = today.year, today.month
    local = os.path.join(root, LOCAL)
    os.makedirs(local, exist_ok=True)
    notes = []

    owner_info, _ = api("/users/" + owner)
    usage = ""
    if not isinstance(owner_info, dict) or not owner_info.get("type"):
        usage = "github: the owner's type could not be read; billing usage skipped, storage only"
    else:
        kind = "organizations" if owner_info.get("type") == "Organization" else "users"
        report, error = api("/%s/%s/settings/billing/usage?year=%d&month=%d" % (kind, owner, year, month))
        if report is None:
            usage = billing_note(error, owner)
        else:
            prefix = "%04d-%02d" % (year, month)
            path = os.path.join(local, "github.jsonl")
            old, skipped = read_jsonl(path)
            keep = [json.dumps(r) for r in old if not str(r.get("date", "")).startswith(prefix)]
            names = {repo.lower(), ("%s/%s" % (owner, repo)).lower()}
            items = report.get("usageItems", [])
            new = [json.dumps({k: item.get(k) for k in USAGE_FIELDS}) for item in items if str(item.get("repositoryName", "")).lower() in names]
            if items and not new:
                usage = "github: no usage item matched %s/%s; the month's recorded lines are kept" % (owner, repo)
            else:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("".join(line + "\n" for line in keep + new))
            if skipped:
                print("github: dropped %d unreadable line(s) from github.jsonl" % skipped)
    if usage:
        notes.append(usage)

    artifacts, a_err = {"artifacts": []}, ""
    for page in range(1, 101):
        if time.monotonic() > _started[0] + DEADLINE:
            artifacts, a_err = None, "gh did not answer within the deadline"
            break
        batch, a_err = api("/repos/%s/%s/actions/artifacts?per_page=100&page=%d" % (owner, repo, page))
        if batch is None:
            artifacts = None
            break
        artifacts["artifacts"] += batch.get("artifacts", [])
        if len(batch.get("artifacts", [])) < 100:
            break
    caches, c_err = api("/repos/%s/%s/actions/cache/usage" % (owner, repo))
    if artifacts is None or caches is None:
        notes.append("github: storage not read (%s)" % ((a_err or c_err).splitlines() or ["no answer"])[0][:100])
        stale = os.path.join(local, "github-storage.json")
        if not os.path.isfile(stale) and usage:
            with open(stale, "w", encoding="utf-8") as handle:
                json.dump({"usage": usage}, handle)
                handle.write("\n")
        elif os.path.isfile(stale):
            try:
                with open(stale, encoding="utf-8") as handle:
                    kept = json.load(handle)
                if isinstance(kept, dict):
                    kept.pop("usage", None)
                    if usage:
                        kept["usage"] = usage
                    with open(stale, "w", encoding="utf-8") as handle:
                        json.dump(kept, handle)
                        handle.write("\n")
            except (OSError, ValueError):
                pass
    else:
        storage = {
            "artifacts_bytes": sum(a.get("size_in_bytes", 0) for a in artifacts.get("artifacts", []) if not a.get("expired")),
            "caches_bytes": caches.get("active_caches_size_in_bytes", 0),
            **({"usage": usage} if usage else {}),
            "fetched": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(os.path.join(local, "github-storage.json"), "w", encoding="utf-8") as handle:
            json.dump(storage, handle)
            handle.write("\n")
    for note in notes:
        print(note)
    if not notes:
        print("github: %s/%s %04d-%02d recorded" % (owner, repo, year, month))
    return 0
