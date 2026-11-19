# Spec: No comments in the code, a check that keeps it so, and three loose ends

Status: ready-for-agent

Written on 19 November 2026, after `kit-phase-3` was merged (`d83fe63`). The owner asked for every comment to be removed and for a rule that keeps them out, "or at least minimal", with this repo as the test ground before the same is done in the starter kit. He asked for the spec and tickets to be written for him, without the planning commands and without an interview. Where this spec names a default, it is a recommendation he has not confirmed line by line: use it, and say so in the hand-over.

The figures below were counted on this repo at `d83fe63`.

## Problem Statement

An agent reads the code before it writes any, and writes what it sees. This repo's code tells it that comments are how things are explained here.

1. **There are about 1,150 comments in the Python.** 479 are in the app and the loop's own files, 631 in the tests and the browser tests, and 35 are linter directives. The scripts and styles of the pages hold about 170 more.
2. **The number goes up with every build.** It rose by about 100 across the last three builds, which changed no page of the app.
3. **A comment is checked by nothing.** It can say what the code no longer does, and no test goes red. A name is used, and a test fails; a comment only sits there.
4. **Nothing stops the next one.** No check, pattern or instruction says a comment is not wanted.
5. **A rule that only GitHub enforces would cost a wait each time.** A build runs the checks on the owner's machine after every ticket, so a build's own comment is caught there. A change made outside a build (a hand edit, a small fix after the hand-over) is pushed with no check run, and the first thing to judge it is the run on GitHub, about five minutes later.

The rule comes from Lauren Tan's talk "All Code Is Slop (Except Mine)", as the owner's trust audit of his larger factory records it (C5, "Almost no comments"): the code carries almost no comments, held by a check that fails when one appears.

## Solution

1. **A count first.** `python3 checks.py --comments` lists every comment and the total, and fails nothing. The build measures before it removes.
2. **Every comment is removed,** from the Python, the scripts and the styles. Nothing else about the code changes: for Python this is proved by comparing each file's syntax tree before and after, and for the scripts and styles by comparing each changed line.
3. **A fact that only a comment held is moved, not lost.** The reviewer reads the removed comments and reports each one that recorded something found nowhere else. Each is put where a check or a reader will meet it.
4. **A check keeps it so.** The `patterns` check is red on any comment, with a message that says what to do instead. Two forms are let through: a linter directive with its reason, and an entry in a short list of kept comments that the owner can read.
5. **It is caught before it leaves the machine.** Every `git push` first runs the three checks that take under a second together (`lint`, `patterns`, `escapes`). A push that would be red for a comment is refused on the spot, with the line that says why, so GitHub never has to say it.
6. **Three loose ends from `kit-phase-3`,** which the owner agreed on 19 November to close here. They are built last, with the rule in force, so they are the first code written under it. The stand-in registry of the browser tests stops at once (about 27 of 152 seconds). The walk-guard tests run their broken pages once in a run, not once in each worker (about 19 seconds). The settings refuse Docker to the building agent: a builder started Docker Desktop and pulled an image during the last build, unasked.

## User Stories

1. As the owner, I want to see how many comments there are and where, so that the removal starts from a measurement.
2. As the owner, I want every comment gone from the app's code, the tests, the browser tests, the scripts and the styles, so that the next agent stops copying the habit.
3. As the owner, I want proof that removing them changed nothing the program does, so that I can accept a change to a hundred files without reading it.
4. As the owner, I want a fact that only a comment recorded to end up in a test, a name or the repo notes, so that nothing known is thrown away.
5. As the owner, I want the checks to go red on a new comment, so that the rule does not depend on an agent remembering it.
6. As the owner, I want the red line to say what to write instead, so that the agent fixes it without me.
7. As the owner, I want the few comments that must stay to be in one list with a reason each, so that "minimal" is a number I can see.
8. As the owner, I want that list to have a ceiling, and a change to it to be named on the pull request, so that it cannot quietly become the new place for comments.
9. As the owner, I want a linter directive to keep its reason on the same line, so that silencing the linter still has to be explained.
10. As the owner, I want the proof that the checks can fail to cover the new rule, so that I know it bites.
11. As the owner, I want a comment stopped on my machine before a push, so that I never wait for a run on GitHub to tell me about one, or have to start one again.
12. As the owner, I want that stop to take about a second and to say exactly which line to fix, so that it costs me nothing when the code is clean.
13. As the owner, I want the browser tests to stop waiting on a stand-in that is shutting down, and to run their broken pages once, so that every full run is about three quarters of a minute shorter.
14. As the owner, I want a build never to start Docker or any other program of mine, so that nothing is left running or downloaded that I did not ask for.
15. As the owner of the starter kit, I want the rule's code to name nothing of this product, so that it can be copied into any other product.

## Implementation Decisions

- **Kit files stay product-neutral.** `checks.py`, its tests and the "Building" section of `CLAUDE.md` read the same in any product. What is particular to this repo goes in `docs/agents/local/`: `repo.md`, the list of kept comments, and the list of breaks.
- **What a comment is.** In a Python file, a comment as Python's own tokenizer finds it, so a `#` inside a string is never one. In a script or a style sheet under `webapp/static/`, the character pairs `//` and `/*` anywhere in the file; in a page there, `<!--`. Today every `//` in the scripts starts a comment, so the plain rule is exact here; a script that later needs those characters inside a string writes the string in parts.
- **What is not touched.** Docstrings. Files that are not code: the workflow, `ruff.toml`, the requirements files, `.gitignore`, `pytest.ini`, and every Markdown and JSON file. Text inside Python strings, such as the page that `handover.py` writes. Anything under `.scratch/`.
- **The two forms let through.** A linter directive that names one rule and gives its reason on the same line, exactly as `tests/test_lint.py` already requires. An entry in `docs/agents/local/comments-kept.json`: the file, the comment's exact text, and why it must stay, in one sentence. A first line that starts `#!` is not a comment.
- **The kept list has a ceiling of 10,** pinned by a test, so raising it is deliberate. It should end this build far below that. An entry whose text is no longer in its file is a fault the ordinary checks report.
- **Removal only.** A comment is deleted, and nothing else on its line or near it changes: no rename, no re-wrapping, no moved code, no new docstring. A line that held only a comment goes; a comment after code is cut and the space before it with it. Do it with a script that uses the tokenizer, not by hand over a thousand lines; the script is not kept.
- **Proof for Python.** For every Python file the build changes in the removal tickets, the syntax tree at the ticket's commit equals the tree at the commit before it (docstrings are part of the tree, so none changed). The ticket's comments hold the command and its result.
- **Proof for scripts and styles.** Every changed line either was a comment-only line and is gone, or equals its old self up to where the comment began. The ticket's comments hold the command and its result. The full `python3 checks.py`, with every browser test at both window sizes, is green before and after.
- **Facts that only a comment held.** Most comments restate the code and are simply deleted. The reviewer of this build reads the removed lines (the diff shows them) and reports, as findings, each one that recorded a fact found nowhere else: not in a test, a name, a docstring, `repo.md` or the defect log. Each finding is fixed by putting the fact where it will be met: a test that would fail without it, a line in `repo.md`, or, last, an entry in the kept list (which restores that comment).
- **The count.** `python3 checks.py --comments` prints one line for each comment that is not let through (`<file>:<line>: <its text>`), then the total, and ends 0. It stays after this build as the way to see them.
- **The rule.** The `patterns` check reports every comment that is not let through, as it reports a forbidden pattern today, and is red on any. Its line says what to do: say it in a name or in a test that fails without it; a comment is checked by nothing. There is still one `patterns` check and five checks in all.
- **Switched on last.** The rule joins the `patterns` check only after the removal tickets, so every ticket's commit is green.
- **The pull-request notice.** `docs/agents/local/comments-kept.json` joins the files whose change the notice reports, as `ruff.toml` did, because it decides what the rule lets through.
- **The proof.** `docs/agents/local/breaks.json` gains a break that adds a comment to the app's code and is proved by the `patterns` check. Any break whose `find` text held a comment is rewritten to the new text, and `python3 prove.py` still catches every break.
- **Before a push.** A git pre-push hook, kept in the repo at `.githooks/pre-push`, runs `python3 checks.py lint patterns escapes` and refuses the push when any is red, printing the red check's own lines. It runs nothing slower: no unit test and no browser test. It judges the working folder as it stands, which is what is being pushed when the folder is clean. Git does not copy hooks with a clone, so the hook is switched on with `git config core.hooksPath .githooks`: the build runs that once in this clone, `repo.md` gives the command, and `python3 checks.py` prints one line when a clone has the folder and has not switched it on (never on GitHub's machine, where nothing is pushed). The settings refuse `git push` with `--no-verify`, so the building agent cannot skip it.
- **Inside a build nothing changes.** The checks after each ticket already run `patterns` whole, quick or picked, so a builder's comment is red within seconds of the ticket and is removed before the next one starts. The hook is for everything else.
- **Editing under `.claude/`.** If the session is not allowed to edit `.claude/settings.json` in the last ticket, the one line is written out in full in `.scratch/kit-phase-4/settings-edit.md` for the owner to apply, and the ticket is complete in that form.
- **The stand-in registry.** `walks/helper.py` starts the stand-in for the outside registry on a thread with the standard half-second wait between looks for a stop request, as the unit suite's server did before `kit-phase-3`. It is started so that stopping takes a few hundredths of a second, and a test holds that. This is this product's own stand-in; the starter has none.
- **The walk-guard tests.** `walks/test_walk_guards.py` runs the deliberately broken pages (`walks/broken/`) once for the whole run of the suite, where today each of the four workers that gets a guard test runs them again (about 25 seconds each). Every guard test still asserts what it asserts now, and still runs in a quick run and in a picked run. How the one run is shared between workers is the builder's choice; the walk runner's way of spreading the other walks does not change.
- **Docker.** `.claude/settings.json` refuses the building agent `docker`, `docker-compose` and opening the Docker app, in the same edit as the refusal of `--no-verify` and with the same fallback. `repo.md` says a build starts no program outside this repo's own, and that a fault which needs Linux to be seen is named in `now_what`: the run on GitHub is where Linux is checked.
- **Instructions.** One line in the "Building" section of `CLAUDE.md`, and one in `repo.md` that names the command, the two forms let through and the kept list. The skill file and the two briefs do not change.
- **Glossary.** No new domain term.

## Testing Decisions

- **What makes a good test here:** it states what the owner or an agent would observe: what a command prints and how it ends, what a file says. It never states how.
- **Seams:** the unit suite only, for the count and the rule. No page of the app changes what it does, so no walk is added or changed.
- **Testers and reviewers.** The scripts of every page change, but in comments only, and that is proved line by line. So no exploratory tester is sent, and one reviewer reads the whole change. Its brief for this build has one more task: the removed comments, as described above.
- **The count and the rule** are tested on small hand-made files in a temporary folder: a comment on its own line, one after code, a `#` inside a string, a linter directive with and without its reason, a `#!` first line, a kept entry, a kept entry whose text is gone, a list over its ceiling, and a script, a style sheet and a page with and without the character pairs.
- **This repo** is held by one test: the count is zero, so a new comment anywhere turns the ordinary checks red.
- **The hook** is tested by a real push, in a temporary folder, to a temporary remote: with a comment in a tracked file the push is refused and the file and line are printed; without one it goes through. A stand-in `checks.py` keeps the test fast.
- **The two speed-ups** are measured, not assumed: one full run of the browser tests before and after each, in the ticket's comments, with the count of times the broken pages ran.
- **Every new test is seen red first.** The removal tickets add no test: their proof is the comparison above.

## Out of Scope

- Docstrings. There are about 1,000 of them, in 2,700 lines, and some are read by tools. Whether they get a ceiling is a decision for after this build.
- Comments in the workflow, `ruff.toml`, the requirements files, `.gitignore` and `pytest.ini`.
- A ceiling on the size of `CLAUDE.md`, `repo.md` and the skill files.
- Renaming anything so that a deleted comment's meaning lives in a name. That is ordinary work for later tickets, done with the rule in force.
- Turning the remaining named lambdas into functions so that their linter directives can go.
- A hook that runs the unit tests or the browser tests before a push, or that needs a whole green run. The owner decided against that on 18 November; this hook runs only what takes about a second.
- Removing comments automatically at commit or push. The rule says what to fix; it does not edit code on its own.
- Tightening the time limits in `CHECKS` and in the workflow. They wait for a timed run on GitHub's machine.
- Running the checks on Linux before a pull request, in a container or otherwise.
- Copying the change into the starter kit: a separate step after this build is merged.
- If a ticket seems to need a comment reader for another language, it is left not done and named first in `now_what`.

## Further Notes

**Size.** About 1,300 lines are deleted or cut, in about 140 files. New code outside tests should be under 120 lines. No new dependency.

**Defaults used unless the owner says otherwise.** Docstrings stay. Files that are not code keep their comments. The kept list is `docs/agents/local/comments-kept.json` with a ceiling of 10. The rule lives in the `patterns` check, not in a sixth check. No exploratory tester. The command is `python3 checks.py --comments`. The hook lives in `.githooks/` and runs `lint`, `patterns` and `escapes`. Docker is refused outright.

**What `now_what` carries, in this order,** beyond what the page computes for itself:

1. The count before and after, for the Python and for the scripts and styles, and the number of files changed.
2. The proof: that every changed Python file's syntax tree is unchanged, and the result of the line comparison for the scripts and styles.
3. Each fact that only a comment held, and where it now lives.
4. Every entry in the kept list, with its reason, or that the list is empty.
5. Anything a removed comment showed to be wrong or out of date in the code itself. These are not fixed here: they are listed.
6. Whether the hook is switched on in this clone, how long it takes, and whether the settings file was edited or the edit was left in `settings-edit.md`.
7. The browser tests' time for one full run before and after the two speed-ups, and how many times the broken pages ran.
8. Each default above that was used, and anything in this spec found to be wrong.
