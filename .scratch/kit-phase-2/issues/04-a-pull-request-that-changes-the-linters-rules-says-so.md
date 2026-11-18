# 04: A pull request that changes the linter's rules says so

**What to build:** `ruff.toml` judges the code, so it joins the files whose change the pull-request notice reports, beside `.github/workflows/`, `checks.py`, `.claude/settings.json` and `pytest.ini`. That is one more path on the notice step of `.github/workflows/checks.yml`, the same path in the comment at the top of that file, in the tests that hold the list (`tests/test_workflow.py`, `tests/test_judge_notice.py`), and in the "Workflows" line of `repo.md`. Nothing else in the workflow changes: it already installs `requirements-dev.txt` and runs `python3 checks.py` with no check named, so the linter runs on GitHub as it stands. No second workflow, no `pull_request_target`. Spec: `.scratch/kit-phase-2/spec.md`, "GitHub".

**Blocked by:** 01

**Status:** done

- [x] Red first: the test that holds the list of judging files fails until `ruff.toml` is among them, in the workflow and in the notice's own tests
- [x] The notice names `ruff.toml` when a pull request changes it, and still never fails the run
- [x] The trigger, the job name, the steps that install and run the checks, and the time limit are unchanged
- [x] `repo.md` names the same judging files as the workflow, and `python3 checks.py` ends green

## Comments

- The notice step of `.github/workflows/checks.yml` now passes `ruff.toml` among the judging files, and the comment at the top and the "Workflows" line of `repo.md` name it too (repo.md adds "the linter's rules"). Nothing else in the workflow changed: trigger, job name, install and run steps and time limit are as they were.
- `ruff.toml` goes before `checks.py` in the step's arguments. Put after it, the existing test `test_every_check_is_run_with_no_check_named` read `checks.py ruff.toml` as a check named and went red; the order means nothing to the notice, so the order changed and the test did not.
- Tests, each seen red first:
  - `tests/test_workflow.py::test_a_step_names_the_five_files_that_judge_a_pull_request_and_no_other` (was "the four files", and only checked inclusion; now the exact list): red until the step named `ruff.toml`.
  - `tests/test_workflow.py::test_the_comment_at_the_top_names_the_same_judging_files_as_the_notice_step` and `::test_repo_md_names_the_same_judging_files_as_the_notice_step` (new): red once the step named `ruff.toml` and the comment and repo.md did not.
  - `tests/test_judge_notice.py::test_a_pull_request_that_changes_the_linters_rules_is_told_so_by_name` (new; `ruff.toml` added to that file's judging list and stand-in repo): the notice script takes its judging files as arguments and needed no change, so this test passed when written; it was seen red with `ruff.toml` taken out of the list it passes, then restored. It also holds that the notice exits 0.
- Checks run on the working tree before commit: `lint`, `patterns`, `escapes` and `unit` green. `walks` not run here (no page changed).
