"""Orchestrates monitoring: adding trials, and re-checking them for changes.

The study-fetching function is injectable and defaults to the real API call.
This is the module's only test seam -- tests pass a stub fetcher and never touch
the network.
"""

from __future__ import annotations

import re
import sqlite3
import time
import urllib.error
from collections.abc import Iterator

import ctgov
import diff
import medical_affairs
import storage

NCT_ID = re.compile(r"^NCT\d{8}$")

# Seconds to wait between trials when working through the watchlist. The
# registry is a free public service; a burst of back-to-back requests is rude.
PAUSE = 0.5


class MonitorError(Exception):
    """Something went wrong that the analyst needs to see, in their words."""


def _default_fetch(nct_id: str) -> dict:
    return ctgov.get(nct_id)


def normalise(nct_id: str) -> str:
    """Tidy a pasted ID. Raises MonitorError if it isn't shaped like an NCT ID."""
    cleaned = nct_id.strip().upper()
    if not NCT_ID.match(cleaned):
        raise MonitorError(f"{nct_id.strip()!r} is not an NCT ID (expected e.g. NCT03412565).")
    return cleaned


def _fetch_record(nct: str, fetch) -> dict:
    """Fetch one study, turning every failure into a message an analyst can read.

    Nothing is stored on the way out: a failed fetch leaves the database as it was.
    """
    try:
        record = (fetch or _default_fetch)(nct)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise MonitorError(f"{nct} was not found on ClinicalTrials.gov.") from exc
        raise MonitorError(f"ClinicalTrials.gov returned an error for {nct} ({exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise MonitorError(f"Could not reach ClinicalTrials.gov: {exc.reason}") from exc
    except Exception as exc:
        # A timeout, a TLS failure, a malformed response. The analyst gets a
        # readable message rather than a traceback.
        raise MonitorError(f"Could not fetch {nct}: {exc}") from exc

    if not record or "protocolSection" not in record:
        raise MonitorError(f"ClinicalTrials.gov returned no usable record for {nct}.")
    return record


# --- named lists
#
# A list is what the reader chooses between; a trial belongs to as many of them
# as cover it. Storage owns the rows, and this layer owns the two refusals the
# reader can actually do something about: an unnamed list, and a name taken.


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise MonitorError("Give the list a name.")
    return cleaned


def create_list(conn: sqlite3.Connection, name: str, when: str | None = None) -> int:
    """Make a new named list and return its id."""
    cleaned = _clean_name(name)
    try:
        return storage.create_list(conn, cleaned, when)
    except sqlite3.IntegrityError as exc:
        raise MonitorError(f"There is already a list called “{cleaned}”.") from exc


def rename_list(conn: sqlite3.Connection, list_id: int, name: str) -> None:
    """Give a list a different name, keeping everything in it."""
    cleaned = _clean_name(name)
    try:
        storage.rename_list(conn, list_id, cleaned)
    except sqlite3.IntegrityError as exc:
        raise MonitorError(f"There is already a list called “{cleaned}”.") from exc


def delete_list(conn: sqlite3.Connection, list_id: int) -> None:
    """Remove a list, and stop monitoring whatever no other list still holds."""
    held = [t["nct_id"] for t in storage.list_trials(conn, list_id)]
    storage.delete_list(conn, list_id)
    for nct in held:
        _forget_if_unlisted(conn, nct)


def _forget_if_unlisted(conn: sqlite3.Connection, nct_id: str) -> None:
    """A trial in no list is nobody's business, so it stops being monitored."""
    if not storage.lists_holding(conn, nct_id):
        storage.delete_trial(conn, nct_id)


def _default_list(conn: sqlite3.Connection) -> int:
    """The list a caller that named none means: the oldest one there is.

    A fresh database always has one, but the reader can delete the last list
    while the app is running, so that is answered rather than raised.
    """
    lists = storage.list_lists(conn)
    if not lists:
        raise MonitorError("There are no lists. Make one before adding a trial.")
    return lists[0]["id"]


def add(
    conn: sqlite3.Connection,
    nct_id: str,
    list_id: int | None = None,
    fetch=None,
    when: str | None = None,
) -> str:
    """Put a trial in a list, monitoring it from now if it isn't already.

    A trial monitored under another list *joins* this one: it is not re-fetched
    and its history is not restarted, because that history is the point of
    having monitored it. A trial new to the app records a baseline snapshot
    only, so adding it never reports its monitored fields as changes.

    Returns the normalised NCT ID. Raises MonitorError -- leaving stored state
    untouched -- if the ID is malformed, already in this list, unknown to the
    registry, or the registry can't be reached.
    """
    nct = normalise(nct_id)
    target = _default_list(conn) if list_id is None else list_id

    if storage.is_member(conn, target, nct):
        name = storage.get_list(conn, target)["name"]
        raise MonitorError(f"{nct} is already in “{name}”.")

    stamp = when or storage.now()
    if storage.get_trial(conn, nct) is None:
        record = _fetch_record(nct, fetch)
        storage.add_trial(conn, nct, stamp)
        storage.add_snapshot(conn, nct, record, stamp)
        storage.mark_checked(conn, nct, stamp)

    storage.add_member(conn, target, nct, stamp)
    return nct


def add_many(
    conn: sqlite3.Connection,
    nct_ids,
    list_id: int | None = None,
    fetch=None,
    when: str | None = None,
) -> dict:
    """Put several trials in a list, reporting on each rather than stopping.

    A search returns a screenful at a time, and one unreachable study must not
    cost the reader the other nine, so every trial is attempted and the outcome
    is a summary: which were added, which the list already held, and which
    failed and why.

    Being already in the list is an outcome here rather than the refusal a
    single add raises: adding twenty results of which three are already watched
    is an ordinary thing to do, not a mistake to be corrected.
    """
    target = _default_list(conn) if list_id is None else list_id

    added: list[str] = []
    already: list[str] = []
    failed: list[dict] = []
    for nct_id in nct_ids:
        try:
            nct = normalise(nct_id)
            if storage.is_member(conn, target, nct):
                already.append(nct)
            else:
                added.append(add(conn, nct, target, fetch=fetch, when=when))
        except MonitorError as exc:
            failed.append({"nct_id": str(nct_id).strip(), "detail": str(exc)})

    return {"added": added, "already": already, "failed": failed, "list_id": target}


def add_to_new_list(
    conn: sqlite3.Connection,
    nct_ids,
    name: str,
    fetch=None,
    when: str | None = None,
) -> tuple[dict, int]:
    """Make a list and fill it, as one act. Returns the outcome and the list.

    A list nothing at all landed in is a list nobody asked for, so it goes back
    and the failure is raised. A list that partly filled is kept: the reader
    asked for it by name, and what did arrive is in it.
    """
    cleaned = _clean_name(name)
    made = create_list(conn, cleaned, when)
    outcome = add_many(conn, nct_ids, made, fetch=fetch, when=when)
    if not outcome["added"] and not outcome["already"]:
        delete_list(conn, made)
        raise MonitorError(_why_nothing_landed(outcome, cleaned))
    return outcome, made


def _why_nothing_landed(outcome: dict, list_name: str) -> str:
    """Why a list that was asked for is going back, in one line.

    The first failure, which in a run where every trial failed is almost always
    the whole story, and a count so the reader knows the rest went the same way
    rather than thinking one NCT ID was the whole of it.
    """
    failed = outcome["failed"]
    if not failed:
        return f"Nothing was given to put in “{list_name}”."
    if len(failed) == 1:
        return failed[0]["detail"]
    return f"{failed[0]['detail']} None of the {len(failed)} trials could be added."


def summarise_search(found: dict) -> str:
    """What a completed search found, in one line above the table.

    A capped set says so: a search matching thousands must not read as though
    it matched forty. A search matching nothing says that plainly, because an
    empty table on its own looks like a fault.
    """
    rows = found["rows"]
    if not rows:
        return "Nothing matched. Widen the search."
    if found["capped"]:
        return f"Showing the first {len(rows)} matches of more."
    noun = "match" if len(rows) == 1 else "matches"
    return f"{len(rows)} {noun}."


def summarise_adds(outcome: dict, list_name: str) -> dict:
    """Turn a bulk add into the lines the analyst reads, worded once here.

    A run with a failure in it is never plain good news, for the same reason a
    check run isn't: an outage must not read as "all done".
    """
    added, already, failed = outcome["added"], outcome["already"], outcome["failed"]

    # One trial is named, several are counted: somebody who pasted a single ID
    # wants that ID confirmed back, and somebody who ticked twenty rows wants a
    # number rather than twenty NCT IDs in a sentence.
    parts = []
    if added:
        which = added[0] if len(added) == 1 else f"{len(added)} trials"
        parts.append(f"Now monitoring {which} in “{list_name}”.")
    if already:
        which = f"{already[0]} was" if len(already) == 1 else f"{len(already)} were"
        # Named when it stands alone, because a refusal has to say which list
        # it is talking about; "there" is unambiguous once the line before it
        # has named the list.
        where = "there" if added else f"in “{list_name}”"
        parts.append(f"{which} already {where}.")

    if failed:
        parts.append(f"{len(failed)} could not be added.")
        level = "warning"
    elif added:
        level = "success"
    else:
        level = "warning"

    return {"level": level, "message": " ".join(parts), "failed": failed}


def remove(conn: sqlite3.Connection, nct_id: str, list_id: int) -> None:
    """Take a trial out of one list, leaving any other list holding it alone."""
    nct = normalise(nct_id)
    storage.remove_member(conn, list_id, nct)
    _forget_if_unlisted(conn, nct)


# --- searching the registry
#
# The way onto a list for somebody who does not know the NCT numbers yet. What
# comes back is described in exactly the columns the watchlist uses, because
# the results table is read as the list it feeds and the two must not drift.

# How many results one search shows. Enough that a real query is answered in
# one screenful, few enough that the reader is choosing rather than wading; a
# search matching more than this says so, so a cap never reads as a total.
RESULT_CAP = 40

# The phases a search can name, in the order a reader expects them offered.
# Re-stated here rather than reached for in the client, because which phases
# can be searched on is part of what search() offers its caller.
PHASES = ctgov.PHASE_CODES


def _default_find(**params) -> list[dict]:
    return ctgov.find(**params)


def _identity(profile: dict) -> dict:
    """What identifies a study, in the columns a table shows it in.

    Shared by the watchlist and by search results: a result is judged on the
    same facts a watched trial is listed by, so both are derived here once.
    """
    return {
        "sponsor": profile.get("leadSponsor"),
        # The official title names the study; the brief title is the fallback
        # for a record that carries only one of them.
        "title": profile.get("officialTitle") or profile.get("briefTitle"),
        "phases": profile.get("phases") or [],
        "conditions": profile.get("conditions") or [],
        # The registry repeats an intervention once per arm it appears in;
        # dict.fromkeys dedupes while keeping the registry's order.
        "interventions": list(dict.fromkeys(profile.get("interventions") or [])),
        "status": profile.get("overallStatus"),
    }


def search(
    cond: str = "",
    intr: str = "",
    spons: str = "",
    phases=(),
    limit: int = RESULT_CAP,
    find=None,
) -> dict:
    """Search the registry on condition, intervention, sponsor and phase.

    Any axis may be left blank, but not all of them: a query with nothing in it
    asks for the whole registry, which is never what the reader meant.

    Returns the matching studies as rows, and whether there were more than the
    cap allowed through -- so a search that matched thousands is not shown as
    though it matched forty. Raises MonitorError if the registry can't be
    reached, rather than returning an empty table an outage looks identical to.
    """
    if not any([cond.strip(), intr.strip(), spons.strip(), tuple(phases)]):
        raise MonitorError(
            "Fill in at least one of condition, intervention, sponsor or phase."
        )

    try:
        # One more than the cap, which is how the cap is known to have bitten.
        studies = (find or _default_find)(
            cond=cond, intr=intr, spons=spons, phases=tuple(phases), limit=limit + 1
        )
    except urllib.error.URLError as exc:
        raise MonitorError(f"Could not reach ClinicalTrials.gov: {exc.reason}") from exc
    except Exception as exc:
        raise MonitorError(f"The search failed: {exc}") from exc

    rows = []
    for study in studies[:limit]:
        profile = medical_affairs.profile(study)
        rows.append({"nct_id": profile["nctId"], **_identity(profile)})
    return {"rows": rows, "capped": len(studies) > limit}


def _last_updated(record: dict | None) -> str | None:
    """The registry's own last-updated date for a record, if it states one."""
    if not record:
        return None
    return medical_affairs.profile(record)["lastUpdatePostDate"]


def fields_moved(count: int) -> str:
    """How many monitored fields moved, in the words the analyst reads.

    One phrase, owned here, so the watchlist, the check result and the feed
    never drift apart on how a change is described.
    """
    return f"{count} field{'' if count == 1 else 's'} changed"


def _record_changes(
    conn: sqlite3.Connection,
    nct: str,
    previous: dict | None,
    record: dict,
    when: str,
    synthetic: bool,
) -> int:
    """Store every monitored field that moved between two records.

    A trial with no earlier snapshot has nothing to be compared against, so it
    records a baseline rather than 41 changes.
    """
    if previous is None:
        return 0

    moved = diff.compare(medical_affairs.profile(previous), medical_affairs.profile(record))
    for change in moved:
        storage.add_change(conn, nct, change, when, synthetic=synthetic)
    return len(moved)


def _unchanged(nct: str) -> dict:
    """The result of a check that found the trial standing still.

    Reached two ways -- the registry's stamp ended the check early, or a full
    comparison found nothing -- and said the same way by both.
    """
    return {"nct_id": nct, "outcome": "unchanged", "changes": 0, "detail": "No changes."}


def check(
    conn: sqlite3.Connection,
    nct_id: str,
    fetch=None,
    when: str | None = None,
    force: bool = False,
) -> dict:
    """Re-check one watched trial against the registry.

    The registry publishes its own last-updated date, so that is compared first:
    when it hasn't moved, nothing downstream of it can have moved either, and the
    trial is left alone but marked as checked. This keeps a check cheap as the
    watchlist grows. It is also the one thing that goes stale silently: an edit
    to which fields are monitored, or to how they are derived, invalidates every
    stored profile without touching the registry's stamp. force=True compares
    every field regardless, which is how a stored profile is re-derived.

    Returns a result: nct_id, an outcome, the number of monitored fields that
    moved, and a detail line for the analyst. Three outcomes short of failure,
    because "nobody edited the record" and "somebody edited a part of it we do
    not watch" are different facts:

        unchanged            the registry's own stamp has not moved, or the
                             record does not state one and nothing moved
        no_monitored_change  it has, but nothing monitored moved with it
        updated              at least one monitored field moved

    Raises MonitorError if the trial isn't watched or the registry can't be
    reached, leaving stored state untouched.
    """
    nct = normalise(nct_id)

    if storage.get_trial(conn, nct) is None:
        raise MonitorError(f"{nct} is not on the watchlist.")

    record = _fetch_record(nct, fetch)
    stamp = when or storage.now()

    snapshot = storage.latest_snapshot(conn, nct)
    stored = snapshot["record"] if snapshot else None
    previous = _last_updated(stored)
    current = _last_updated(record)
    # An absent stamp on either side is evidence of nothing: not that the
    # record stood still, and not that it was revised either. So both readings
    # of the stamp need two real dates, and a record without them is compared
    # in full and then reported as plainly unchanged.
    stated = previous is not None and current is not None
    unmoved = stated and previous == current
    revised = stated and previous != current
    if unmoved and not force:
        storage.mark_checked(conn, nct, stamp)
        return _unchanged(nct)

    # A change found against simulated history is itself simulated.
    moved = _record_changes(
        conn,
        nct,
        stored,
        record,
        stamp,
        synthetic=bool(snapshot and snapshot["synthetic"]),
    )
    # A forced check that found nothing has re-fetched the record the baseline
    # already holds, so there is nothing new to keep. Storing it anyway would
    # grow a snapshot per forced check and, worse, advance the stored registry
    # stamp past the change the watchlist is still reporting.
    if revised or moved:
        storage.add_snapshot(conn, nct, record, stamp)
    storage.mark_checked(conn, nct, stamp)

    if moved:
        return {
            "nct_id": nct,
            "outcome": "updated",
            "changes": moved,
            "detail": f"{fields_moved(moved)}.",
        }
    if revised:
        return {
            "nct_id": nct,
            "outcome": "no_monitored_change",
            "changes": 0,
            "detail": "The registry record has been revised, but no monitored field moved.",
        }
    return _unchanged(nct)


def check_all(
    conn: sqlite3.Connection,
    list_id: int | None = None,
    fetch=None,
    when: str | None = None,
    pause: float = PAUSE,
    force: bool = False,
) -> Iterator[dict]:
    """Re-check watched trials, yielding one result as each finishes.

    Everything monitored, or only what one named list holds -- the reader is
    looking at one list, so that is what "check all" means to them.

    Yielding rather than returning a list lets the page show progress while the
    run is still going. Trials are taken one at a time with a pause between
    them, and a trial that fails is reported as its own result rather than
    ending the run.
    """
    for index, trial in enumerate(storage.list_trials(conn, list_id)):
        if index:
            time.sleep(pause)
        nct = trial["nct_id"]
        try:
            result = check(conn, nct, fetch=fetch, when=when, force=force)
        except MonitorError as exc:
            result = {"nct_id": nct, "outcome": "error", "changes": 0, "detail": str(exc)}
        yield result


def summarise(results: list[dict]) -> dict:
    """Turn a completed run into the one line the analyst reads.

    A run with a failure in it is never reported as plain good news: an outage
    must not be mistaken for "nothing changed".

    A record revised outside what is monitored gets its own line rather than
    being folded into either. It is not news the analyst must act on, so it is
    not a warning; but it is not "nothing happened" either, because the sponsor
    did edit the record.
    """
    failed = [r for r in results if r["outcome"] == "error"]
    updated = [r for r in results if r["outcome"] == "updated"]
    unmonitored = [r for r in results if r["outcome"] == "no_monitored_change"]
    checked = len(results) - len(failed)
    noun = "trial" if checked == 1 else "trials"
    # Said the same way wherever it appears, so the two messages that can carry
    # it read alike.
    aside = f" {len(unmonitored)} revised, but no monitored field moved."

    if failed:
        message = (
            f"Checked {checked} of {len(results)} trials. "
            f"{len(failed)} could not be reached."
        )
        level = "warning"
    elif updated:
        message = f"Checked {checked} {noun}. {len(updated)} revised on the registry."
        if unmonitored:
            message += aside
        level = "warning"
    elif unmonitored:
        message = f"Checked {checked} {noun}.{aside}"
        level = "info"
    else:
        message = f"Checked {checked} {noun} — no changes."
        level = "success"

    return {
        "level": level,
        "message": message,
        "updated": updated,
        "unmonitored": unmonitored,
        "failed": failed,
    }


def profile_of(conn: sqlite3.Connection, nct_id: str) -> dict | None:
    """The monitored profile derived from a trial's newest stored snapshot."""
    snapshot = storage.latest_snapshot(conn, nct_id)
    return medical_affairs.profile(snapshot["record"]) if snapshot else None


def feed(conn: sqlite3.Connection, list_id: int | None = None) -> list[dict]:
    """Events for the activity feed, most recent first.

    The feed names trials, not fields: every field that moved in one check of
    one trial collapses into a single entry, so a sponsor revising fifteen
    fields at once doesn't bury everything else.

    Narrowed to one list when asked, so the feed under a list is about the
    trials in it rather than about everything the app watches.
    """
    watched = storage.list_trials(conn, list_id)
    shown = {t["nct_id"] for t in watched}
    events = [
        {
            "at": t["monitoring_began"],
            "nct_id": t["nct_id"],
            "kind": "started monitoring",
            # Not something there is anything to review, so never flagged as new.
            "synthetic": False,
            "reviewed": True,
        }
        for t in watched
    ]

    detections: dict[tuple[str, str], list[dict]] = {}
    for change in storage.list_changes(conn):
        if change["nct_id"] not in shown:
            continue
        detections.setdefault((change["nct_id"], change["detected_at"]), []).append(change)

    for (nct, at), changes in detections.items():
        events.append(
            {
                "at": at,
                "nct_id": nct,
                # Counted as the entry names it: a date and its type moving
                # together are one event, not two fields.
                "kind": fields_moved(len(diff.fold_qualifiers(c["field"] for c in changes))),
                "synthetic": any(c["synthetic"] for c in changes),
                "reviewed": all(c["reviewed"] for c in changes),
            }
        )

    return sorted(events, key=lambda e: e["at"], reverse=True)


def marked_profile(conn: sqlite3.Connection, nct_id: str) -> dict:
    """A trial's monitored profile, marked up with what has moved.

    Returns the profile itself, for a caller wanting a field by name, one row
    per field marked with whether it moved and what it moved from, and how much
    is still awaiting review. Every field is included, not only the ones that
    moved, so a change is read in the context of the study around it.

    The outstanding count comes from the stored records rather than from the
    marked rows: a change recorded against a field since dropped from the
    monitored set has nothing left to highlight, but must still be clearable.
    """
    profile = profile_of(conn, nct_id) or {}
    return {
        "profile": profile,
        "rows": diff.annotate(profile, storage.list_changes(conn, nct_id)),
        "unreviewed": storage.count_unreviewed(conn, nct_id),
    }


def last_change(conn: sqlite3.Connection, nct_id: str) -> dict | None:
    """What is outstanding on this trial, or None if it has never changed.

    Everything still awaiting review, however many checks those moves are
    spread across. This is the column an analyst scans across thirty trials, so
    reporting only the newest check would drop a completion date that slipped
    on Monday the moment a title typo is corrected on Wednesday.

    Once everything has been read there is nothing outstanding, but "what has
    changed on this trial" stays a fair question, so it falls back to the
    newest check. Fields are ordered high-signal first, so a caller showing
    only the first few never drops a slipped completion date, a moved endpoint
    or an amended eligible population for a typo fix.
    How much is unread is a separate question, answered by marked_profile.
    """
    changes = storage.list_changes(conn, nct_id)
    if not changes:
        return None

    shown = [c for c in changes if not c["reviewed"]]
    if not shown:
        newest = changes[0]["detected_at"]
        shown = [c for c in changes if c["detected_at"] == newest]

    return {
        # The newest of the moves being named, so a column of old news is not
        # dated as though it landed today.
        "at": max(c["detected_at"] for c in shown),
        # A field that moved twice is one entry: changes come newest first, so
        # the first sighting of each name is its most recent move. So is a date
        # or an enrolment figure that moved between estimated and actual: the
        # value and its type are folded into one name.
        "fields": diff.by_signal(diff.fold_qualifiers(c["field"] for c in shown)),
        # A detection is simulated if any part of it was.
        "synthetic": any(c["synthetic"] for c in shown),
    }


def watchlist(conn: sqlite3.Connection, list_id: int | None = None) -> list[dict]:
    """One row per watched trial: what identifies it, and what is outstanding.

    Everything monitored, or only what one named list holds.

    Two dates travel with each row and are read as a pair: when the sponsor
    revised the record, and when this tool noticed. Only the second is the
    row's own history; the first is the registry's, taken from the newest
    stored snapshot.

    The whole of the watchlist table, derived here rather than in the page, so
    the table can be tested without running Streamlit and a later move off
    Streamlit rewrites only the rendering.
    """
    rows = []
    for trial in storage.list_trials(conn, list_id):
        nct = trial["nct_id"]
        profile = profile_of(conn, nct) or {}
        rows.append(
            {
                "nct_id": nct,
                **_identity(profile),
                # When the sponsor last revised the record, which is not when
                # this tool noticed: a list checked weekly can meet a
                # fortnight-old revision.
                "registry_updated": profile.get("lastUpdatePostDate"),
                "last_checked": trial["last_checked"],
                "last_reviewed": trial["last_reviewed"],
                "unreviewed": storage.count_unreviewed(conn, nct),
                "synthetic": storage.is_synthetic(conn, nct),
                "change": last_change(conn, nct),
            }
        )
    return rows

def review(conn: sqlite3.Connection, nct_id: str, when: str | None = None) -> int:
    """Mark a trial's outstanding changes as read, clearing its highlighting.

    Nothing is deleted: the change records are the trial's history, and a later
    move highlights it afresh. Returns how many records were marked. Raises
    MonitorError if the trial isn't watched.
    """
    nct = normalise(nct_id)

    if storage.get_trial(conn, nct) is None:
        raise MonitorError(f"{nct} is not on the watchlist.")

    return storage.mark_reviewed(conn, nct, when)
