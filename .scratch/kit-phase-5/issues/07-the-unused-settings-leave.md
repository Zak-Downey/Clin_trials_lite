# 07: The unused settings leave

**What to build:** `display.py` holds three settings no page has used for some time: `DATE_FORMAT`, `INPUT_DATE_FORMAT` and `COLUMN_WIDTHS` (found by `review-whole-07` of `kit-phase-4`, when the comments above them were removed and nothing explained them). First show that nothing reads them: search the app's modules, the tests, the browser tests and the scripts and pages under `webapp/static/` for each name and for anything built from it, and put the searches and their results in the comments. Then remove the three, and anything that exists only to serve them (a helper, an import, a test that tests only them). If one of them does have a reader, leave that one, and say which and what reads it. Nothing else in `display.py` changes. Give `review-whole-07` its outcome in `.scratch/kit-phase-4/fates.jsonl` only if that file's own rules allow a later build to; otherwise say in `now_what` that it is now done. Spec: `.scratch/kit-phase-5/spec.md`, "The unused settings".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The comments hold the search for each of the three names and what it found
- [ ] Each setting with no reader is gone, with anything that only served it; one with a reader is left and named
- [ ] The map of the pages, the list of deliberate breaks and the linter are still green: no entry pointed at what was removed
- [ ] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments
