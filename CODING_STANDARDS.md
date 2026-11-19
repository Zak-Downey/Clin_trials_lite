# Coding standards

Each line came from a defect that got past the checks; the ids in brackets are its lines in `docs/agents/local/escapes.jsonl`. A line a pattern can see is enforced by `python3 checks.py` (`PATTERNS` in `checks.py`); the rest are read for by the reviewers in a build.

- **R-001. A slow render never draws over a newer page.** Every async view render takes `alive` and returns before drawing when it is false. (E-003, E-015) Not yet true of `webapp/static/views/new_matches.js`; once it is, the pattern `^export async function render\w*\((?!.*\balive\b)` over `webapp/static/views/*.js` goes into `checks.py`.
- **R-002. What the analyst set on a tab survives a redraw.** Selection, filter, sort, period, typed dates, a pending confirmation and the sub-view live in a per-watchlist module map, never in render's locals or a captured query; refresh redraws from it. (E-004, E-014)
- **R-003. Registry calls happen outside the lock, through one helper, and every write after one re-reads the rows it writes to.** (E-023, E-024)
- **R-004. A failure is stated as a failure.** A view's catch states it in an error element (never `.banner`) and branches on `err.kind` where the server gives one. (E-008, E-017, E-020, E-022)
- **R-005. No check compares a value with itself.** Enforced by `checks.py` over `walks/` and `tests/`. (E-026)
- **R-006. Every means every.** A check of something the spec says of every, any or each instance looks at each instance (every step, every stop, every field), not at a sample. (E-012, E-027, E-028)
- **R-007. A reason the code depends on is held by a test.** A constraint that no name states (why a value must keep its form, why a step stores nothing, why an order breaks a tie) has a test that fails when the constraint is broken; a comment is not where it lives. (E-044, E-045, E-046, E-047)
