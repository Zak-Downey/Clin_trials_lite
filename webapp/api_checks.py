"""Checking a watchlist for updates: a run on a server thread, and its progress.

A run is kept in memory, one per watchlist, and the page polls it. What a check
means (failures recorded per trial, the last-checked time, who Retry failed
re-checks) is in `monitor`; this module only runs the steps in the background,
keeps one run at a time per watchlist and reports progress.
"""

from __future__ import annotations

import threading
import time

import ctgov
import monitor
import storage

from .errors import ApiError
from .times import local


class Run:
    def __init__(self, list_id: int, kind: str, steps: list[tuple[str, str | None]]):
        self.list_id = list_id
        self.kind = kind  # "check", "recheck" or "retry"
        self.steps = steps  # ("trial", nct) ... then ("search", None)
        self.processed = 0
        self.results: list[dict] = []
        self.running = True
        self.finished_at: str | None = None
        self.crashed: str | None = None
        self.skipped = 0  # trial steps dropped because the watchlist no longer held the trial


def _runs(ctx) -> dict:
    if not hasattr(ctx, "runs"):
        ctx.runs = {}
    return ctx.runs


def _require(ctx, list_id: int) -> None:
    if storage.get_list(ctx.conn, list_id) is None:
        raise ApiError(404, "watchlist_not_found", f"There is no watchlist {list_id}.")


def _unlocked(ctx, call):
    """Wrap a registry call so the database lock is released while it waits on the network."""

    def wrapper(*args, **kwargs):
        ctx.lock.release()
        try:
            return call(*args, **kwargs)
        finally:
            ctx.lock.acquire()

    return wrapper


class _Removed(BaseException):
    """(Not an Exception, so the check's own failure handling lets it through.) The watchlist stopped holding a trial while its fetch waited on the network."""


def _work(ctx, run: Run, force: bool) -> None:
    fetch = _unlocked(ctx, ctx.fetch or ctgov.get)
    find = _unlocked(ctx, ctx.find or ctgov.find)
    pause = getattr(ctx, "pause", monitor.PAUSE)
    try:
        for index, (kind, nct) in enumerate(run.steps):
            if index:
                time.sleep(pause)
            with ctx.lock:
                if storage.get_list(ctx.conn, run.list_id) is None:
                    break  # the watchlist was deleted while the run waited
                if kind == "trial" and not storage.is_member(ctx.conn, run.list_id, nct):
                    run.skipped += 1  # removed from this watchlist since the run began
                    run.processed = index + 1
                    continue
                if kind == "trial":

                    def held_fetch(n, nct=nct):
                        record = fetch(n)  # the lock is retaken here
                        if not storage.is_member(ctx.conn, run.list_id, nct):
                            raise _Removed(nct)
                        return record

                    try:
                        result = monitor.check_one(ctx.conn, nct, fetch=held_fetch, force=force)
                    except _Removed:
                        run.skipped += 1
                        run.processed = index + 1
                        continue
                else:
                    result = monitor.find_new(ctx.conn, run.list_id, find=find)
                if result is not None:
                    run.results.append(result)
                run.processed = index + 1
    except Exception as err:  # the run must end, or the watchlist could never be checked again
        run.crashed = str(err)
    finally:
        try:
            with ctx.lock:
                if storage.get_list(ctx.conn, run.list_id) is not None:
                    monitor.finish_run(ctx.conn, run.list_id, run.results)
                    run.finished_at = storage.last_check_run(ctx.conn, run.list_id)["finished"]
        finally:
            run.running = False


def _start(ctx, list_id: int, kind: str, trials: list[str], search: bool, force: bool) -> dict:
    runs = _runs(ctx)
    current = runs.get(list_id)
    if current is not None and current.running:
        raise ApiError(409, "check_running", "A check for this watchlist is already running.")
    steps = [("trial", n) for n in trials] + ([("search", None)] if search else [])
    run = runs[list_id] = Run(list_id, kind, steps)
    if not steps:
        monitor.finish_run(ctx.conn, list_id, [])
        run.finished_at = storage.last_check_run(ctx.conn, list_id)["finished"]
        run.running = False
    else:
        threading.Thread(target=_work, args=(ctx, run, force), daemon=True).start()
    return _state(ctx, list_id)


def start(ctx, list_id: str, force: bool = False, **_):
    """A normal check, or with force a full recheck (its own kind, so the page labels it)."""
    list_id = int(list_id)
    _require(ctx, list_id)
    trials = [t["nct_id"] for t in storage.list_trials(ctx.conn, list_id)]
    searching = monitor.remembered_search(ctx.conn, list_id) is not None
    return _start(ctx, list_id, "recheck" if force else "check", trials, searching, force)


def recheck(ctx, list_id: str, **_):
    """A full recheck: every monitored field compared, not only when the registry's stamp moved."""
    return start(ctx, list_id, force=True)


def retry(ctx, list_id: str, **_):
    list_id = int(list_id)
    _require(ctx, list_id)
    current = _runs(ctx).get(list_id)
    if current is not None and current.running:
        raise ApiError(409, "check_running", "A check for this watchlist is already running.")
    failed = monitor.failed_in_last_run(ctx.conn, list_id)
    if not failed:
        raise ApiError(409, "nothing_to_retry", "No trial failed in the last check.")
    return _start(ctx, list_id, "retry", failed, False, False)


def progress(ctx, list_id: str, **_):
    list_id = int(list_id)
    _require(ctx, list_id)
    return _state(ctx, list_id)


def _state(ctx, list_id: int) -> dict:
    run = _runs(ctx).get(list_id)
    retryable = len(monitor.failed_in_last_run(ctx.conn, list_id))
    if run is None:
        return {"state": "idle", "retryable": retryable}
    trial_steps = [s for s in run.steps if s[0] == "trial"]
    trials = [r for r in run.results if r.get("kind") != "search"]
    search = next((r for r in run.results if r.get("kind") == "search"), None)
    failed = [r for r in trials if r["outcome"] == "error"]
    updated = [r for r in trials if r["outcome"] == "updated"]
    upcoming = run.steps[run.processed] if run.processed < len(run.steps) else None
    state = {
        "state": "running" if run.running else "complete",
        "kind": run.kind,
        "total": len(trial_steps) - run.skipped,
        "processed": len(trials),
        "checked": len(trials) - len(failed),
        "failed": len(failed),
        "changed": len(updated),
        "steps": len(run.steps),
        "steps_done": run.processed,
        "next": None if upcoming is None else {"kind": upcoming[0], "nct_id": upcoming[1]},
        "has_search": any(s[0] == "search" for s in run.steps),
        "trials": [
            {
                "nct_id": r["nct_id"],
                "outcome": r["outcome"],
                "error_kind": r.get("error_kind"),
                "detail": r["detail"],
            }
            for r in trials
        ],
        "search": None
        if search is None
        else {"outcome": search["outcome"], "detail": search["detail"], "found": len(search["found"])},
        "finished_at": local(run.finished_at),
        "crashed": run.crashed,
        "retryable": retryable,
    }
    if not run.running:
        if failed or run.crashed or (search is not None and search["outcome"] == "error"):
            state["state"] = "incomplete"
        changed_ids = {r["nct_id"] for r in updated}
        state["still_need_review"] = sum(
            1 for e in monitor.needs_review(ctx.conn, list_id) if e["nct_id"] not in changed_ids
        )
    return state
