# 06: The hand-over page shows flaky walks

**What to build:** The hand-over page reads what ticket 05 records. When a walk was flaky in one of the build's runs, the page counts it among the things for the owner to look at and names each one under a fold, in the owner's words: a browser test that failed when run with the others and passed when run alone. With none, the page says nothing new and looks as it does today. Where the record is missing, the page says it is missing and never shows a zero. `docs/agents/local/repo.md`'s sentence about load-only flakes says where they now show. The page's new wording follows `.claude/rules/human-facing-writing.md`. Spec: `.scratch/kit-phase-1/spec.md`, user stories 11 to 14.

**Blocked by:** 05

**Status:** done

- [x] Red first: a page test with a hand-made record shows a flaky walk counted among the things to look at
- [x] Each flaky walk is named under a fold, without a name from the code in the headline
- [x] With no flaky walk recorded, the page's text is the same as before this ticket
- [x] With no record at all, the page says the record is missing
- [x] `repo.md` says where a flaky walk now shows

## Comments
