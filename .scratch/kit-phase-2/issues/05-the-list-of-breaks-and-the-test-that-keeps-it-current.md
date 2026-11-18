# 05: The list of breaks, and the test that keeps it current

**What to build:** The format of the list of deliberate breaks, and the cheap test of it. The list is `docs/agents/local/breaks.json`: entries with an `id`, the `file` to change, the text to `find`, the text to `replace` it with, a `why` in one sentence, and either `test` (one pytest test, by its id) or `check` (the name of a check in `CHECKS`), never both. This ticket starts the list with two real entries for this product: one proved by a unit test and one proved by the `lint` check. A function that reads the list lives in `prove.py` (which ticket 06 completes) and says, for any list and repo, what is wrong with it: an entry missing a field or naming both a test and a check; a repeated id; a file that does not exist; `find` text that is absent or occurs more than once; `find` and `replace` the same; a test file or test function that does not exist; a check that is not in `CHECKS`. A unit test runs that function on this repo's list, so a stale entry turns the ordinary checks red. It makes no break and runs no test. Spec: `.scratch/kit-phase-2/spec.md`, "The breaks are data" and "Keeping the list current".

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Red first: each fault named above, in a hand-made list over a small repo in a temporary folder, is reported in words that name the entry and the fault
- [ ] Red first: this repo's list is read by a unit test, which fails when an entry's `find` text is edited out of its file
- [ ] The function names nothing of this product and takes the list and the repo as arguments
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
