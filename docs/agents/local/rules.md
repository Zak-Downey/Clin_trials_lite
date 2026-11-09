# Rule queue

Rules proposed after an escape, waiting for the user to adopt or retire them. `python3 .claude/factory/gate.py handover <feature>` lists every row that is neither adopted nor retired. One row each.

| id | rule | kind | escape ids | proposed | adopted | review by | retired |
|---|---|---|---|---|---|---|---|
| R-001 | Every async view render takes `alive` and returns before drawing when it is false: forbid `^export async function render\w*\((?!.*\balive\b)` in `webapp/static/views/*.js` | forbid | E-003, E-015 | 2026-11-09 | | | |
| R-002 | State the analyst sets on a tab (selection, filter, sort, period, typed dates, pending confirmation, sub-view) lives in a per-watchlist module map, never in render's locals or a captured query; refresh redraws from it | standards | E-004, E-014 | 2026-11-09 | | | |
| R-003 | Registry calls outside the lock go through one `ctx.unlocked()` helper (forbid `\.lock\.release\(\)` in `webapp/api_*.py`), and every write after one re-reads the rows it writes to | forbid | E-023, E-024 | 2026-11-09 | | | |
| R-004 | A view's catch states the failure in an error element (never `.banner`) and branches on `err.kind` where the server gives one | standards | E-008, E-017, E-020, E-022 | 2026-11-09 | | | |
| R-005 | No value compared with itself in a check: forbid `\(\s*\w+\s*,\s*(\w+)\s*\)\s*==\s*\([^()]*,\s*\1\s*\)` in `walks/**/*.py` and `tests/**/*.py` | forbid | E-026 | 2026-11-09 | | | |
| R-006 | A box that says every, any or each is checked at each instance (every step, every stop, every field), not at a sample; a check's `Lacks:` line names any instance it skips | standards | E-012, E-027, E-028 | 2026-11-09 | | | |
