# 07: The unused settings leave

**What to build:** `display.py` holds three settings no page has used for some time: `DATE_FORMAT`, `INPUT_DATE_FORMAT` and `COLUMN_WIDTHS` (found by `review-whole-07` of `kit-phase-4`, when the comments above them were removed and nothing explained them). First show that nothing reads them: search the app's modules, the tests, the browser tests and the scripts and pages under `webapp/static/` for each name and for anything built from it, and put the searches and their results in the comments. Then remove the three, and anything that exists only to serve them (a helper, an import, a test that tests only them). If one of them does have a reader, leave that one, and say which and what reads it. Nothing else in `display.py` changes. Give `review-whole-07` its outcome in `.scratch/kit-phase-4/fates.jsonl` only if that file's own rules allow a later build to; otherwise say in `now_what` that it is now done. Spec: `.scratch/kit-phase-5/spec.md`, "The unused settings".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The comments hold the search for each of the three names and what it found
- [x] Each setting with no reader is gone, with anything that only served it; one with a reader is left and named
- [x] The map of the pages, the list of deliberate breaks and the linter are still green: no entry pointed at what was removed
- [x] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments

### The search (run on 2b885ab, before the removal)

Each name, whole word, across the app's modules, the tests, the walks, the pages' scripts and pages, the map of the pages, the list of deliberate breaks, the linter's settings and the GitHub workflow:

```
grep -rnw "$n" *.py webapp tests walks docs/agents/local/walk-map.json docs/agents/local/breaks.json ruff.toml .github
```

- `DATE_FORMAT`: `display.py:340` (the setting itself) and `tests/test_display.py:235-236`, in `test_the_date_column_spells_the_month_out`, which tests only that setting's text. No module and no page reads it.
- `INPUT_DATE_FORMAT`: `display.py:342` only.
- `COLUMN_WIDTHS`: `display.py:551` only.

Anything built from them (another spelling, a read by name, or the values themselves):

```
grep -rn -i "date_format\|column_widths\|columnwidths\|dateformat\|MMMM\|DD/MM\|\"large\"\|'large'" *.py webapp tests walks docs/agents/local/walk-map.json docs/agents/local/breaks.json ruff.toml .github
git ls-files | grep -v '^\.scratch' | xargs grep -n -i "getattr(display\|vars(display\|display\.__dict__\|date_format\|column_widths\|MMMM\|DD/MM"
```

Found only the same lines in `display.py` and `tests/test_display.py:235-236`; nothing reads `display` by a computed name.

### What went

- `DATE_FORMAT`, `INPUT_DATE_FORMAT` and `COLUMN_WIDTHS` from `display.py`.
- `tests/test_display.py::test_the_date_column_spells_the_month_out`, which tested only `DATE_FORMAT`. The month is still spelled out on the page by `display.long_date`, which this ticket leaves alone.
- No setting had a reader, so none is left.

`python3 checks.py unit` was green before and after the removal.

`review-whole-07` of `kit-phase-4` keeps its fate `left`: the rules for `fates.jsonl` in `.claude/skills/implement-spec/SKILL.md` record what happened in that build and give no later build leave to change it, so the hand-over's `now_what` says it is now done.

A full `python3 checks.py` on d817a92 (same code as this commit; only this ticket file changed since) ended green in 2.1 min: lint, patterns, escapes, unit and walks all green.
