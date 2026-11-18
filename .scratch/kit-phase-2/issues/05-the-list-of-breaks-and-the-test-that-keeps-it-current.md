# 05: The list of breaks, and the test that keeps it current

**What to build:** The format of the list of deliberate breaks, and the cheap test of it. The list is `docs/agents/local/breaks.json`: entries with an `id`, the `file` to change, the text to `find`, the text to `replace` it with, a `why` in one sentence, and either `test` (one pytest test, by its id) or `check` (the name of a check in `CHECKS`), never both. This ticket starts the list with two real entries for this product: one proved by a unit test and one proved by the `lint` check. A function that reads the list lives in `prove.py` (which ticket 06 completes) and says, for any list and repo, what is wrong with it: an entry missing a field or naming both a test and a check; a repeated id; a file that does not exist; `find` text that is absent or occurs more than once; `find` and `replace` the same; a test file or test function that does not exist; a check that is not in `CHECKS`. A unit test runs that function on this repo's list, so a stale entry turns the ordinary checks red. It makes no break and runs no test. Spec: `.scratch/kit-phase-2/spec.md`, "The breaks are data" and "Keeping the list current".

**Blocked by:** 02

**Status:** done

- [x] Red first: each fault named above, in a hand-made list over a small repo in a temporary folder, is reported in words that name the entry and the fault
- [x] Red first: this repo's list is read by a unit test, which fails when an entry's `find` text is edited out of its file
- [x] The function names nothing of this product and takes the list and the repo as arguments
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

- `prove.py` (80 lines so far) holds `list_problems(breaks, root, check_names=None)`: the parsed list and the repo's folder go in, one line `<id>: <fault>` per fault comes out (an entry with no id is named `entry <n>`). The checks default to the names in `checks.CHECKS`. A test is `<file>::<test>` or `<file>::<Class>::<test>`, with any `[parameters]` ignored; its function is looked up by parsing the file, not by running pytest. `replace` may be empty (a break that deletes text). `prove.BREAKS` is the list's path, for ticket 06.
- Tests in `tests/test_prove.py`, each seen red before the code: 12 over a small repo in a temporary folder (every fault the ticket names, plus an entry with no id, an empty `replace`, a test in a class, and the default list of checks), and `test_this_repos_list_of_breaks_is_current`, which was red while `breaks.json` did not exist. By hand: with `if start > end:` edited to `if end < start:` in `webapp/api_summary.py`, that test went red naming `summary-one-day-range-refused`; the file was then restored.
- `docs/agents/local/breaks.json` starts with two entries, both in `webapp/api_summary.py`. `summary-one-day-range-refused` turns `start > end` into `start >= end`, so a one-day custom period is refused; proved by `tests/test_api_summary.py::test_a_custom_range_is_inclusive_and_validated`, which I ran green before the change and red (1 failed, exit 1) after it, then restored the file. `summary-import-left-unused` adds `import json` after `import briefing`; `python3 checks.py lint` was green before and red after, then the file was restored. Each `find` occurs once in its file (the new test holds that).
- `python3 checks.py lint`, `unit`, `patterns` and `escapes` ended green; a full `python3 checks.py` on the uncommitted change ended green in 3.7 minutes (lint, patterns, escapes, unit 1.2, walks 2.6).
