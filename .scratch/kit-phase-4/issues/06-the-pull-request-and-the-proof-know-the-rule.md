# 06: The pull request and the proof know the rule

**What to build:** Two things that keep the rule honest. First, `docs/agents/local/comments-kept.json` decides what the rule lets through, so it joins the files whose change the pull-request notice reports, as `ruff.toml` did: one more path on the notice step of `.github/workflows/checks.yml`, the same path where that file's opening lines list them, in the tests that hold the list (`tests/test_workflow.py`, `tests/test_judge_notice.py`) and in the "Workflows" line of `repo.md`. Nothing else in the workflow changes. Second, `docs/agents/local/breaks.json` gains a break that adds a comment to a line of the app's code and is proved by the `patterns` check. Any break whose `find` or `replace` text held a comment that tickets 02 to 04 removed is rewritten to the text as it now is; the cheap test of the list names them. Then `python3 prove.py` is run once: every break is caught. If the map of the pages needs the new file placed (`tests/test_walk_map.py` says so), place it. Spec: `.scratch/kit-phase-4/spec.md`, "The pull-request notice" and "The proof".

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Red first: the test that holds the list of judging files fails until `docs/agents/local/comments-kept.json` is among them, in the workflow and in the notice's own tests
- [ ] The trigger, the job name, the steps that install and run the checks, and the time limit of the workflow are unchanged
- [ ] `python3 prove.py` ends 0 with the new break caught by `patterns`; its printed lines are in the comments, with each break that had to be rewritten
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
