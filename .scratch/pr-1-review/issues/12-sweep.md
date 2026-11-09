# 12: Sweep: the stand-ins rows, the setup notes and the walk tightenings

**Blocked by:** 10

**Status:** needs-triage

**Touches:** docs/agents/local/repo.md, requirements-dev.txt, README.md, walks/test_check_walk.py, walks/test_walk_guards.py, walks/test_acceptance_walk.py

**Spec sections (read these, not this ticket's paraphrase):** `ranked.md` › Sweep (each box names its finding and source).

**What to build:** Mechanical changes inside one file each, with no change in what the app does. One box per sweep finding in `ranked.md`.

- [ ] `docs/agents/local/repo.md`: "Find trials (not built yet)" is gone; the stub fetcher/finder row names every endpoint that calls the registry, adds the `find_page` stub (`tests/test_api_search.py:24`) and says what checks the stubs; the stand-in registry row lists the `fail` switch; a row for the monkeypatched `time.sleep` in `tests/test_api_checks.py` and `tests/test_check_trials.py` names the walks' real sleep as its check (sweep S-1: server-and-domain 5, walks-and-retirement S4)
- [ ] Test: `ctgov.find_page` over a stubbed `_get` asks for `pageSize = page * 10` and returns the page's ten, and `totalCount` (sweep S-2: server-and-domain 5)
- [ ] `docs/agents/local/repo.md`'s stand-in registry row says it ignores every search parameter but `query.cond` (`many`, `nothing`) and paging; walk: a filtered search (a phase, a status and a start-date range) reaches the stand-in with those parameters in its recorded request (sweep S-3: walks-and-retirement S3)
- [ ] `requirements-dev.txt` installs both `chromium` and `webkit`, and the README names the walk suite, `requirements-dev.txt` and the browser install (sweep S-4: walks-and-retirement S5)
- [ ] Walk: pressing Check for updates while a check runs starts no second check and shows no error banner (sweep S-5: walks-and-retirement S6)
- [ ] Walk: the WebKit acceptance run asserts the copy notice reads "Summary copied." (sweep S-6: walks-and-retirement N1)
- [ ] Walk: each guard test matches its guard's message inside its own failure block, not anywhere in the combined output (sweep S-7: walks-and-retirement N4)

## Comments
