# 03: Every list of the checks names five

**What to build:** Everything that lists the checks agrees with `CHECKS`. `handover.py` gives `lint` its words for the owner beside the other four, in plain words that do not need the word "linter" explained elsewhere. `docs/agents/local/repo.md` says five checks on its "Every check" and "Quick run" lines, says what `lint` is, where its rules live (`ruff.toml`), that the version is pinned and why, and that a rule group is added at a retro and never to make a build pass. A test holds the "Every check" line of `repo.md` to the names in `CHECKS`, in the same order, so the two cannot drift. The tests that quote the list of checks on the hand-over page are updated to the five. Spec: `.scratch/kit-phase-2/spec.md`, "The lists of checks".

**Blocked by:** 02

**Status:** done

- [x] Red first: a test fails until the "Every check" line of `repo.md` names exactly the checks in `CHECKS`, in order
- [x] Red first: a page built from a run that lists `lint` names it in the owner's words, never as a bare check name
- [x] No sentence outside `.claude/` and `.scratch/` still says there are four checks
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

- **Done.** `docs/agents/local/repo.md` now says five checks on its "Every check" and "Quick run" lines, says what `lint` does, and has a new "The linter" line: Ruff pinned to `ruff==0.17.5` in `requirements-dev.txt` so a new release cannot turn a build red on its own, the rules written out in `ruff.toml`, a rule group added at a retro and never to make a build pass, and no cache. The whole-run bound on the "Every check" line went from 13 to 14 minutes, because `lint` adds a 1-minute limit.
- **The words for `lint` changed.** Ticket 02 gave it "the read of the code for common mistakes"; "read" as a noun is unusual, so it is now "the check of the code for common mistakes", which needs no word explained. The hand-over tests that quote it were updated to match.
- **Red first, the repo.md line.** `tests/test_checks.py::test_the_every_check_line_of_repo_md_names_the_checks_in_CHECKS_in_order` failed against the old line (it listed `patterns` first and four names), then passed after the edit. It also holds the number word ("five") to the length of `CHECKS`.
- **Red first, the page.** `tests/test_handover.py::test_a_page_from_a_run_that_lists_lint_names_it_in_the_owner_s_words_never_bare` failed first on the old wording. Then, with the new wording in place, I removed the `lint` entry from `CHECK_GLOSS` by hand, saw the test fail (the page said `lint` bare), and restored the entry; it passes. The test ignores `.checks/lint.txt`, the output file's name.
- **The full run was green** (3.8 minutes: lint, patterns, escapes, unit, walks), run on the working tree just before this commit with only this ticket file left to change.
- **No sentence says four checks.** A search outside `.claude/` and `.scratch/` for "four checks", "4 checks" and lists of the check names found none left. The `checks.py` docstring already listed all five after ticket 02. The remaining "four" hits are about search axes, workers and display cards.
