# 04: A pull request that changes the linter's rules says so

**What to build:** `ruff.toml` judges the code, so it joins the files whose change the pull-request notice reports, beside `.github/workflows/`, `checks.py`, `.claude/settings.json` and `pytest.ini`. That is one more path on the notice step of `.github/workflows/checks.yml`, the same path in the comment at the top of that file, in the tests that hold the list (`tests/test_workflow.py`, `tests/test_judge_notice.py`), and in the "Workflows" line of `repo.md`. Nothing else in the workflow changes: it already installs `requirements-dev.txt` and runs `python3 checks.py` with no check named, so the linter runs on GitHub as it stands. No second workflow, no `pull_request_target`. Spec: `.scratch/kit-phase-2/spec.md`, "GitHub".

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Red first: the test that holds the list of judging files fails until `ruff.toml` is among them, in the workflow and in the notice's own tests
- [ ] The notice names `ruff.toml` when a pull request changes it, and still never fails the run
- [ ] The trigger, the job name, the steps that install and run the checks, and the time limit are unchanged
- [ ] `repo.md` names the same judging files as the workflow, and `python3 checks.py` ends green

## Comments
