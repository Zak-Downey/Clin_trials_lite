# 03: Every list of the checks names five

**What to build:** Everything that lists the checks agrees with `CHECKS`. `handover.py` gives `lint` its words for the owner beside the other four, in plain words that do not need the word "linter" explained elsewhere. `docs/agents/local/repo.md` says five checks on its "Every check" and "Quick run" lines, says what `lint` is, where its rules live (`ruff.toml`), that the version is pinned and why, and that a rule group is added at a retro and never to make a build pass. A test holds the "Every check" line of `repo.md` to the names in `CHECKS`, in the same order, so the two cannot drift. The tests that quote the list of checks on the hand-over page are updated to the five. Spec: `.scratch/kit-phase-2/spec.md`, "The lists of checks".

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Red first: a test fails until the "Every check" line of `repo.md` names exactly the checks in `CHECKS`, in order
- [ ] Red first: a page built from a run that lists `lint` names it in the owner's words, never as a bare check name
- [ ] No sentence outside `.claude/` and `.scratch/` still says there are four checks
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
