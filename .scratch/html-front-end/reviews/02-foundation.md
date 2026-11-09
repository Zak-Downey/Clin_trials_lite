# Branch review: the walk tooling (ticket 02)

Diff: `git diff 8250054..ffe5356`. Read first: `reviews/02.md`. Its blocking finding (the fidelity comparison had no test) is fixed at this tip, and its four notes are decisions. None is repeated here.

How I checked: I copied the repo, without `.git`, `.venv` or `.scratch`, to `/tmp/rv02/repo` and ran experiments there with the main checkout's `.venv/bin/python`. Nothing in the worktree was changed. "Reproduced" means I ran it there. "Inferred" means I read it.

## Blocking

1. **The walk runner reports green when a walk errors in setup and another walk flakes. An erroring walk never reaches `## Result`.**
   - Where: `walks/run_walks.py:56` (`... else code if not failed else 0`), `:44` (only `^FAILED` lines are collected) and `:32` (`-rf`).
   - What happens: `-rf` drops the `ERROR` lines from pytest's short summary. A setup error is how a walk fails when its app or registry does not start (`helper.App` raises `RuntimeError("the app did not start")`), so that kind of walk is never re-run and never listed. If any `FAILED` walk is also in the run and passes when run alone, `main` returns 0, whatever the setup errors. If a run has only errors, the exit is 1 but `## Result` is empty, and `evidence.md` says the ready gate reads the verdict "from the `## Result` section and nothing else". The `red_marker` `FAILED|ERROR` cannot pair `ERROR` with a title either, because `-rf` keeps that line out of the output.
   - Who meets it: the orchestrator and the user, through `gate.py checks`, `merge` and `ready`. The walk would be broken while the gate says green.
   - How I know: reproduced. `walks/test_zzrun.py` in the copy has one test whose fixture raises and one that fails once, then passes. `WALK_FEATURE=rv walks/run_walks.py -k zzrun` gave `1 failed, 1 error`, `## Result` listed only the flake as "red under load, green alone", and the exit was 0 (`/tmp/rv02/e6.txt`).
   - Class: blocking.

2. **The `requestfailed` guard has never been seen red. Removing it leaves every guard walk green.**
   - Where: `walks/helper.py:130`. The page that should show it is `walks/broken/broken_pages.py:28`.
   - What happens: the only broken page that makes a request fail at the network level sends it to `127.0.0.1:9`. The foreign-request guard (`helper.py:139`) catches that request first, and `test_walk_guard_fails_a_walk_on_a_failed_request_or_one_to_somewhere_else` asserts only the 404 message and the "not the app's own server" message. So a request to the app's own server that gets no response (connection reset, server died mid-request, blocked or aborted) has no check that it fails a walk.
   - How I know: reproduced. In the copy, with line 130 replaced by `pass`, `pytest walks/test_walk_guards.py` gave `4 passed` (`/tmp/rv02/e3.txt`).
   - For comparison, the same experiment on the `pageerror` guard (line 129) was caught: `1 failed, 3 passed` (`/tmp/rv02/e2.txt`). The console, 404, foreign and sideways guards each have their message asserted, so removing any of them would turn a guard walk red. That is inferred; I did not mutate those four.
   - Class: blocking. This is a guard never seen red, and a surviving mutant on a walk-tooling ticket.

## Design

3. **Any response of 400 or more, and any console error, fails a walk, and a walk cannot declare one it expects.** This gets expensive once the error-path tickets build on it.
   - Where: `walks/helper.py:143` (`response.status >= 400`) and `:135-136`. Chromium also logs "Failed to load resource: ... 404" as a console error, so the one fault trips two guards.
   - What happens: the API answers ordinary user errors with 4xx: `watchlist_not_found` 404 (`webapp/api_watchlists.py:15`), `trial_not_found` 404 (`webapp/api_trials.py:16`), and the planned invalid-ID, not-found, already-listed and registry-unavailable kinds (spec story 71, and "Distinct error kinds" under Implementation Decisions). A walk that proves the app handles one of these correctly will be red whatever the page shows. Each later ticket will then either weaken a guard locally, add its own allow-list, or change the API to answer 200 with an error body. Those are three conventions for one problem, and changing it later means touching every error walk.
   - How I know: reproduced. Opening `#/watchlists/999/needs-review` on the seeded app failed the walk with `failed request: .../api/watchlists/999/needs-review (status 404)` and the console 404 (`/tmp/rv02/e1.txt`). A stale bookmark is a path a user can reach.
   - What to decide: one way for a walk to say which response it expects, for example `walk.expect(status=404, path=...)`, kept in the helper so the guards stay one copy. The decision is whether the guard means "unexpected failure" or "any failure".
   - Class: design.

## Sweep

4. **The sideways-scroll guard measures only the document's width, and only once, after the walk has finished.**
   - Where: `walks/helper.py:146-153`, called once from `walks/conftest.py:91`.
   - What happens: a page that is wider than the window in the middle of a walk (a dialog, an expanded change list) and narrower again by the end passes, and its mid-walk screenshot shows the overflow. A region that scrolls sideways inside an `overflow-x: auto` container also never widens the document. Spec story 99 asks for "no horizontal scrolling of titles, changes or summaries" on every screen.
   - How I know: reproduced for the mid-walk case. I widened the page, took `walk.shot`, then removed the wide element, and the walk passed (`test_zz_sideways_mid_walk`, `/tmp/rv02/e1.txt`). The container case also passed (`test_zz_inner_overflow`), but I did not confirm that the container really scrolled, so treat that half as inferred.
   - A fix would check at each `walk.shot` as well as at the end.
   - Class: sweep.

5. **A walk that opens a second page loses the guards of the first.**
   - Where: `walks/conftest.py:76` (`request.node.walk = walk`).
   - What happens: each call to `make_walk` overwrites `request.node.walk`, and the report hook reads only the last one. A console error on the first page goes unreported. Screenshot numbering restarts for the second page, under the same name, so its shots overwrite the first page's. Walks with two windows, such as two tabs on one watchlist or a check running while another view is open, are what concurrency tickets write.
   - How I know: reproduced. `test_zz_two_pages_first_errors` logged `console.error` on the first page and passed (`/tmp/rv02/e1.txt`).
   - Class: sweep.

6. **The walks start the app through `walks/serve.py`, not `run.py`, and the stand-ins table has no row for that.**
   - Where: `docs/agents/local/repo.md:36`. That row covers the in-process `make_server` in the unit suite's `api` fixture.
   - What happens: `serve.py` skips `instance.claim`, `--port`, the start-up error messages and the "Trial Change Monitor is running at" line, and it replaces `ctgov.BASE` after import. Its docstring says "nothing else differs from run.py's server". `tests/test_run.py` checks `run.py` itself, but nothing ties the walks' start path to it.
   - How I know: inferred, by reading both files.
   - Class: sweep. Add a row, or widen the existing one.

7. **The fidelity check compares only the single-study response. The search response the stand-in serves is never compared with the live registry.**
   - Where: `walks/fidelity_check.py:61`. The search shape is in `walks/standin_registry.py`, `do_GET` under `/studies`.
   - What happens: the stand-in's search answers (`studies`, `nextPageToken` as a stringified offset, `totalCount` whenever it is asked for, `pageToken` parsed as an int) are the stand-in's own invention, and they back the `register` switch and every Find trials walk to come. The spec asks only for the lookup comparison, so this is a gap rather than a departure, but the dated row in `repo.md` reads as if it covers the whole stand-in.
   - How I know: inferred.
   - Class: sweep. At least say in the row that search is not checked.

## Nit

8. **The foreign-request check matches the origin by string prefix.**
   - Where: `walks/helper.py:139`.
   - What happens: the origin is `http://127.0.0.1:5803` with no trailing slash, so a request to `http://127.0.0.1:58032/...` counts as the app's own.
   - How I know: inferred.
   - Class: nit.

9. **A walk that closes its page drops every problem the guards had already found.**
   - Where: `walks/conftest.py:91` (`[] if walk.page.is_closed() else ...`).
   - What happens: the guards record console errors and failed requests as they happen, but the hook returns an empty list when the page is closed. Only the sideways measurement needs an open page.
   - How I know: inferred.
   - Class: nit.

## Not read

- The thin-slice walks' assertions against the design PDF.
- `gate.py` and the factory tests.
- The unit suite, and the full walk suite at the tip: I did not run either in the worktree, which keeps to the one-browser rule.
- The live fidelity run.
- WebKit.
- Mutations of the console, 404, foreign and sideways guards. I mutated only `pageerror` and `requestfailed`.
- The red files `02-walks-9ec3673.txt` and `02-walks-07ba86d.txt` beyond their names in the ticket. Of `02-walks-8250054.txt` I read only the summary and `## Result`.
