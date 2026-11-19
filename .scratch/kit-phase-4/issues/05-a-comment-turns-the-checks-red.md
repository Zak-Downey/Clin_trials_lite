# 05: A comment turns the checks red

**What to build:** The `patterns` check now reports every comment that is not let through, beside the forbidden patterns it reports today, and is red on any. Its line names the file and line and says what to do: say it in a name, or in a test that fails without it, because a comment is checked by nothing. There is still one `patterns` check and five checks in all. The second form let through arrives here: `docs/agents/local/comments-kept.json`, a list of entries with the `file`, the comment's exact `text` and `why` it must stay, in one sentence. A kept comment is not reported; an entry whose text is no longer in its file is reported, and so is a list longer than its ceiling of 10, which a test pins. The list starts empty in this ticket. `python3 checks.py --comments` keeps working and agrees with the check. One test holds this repo: the count is zero. The "Building" section of `CLAUDE.md` gains one line with the rule, and `docs/agents/local/repo.md` one line naming the command, the two forms let through and the kept list. No file under `.claude/` changes. Spec: `.scratch/kit-phase-4/spec.md`, "The rule", "The kept list has a ceiling of 10" and "Instructions".

**Blocked by:** 03, 04

**Status:** done

- [x] Red first, on a small repo in a temporary folder: a comment in a Python file, and `//` in a script, each turn the `patterns` check red, with a line that names the file and line and says what to do instead
- [x] Red first: a kept entry lets its comment through; an entry whose text is gone, an entry with a field missing, and an eleventh entry are each reported
- [x] Red first: the test that holds this repo to zero fails when a comment is added to any tracked Python file, and passes without it
- [ ] `CLAUDE.md` and `repo.md` each have their one line, and `python3 checks.py` ends green on this ticket's commit

## Comments

- 05 built: `checks.py` gains `comments_not_let_through`, `comment_faults` and the kept list (`KEPT`, `KEPT_CEILING` = 10, `kept_entries`); `--patterns` prints the kept list's faults, then one line per comment (`<file>:<line>: say it in a name, or in a test that fails without it; a comment is checked by nothing (<the comment>)`), and `--comments` lets kept comments through too. `docs/agents/local/comments-kept.json` starts as `[]`; a missing list keeps nothing. Each new test in `tests/test_checks.py` was seen red first; the test holding this repo to zero was also seen red with `# a stray comment` appended to `walk_map.py`, then green with it removed. `CLAUDE.md` ("Building") and `repo.md` have their lines; the "Every check" line of `repo.md` now says `patterns` also reads comments. `python3 checks.py lint patterns escapes unit` was green on the working folder before the commit; the full run is left to the build.
