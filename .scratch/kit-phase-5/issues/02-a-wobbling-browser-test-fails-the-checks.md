# 02: A wobbling browser test fails the checks

**What to build:** A walk that is red beside the others and green when run alone now ends the `walks` check red. The setting exists: `FLAKY_IS_RED` in `walks/run_walks.py` becomes true, and the test that pins it is changed on purpose. The runner's printed lines name each such walk and say that it wobbled: failed beside the others, passed alone. The record of wobbling walks (`flaky.jsonl`) and the hand-over page's list of them are unchanged. `docs/agents/local/repo.md` says, where it describes the walk runner, that a wobble is red, why (a walk that needs a second go is reading something too early, and on a slower machine fails outright: E-039, E-040), and what to do (make the walk wait for what it reads; never a retry or a fixed pause). It also says this is on trial until the next retro. The change names nothing of this product. Spec: `.scratch/kit-phase-5/spec.md`, "A wobble is red".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Red first, with a hand-made first run and re-run as the runner's tests already use: a walk red beside the others and green alone ends the run red and is named with the word for a wobble; a walk red both times is reported as before; a run with neither is green
- [ ] The record of wobbling walks and the page's list of them read as they did before this ticket
- [ ] `repo.md` says a wobble is red, why, what to do, and that it is on trial
- [ ] A full `python3 checks.py`, not quick and not picked, ends green on this ticket's commit

## Comments
