# Code review: main...HEAD (feature html-front-end)

## Standards

Sampled webapp/*.py (api_checks, api_membership, api_search, api_summary, api_watchlists, api_new_matches, api_saved_search, api_trials) and the webapp/static/views JS. No hard violations of a documented standard: no coding-standards file exists, and CONTEXT.md, the ADRs and repo.md describe tooling, not code style. CONTEXT.md vocabulary against the code, and ticket-format compliance, were not checked. All findings below are judgement-call smells.

**Duplicated Code (the strongest finding)**
- The `el` DOM helper is copy-pasted as `const el = (tag, attrs = {}, ...kids) => {...}` in 12 files: all views except `dialog`, `tabs` and `menu_keys` (`trial.js`, `check.js`, `find.js`, `summary.js`, `add_by_id.js`, `all_trials.js`, `needs_review.js`, `new_matches.js`, `new_watchlist.js`, `saved_search.js`, `watchlist_menu.js`, `registry_trial.js`). `app.js` has a variant, `el = (tag, attrs = {})`, which takes no children. `plural` is also defined locally in `trial.js`. Extract both to a shared module, for example `/static/dom.js`. Also Shotgun Surgery: changing attribute handling means 13 edits.
- The "watchlist exists else 404" guard is written five times with the same message, `raise ApiError(404, "watchlist_not_found", f"There is no watchlist {list_id}.")`: `api_watchlists._require(conn, list_id)`, `api_checks._require(ctx, list_id)`, inline in `api_membership.add_trials`, inline in `api_summary.summary`, inline at `api_membership.py:105`. The two `_require` helpers have different signatures (`conn` vs `ctx`). Reuse `api_watchlists._require` everywhere.
- The lock-release pattern repeats (`ctx.lock.release()` ... `finally: ctx.lock.acquire()`) in `api_checks._unlocked`, `api_membership._fetch_outside_lock` and `api_search.py:32`. A shared context manager such as `ctx.unlocked()` would replace all three.
- Mysterious Name: `api_trials._require(ctx, nct_id)` shares a name with the watchlist `_require` helpers but validates and returns an NCT ID. Consider `_require_trial` and `_require_watchlist`.

**Feature Envy / Message Chains**
- `api_membership` and `api_search` call underscore-private members of `monitor` from outside the module: `monitor._default_fetch`, `monitor._fetch_record` and `monitor._refuse_unanswerable`. Expose public functions in `monitor`.
- `registry_trial` in `api_membership.py` (lines 68-75) re-wraps a fetched value or exception into a lambda or `raise_it` closure just to feed `_fetch_record`. `add_trials` does the same with its `replay` closure. Having `monitor` accept an already-fetched result or exception would remove it.

**Primitive Obsession (minor)**
- `Run.steps` is `list[tuple[str, str | None]]`, using `("trial", nct)` and `("search", None)` as tagged tuples. `Run.kind` is a bare string ("check", "recheck", "retry"). A small dataclass or enum would be clearer.
- Handlers repeat `int(list_id)` on each call, which a router-level coercion would remove.

**Divergent Change / size (judgement)**
- `find.js` (317 lines), `trial.js` (279) and `monitor.py` (+363) each mix rendering, state and API orchestration. This was a skim, not a deep read.

**Speculative Generality**
- None found.

## Spec

Reviewed from source; no code or walk was run, so "implemented" means "present in source". Coverage is broad. No clear missing requirement. The items under (c) are unconfirmed suspicions.

**(a) Missing or partial**
- The hand-over ticket is open. End State 6: "the user has started the app with the README's command, clicked through the acceptance journey in their own browser (Safari included), and ticked it." `issues/17-hand-over.md` is `ready-for-human`.
- Nine exploration findings are open (listed in the spec's Further Notes). The spec allows this under End State 5, but they are visible defects. Examples: a summary URL with unusable custom dates replaces the whole tab with a bare message; the CSV does not escape cells starting with `=`; a failed action with the server stopped shows "Failed to fetch".
- Story 87: the summary has "how many checks found changes". Not confirmed that `webapp/static/views/summary.js` shows that count.

**(b) Scope creep**
- Mostly none. The server rejects non-local hosts (`webapp/server.py`: Host-header check and `make_server` host restriction); this serves story 101's "reachable only from my own machine", so it is justified.
- Stray ignored local files: `PROTOTYPE_card_history_wipe_me.db` and a root `views/` directory (only `__pycache__`). `views/` should be removed; End State 2 forbids old Streamlit view modules.

**(c) Implemented but possibly wrong**
- Story 100a and decision 12: "in my machine's local time zone, named in the summary line". `webapp/api_summary.py` computes the zone name as `datetime.datetime.now().astimezone().tzname()`, today's abbreviation, which can disagree with the zone of a date in the other half of a daylight-saving year. Conversion via `webapp/times.py` not verified.
- Story 84 and design 10/2 (Custom dates: "old summary kept until valid"). `_period` raises a 400 for bad or missing custom dates, and exploration finding summary 4 confirms a bad address blanks the tab. The in-page Apply path may be correct; the deep-link and reload path is not.
- Story 8: the app never switches tabs by itself. Ticket 16 patched focus loss on redraw; the tab-memory rule itself was not verified.
- Story 55: CSV carries "exact values". `briefing.as_csv` runs titles through `display.collapse(display.show(...))`, which may alter whitespace.
- Story 4 / End State 4: `walks/test_acceptance_walk.py` exists. Not checked that it is keyboard-only, nor that it runs at 1440 and 1024 in Chromium and at 1440 in WebKit.

## Summary

Standards: 10 findings (all judgement calls; worst: Duplicated Code, `el` helper copied in 13 files). Spec: 11 findings (worst: nine open exploration defects, including the blanked summary tab on bad custom-date URLs).
