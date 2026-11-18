# Spec: A linter as the first check, proof that the checks can fail, and one more refusal

Status: ready-for-agent

Written on 18 November 2026, after `kit-phase-1` was merged (`1d828fa`) and copied into the starter kit. The owner agreed the scope in conversation and asked for the spec and tickets to be written for him, without the planning commands and without an interview. Where this spec names a default, it is a recommendation he has not confirmed line by line: use it, and say so in the hand-over.

The figures below were measured on this repo at `1d828fa` with Ruff 0.17.5, and nothing here was changed to get them.

## Problem Statement

The owner starts a build, leaves, and decides from one page. Three things about the build loop itself still weaken that page.

1. **Nothing reads the code without running it.** The only static check is one pattern (R-005). An unused import, a variable that is assigned and never read, or a name that does not exist reaches the unit tests or nobody. The code already carries 38 `# noqa` markers, written for a linter that is not installed, so nothing says whether any of them still does anything.
2. **Nobody has proved the checks can fail.** Every check is green, and green is all the owner sees. The starter's app was once broken on purpose in six ways by hand, and a test went red each time. That was never repeated, was never done in this product, and no script does it.
3. **The building agent can merge its own pull request.** Pushing to `main` is refused, but `gh pr merge` is not, and the session is now logged in to GitHub. The owner's yes should be the only thing that merges.

These are faults of the loop's own files, not of the product. The same files will be copied back into the starter kit, so they must hold in any product.

## Solution

1. **A linter as the first check.** Ruff runs before every other check, as a check named `lint`. Its version is pinned and its rules are written out in a file, so a new release of Ruff cannot turn a build red on its own. The code is cleaned until it passes; nothing is silenced to get there.
2. **Proof that the checks can fail.** A list of small deliberate breaks, and a command, `python3 prove.py`, that makes each one in a copy of the repo and confirms that the named test or check goes red. A break that stays green is reported, and the command ends red. The working folder is never touched.
3. **One more refusal.** `.claude/settings.json` refuses `gh pr merge`.

## User Stories

1. As the owner, I want the code read for mistakes before any test runs, so that the cheapest check catches what it can first.
2. As the owner, I want the linter's version and its rules written in the repo, so that the same commit gets the same result next month.
3. As the owner, I want the code to pass the linter because it was fixed, so that green means clean and not silenced.
4. As the owner, I want a `# noqa` marker that silences nothing to be a finding, so that the markers cannot pile up unread.
5. As the owner, I want the hand-over page to name the new check in my words, so that I can read a run's history.
6. As the owner, I want every sentence that lists the checks to agree with the code, and a test that keeps it so, so that the next agent reads the truth.
7. As the owner, I want to be told on the pull request when it changes the linter's rules, so that weakening the judge is never quiet.
8. As the owner, I want one command that breaks the code on purpose and shows that a check notices, so that I know green can mean something.
9. As the owner, I want every one of the five checks proved able to fail, so that none of them is decoration.
10. As the owner, I want a break the checks do not notice to be reported and never quietly dropped, so that a missing test is found.
11. As the owner, I want the proof to count only a test that ran and failed, so that a break which merely stops the tests from starting is not called proof.
12. As the owner, I want the proof never to change my working folder, so that I can run it at any time.
13. As the owner, I want a stale break (its text is no longer in the file) caught by the ordinary checks, so that the list does not rot between runs.
14. As the owner, I want the agent unable to merge a pull request, so that merging stays mine.
15. As the owner of the starter kit, I want none of the new kit files to name anything of this product, so that they can be copied into any other product.

## Implementation Decisions

- **Kit files stay product-neutral.** `checks.py`, `handover.py`, `prove.py`, `ruff.toml`, the workflow and their tests read the same in any product. What is particular to this repo goes in `docs/agents/local/`: `repo.md`, and the list of breaks.
- **The linter.** Ruff, pinned as `ruff==0.17.5` in `requirements-dev.txt`. The build session installs it into `.venv` itself.
- **Its rules are written out.** `ruff.toml` at the repo root selects exactly `E4`, `E7`, `E9`, `F` and `RUF100`, and nothing is left to Ruff's defaults. The reason: since Ruff 0.16.0 (July 2026) the defaults are 413 rules, and 0.17.0 changed them again. Under today's defaults this repo has 210 findings; under the list above it has 25 (15 unused imports, 4 unused variables, 3 `# noqa` markers that silence nothing, 1 f-string with no placeholder, 1 lambda assigned to a name, 1 import not at the top). The rule set starts small and is widened at a retro, one rule group at a time.
- **What it reads.** Every Python file git tracks except those under `.scratch/`, which holds records, not code. `.venv` is never read. The file states the Python version of this repo's `.venv` (3.13).
- **Cleaning up.** Each of the 25 findings is fixed in the code. No rule leaves the list, no file or folder is exempted, and no blanket `# noqa` is added. Where a finding cannot be fixed without changing what the code does, a `# noqa` naming that one rule, with the reason on the same line, is allowed, and the ticket's comments count them. A fix never changes behaviour: the unit tests and the walks pass before and after.
- **The check.** Named `lint`, first in `CHECKS`, with a limit of 1 minute. Its output goes to `.checks/lint.txt` like any other. It leaves no cache folder or other file behind: `git status` is the same after a run as before. `checks.py` still decides red or green by exit code and timeout alone.
- **R-005 stays.** Tested on 18 November: Ruff 0.17.5 with every rule switched on reports `b == b` and does not report `(a, b) == (3, b)`, which is the shape R-005 exists for.
- **The lists of checks.** `handover.py` gives `lint` its words for the owner. `repo.md` and the docstring of `checks.py` say five checks. A test holds the "Every check" line of `repo.md` to the names in `CHECKS`, in order, so the two cannot drift again.
- **GitHub.** The workflow already installs `requirements-dev.txt` and runs `python3 checks.py` with no check named, so the linter runs there with no change to those steps. `ruff.toml` joins the files whose change the pull-request notice reports, because it judges the code. No second workflow, no `pull_request_target`.
- **The breaks are data.** `docs/agents/local/breaks.json`: a list of entries, each with an `id`, the `file` to change, the text to `find` (it must occur exactly once in that file), the text to `replace` it with, a `why` in one sentence, and what proves it: either `test` (one pytest test, by its id) or `check` (the name of a check in `CHECKS`).
- **`prove.py`.** A kit file at the repo root. It copies the files git tracks, as they are on disk, into a temporary folder and works only there, reaching this repo's `.venv` from the copy. For each break it runs the named test or check unbroken, which must be green; makes the change; runs it again, which must be red. For a test, red means pytest ran the test and it failed (pytest's exit code 1): a break that stops the tests from being collected or run is not proof. For a check, red means `python3 checks.py <name>` ends 1. It prints one line per break and a last line with the count, and ends 1 when any break stayed green, was red before the change, or could not be made (the text is missing or appears more than once), or when the list is empty. Each run has a time limit and never outlives the command. One line per run is appended to `.checks/proof.jsonl`.
- **When the proof runs.** By hand: `python3 prove.py`. It is not a sixth check and the build loop does not run it. After this build, the starter's `new_product.py --check` will run it on the example app.
- **Keeping the list current.** A unit test, which therefore runs in every `python3 checks.py`, holds that each entry is well formed, its `find` text occurs exactly once in its file, its test or check exists, and ids are not repeated. It makes no break and runs nothing.
- **This product's list.** At least one break for each of the five checks, and at least three proved by a walk, because 11 of the 15 problems found late in the last two builds were page behaviour. A break proved by a unit test or a walk changes the app's code, never a test. Each is a mistake a build could plausibly make: a refusal removed, a wrong status, a field dropped, a page not redrawn.
- **A break the checks miss is a finding.** If a plausible break stays green, it is not deleted from the list to make the proof pass. Write the missing test (seen red first) if it is small; otherwise leave the break out of the list and name it first in `now_what`.
- **The refusal.** One line, `Bash(gh pr merge*)`, added to the deny list in `.claude/settings.json`. Nothing else in that file changes. It stops that spelling of the command and no other; the spec does not claim more.
- **Editing under `.claude/`.** Claude Code can stop for a permission prompt on an edit there. If the session is not allowed to make the edit in the last ticket, the change is written out in full in `.scratch/kit-phase-2/settings-edit.md` for the owner to apply, and the ticket is complete in that form.
- **Glossary.** No new domain term.

## Testing Decisions

- **What makes a good test here:** it states what the owner or an agent would observe: a run's result and its log line, what a command prints and how it ends, what a file says. It never states how.
- **Seams:** the unit suite only. No page of the app changes, so no walk is added or changed and no area in `repo.md` is touched. By the build's own rules that means no exploratory tester, and one reviewer for `server-and-checks`.
- **The linter** is not tested by re-testing Ruff. The tests hold what this repo decides: `lint` is first and has 1 minute; the version is pinned to one exact version; `ruff.toml` selects exactly the agreed rules and exempts nothing; a file with an unused import, in a copy, turns the check red; and the repo as committed is green.
- **`prove.py`** is tested on a small hand-made repo in a temporary folder (a module, a test, a list), as `tests/test_checks.py` already does with stand-in commands. The cases: a break its test catches; a break its test misses; text that is missing; text that appears twice; a test that is red before the break; a break that stops collection; a break proved by a check; an empty list; and that the folder it was run in is unchanged.
- **This product's proof** is run once for real in ticket 07, and its output is kept in the ticket's comments. The cheap test of the list runs in the unit suite from then on.
- **Every new test is seen red first.**

## Out of Scope

- A pre-push hook, a deny line for `--no-verify`, and blocks on editing `checks.py`, the settings file or the workflow. The owner decided against these on 18 November: the check on GitHub already reports a red pull request and a change to a judging file.
- Any command guard that runs before a tool call.
- Widening the linter beyond the five rule groups above, and a code formatter.
- Running the proof on GitHub or inside the build loop, and showing it on the hand-over page.
- Line ceilings on the instruction files, and a budget for new tests.
- Choosing which tests to run from what a change touched.
- One committed line per build.
- Protecting `main` on GitHub: the owner's step.
- Copying the changed files back into the starter kit: a separate step after this build is merged.
- The larger factory's gate, guard, picker, ticket parser and dashboard. If a ticket seems to need one, it is left not done and named first in `now_what`.

## Further Notes

**Size.** `prove.py` should be about 150 lines. If the build passes about 400 lines of new code outside tests, `now_what` says so and why. One new dependency: Ruff, for development only.

**Defaults used unless the owner says otherwise.** Ruff 0.17.5. The rule list `E4`, `E7`, `E9`, `F`, `RUF100`. The check is named `lint`. The files are named `ruff.toml`, `prove.py` and `docs/agents/local/breaks.json`. A time limit of two minutes for each run inside the proof. The proof is by hand only.

**What `now_what` carries, in this order,** beyond what the page computes for itself:

1. Any plausible break the checks did not catch, and what was done about it.
2. The findings fixed, counted by rule, and every `# noqa` added or removed, with the reason for each one added.
3. The measured minutes: a full `python3 checks.py` before and after the linter joined, the linter alone, and one run of `python3 prove.py`.
4. Whether the settings file was edited or the edit was left in `settings-edit.md`.
5. Each default above that was used, and anything in this spec found to be wrong.
