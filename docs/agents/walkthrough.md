# Walkthroughs: the running app is checked before the user checks it

Facts for any agent that builds, reviews or hands over a change the user will see in a browser. A **walk** is a script that drives the running app in a real browser the way a user would and checks what it sees. Tests that call functions or the server prove the parts; only a walk proves the page. A build once reached the user with every test green and its main form drawn behind the map, so the first click failed (2026-11-06): nobody had opened the page.

What is particular to this repo (the driver, the helper, the folders, the areas) is in `local/repo.md`. What counts as evidence, and the rule that every check is shown to fail, are in `evidence.md`.

## 1. The gate

- **Walks pass before any human check.** A pull request is not marked ready, and no ticket or checklist goes to the user as `ready-for-human`, until the whole walk suite is green on the branch tip and every acceptance box is either ticked with evidence or marked needs-human. The user should never find what a walk could have found. The ready gate (`gate.py ready`) runs the suite and audits the boxes; `gh pr ready` is refused without it.
- **Each ticket with browser acceptance boxes owns a walk**, named in the ticket. The implementer writes or extends it test-first, runs it after the last change, and the report names that run's output file. A ticket whose walk is red is not done, as a ticket whose tests are red is not.
- **A change to shared client plumbing runs the whole walk suite before reporting**: shared CSS, the dialog or component helpers, client libraries other pages use, the walk helpers themselves. `local/repo.md` lists the files.
- **`gate.py merge` runs the whole walk suite on every merge** into the integration branch, with the unit suite. A ticket's walk broken by another ticket is found there, at the merge that broke it, not by the user.
- **Every spec ends with an acceptance-walk ticket** (`tickets.md`): one end-to-end journey across all the spec's tickets, keyboard only, blocked by every ticket that builds something. Per-ticket walks miss what lies between tickets: in another repo every ticket was green and the acceptance walk still found four defects across tickets and in layout. The acceptance-walk ticket fixes a defect only when the fix is a line or two; otherwise it stops and reports it.
- **The acceptance walk runs at two sizes**: the fixed viewport, and the smallest one the brief allows. The guards in section 3 catch layout faults only at the size they run at.

## 2. Isolation and parallel runs

- **Every walk starts its own server on a free port, with its own temporary copy of the fixture data and its own stand-in for each external service.** Nothing is shared, so any number of walks run at once without reading each other's state. Leave any shared-data or shared-port environment variable unset.
- **A walker stops only the processes it started, by their process id** (`every-agent.md`).
- **Walks use fixtures committed to the repo**, so the suite needs nothing beside the checkout. A walk that needs real data or a real external service is a by-hand walk, outside the gate, and says so at its top: when it breaks, nothing goes red.
- **The full suite runs across parallel workers**; a narrowed run of a few walks need not. Each worker launches one browser and gives each walk a fresh browser context.
- **A walk that fails only under parallel load is re-run alone before it is called a failure.** If it passes alone, it is reported by name and ticketed once, so the flake is not re-diagnosed by every implementer. A real race is fixed with a wait on the right condition, not by a longer timeout.
- **The orchestrating session keeps the number of agents running browsers at once at or below the figure in `local/repo.md`.** Past the machine's cores, every walk times out and every agent re-runs alone.

## 3. Writing a walk

- **Every walk goes through the shared helper**, which installs the guards. A walk that launches its own browser has its own copy of the guards, and the copies drift.
- **Act as a user.** Find elements by role and accessible name, type and press keys, click what a user clicks. Never send a request around the page: a walk's own request diverges from the page's and keeps passing after the page breaks. Never force a click past whatever covers the element: that is the defect.
- **Every journey has a keyboard-only walk**: every control reachable and labelled, focus visible, focus held inside an open dialog and returned to its opener on close, focus kept across redraws.
- **Every walk fails, without being told to, on**: a console error or uncaught page error; a request to anywhere but the app's own server; sideways scrolling of the page; an element the walk clicks that something else covers. The shared walk helpers install these guards.
- **Wait on a condition, never a fixed delay, and a wait the wrong state cannot meet.** A wait for "Saved" must not be met by "Not saved".
- **Every check can fail** (`evidence.md`): no always-true check; a "before" value taken before the action; no value compared with itself; fixtures whose answers differ, so an ignored input shows. Each new check is shown to fail on the regression it names (break the code locally, see it red, restore it).
- **Check what is drawn, not a proxy for it**, and check layout with assertions (the element is on top across its whole box, not only at its centre; nothing overflows), not by reading screenshots. A full-page screenshot taken after scrolling shows layout faults that are not there.
- **Walk the paths the acceptance boxes name, not just the happy path**: failed saves, refusals, empty results, recovery, the last option in a long list. Defects hide in the paths nobody walked.
- **A walk says at its top which data it uses and what that data lacks.** Fixtures bound what a walk proves.
- **Before changing a helper other walks use, find its callers and run them**, and keep its signature.
- **A walk's script, any narrative a human follows for it, and its screenshots change together.** A stale narrative has the user report the new behaviour as a defect.

## 4. Evidence

- **Walk output goes to a file, and the file is read**, never the terminal.
- **An acceptance box is ticked only with evidence** (`evidence.md`): a named walk check, or a screenshot path for what a check cannot hold.
- **Screenshots** are taken at one fixed viewport, named in reading order (`NN-<step>.png`), with personal paths masked, and kept for every failed walk. They live in a git-ignored folder; the results file cites them by path.
- **Simulated data is labelled as simulated** wherever a screenshot or report shows it.
- **Every walk report ends with "Not checked"**: what the walk could not see (judgement of wording and legibility, real hardware, paper, screen readers, real external services, real data). Every claim in a report was observed or is marked not checked.

## 5. Exploring before the review

Per-ticket walks turn acceptance boxes into checks. Nobody was looking for what no box names, and in the first build that ran walkers they found three defects that 204 unit tests and two review waves had missed. So a spec that changes what a user sees has an exploration ticket (`tickets.md`), worked after the acceptance walk and before the whole-branch review:

1. **One exploratory walker per area runs at once** (`exploratory-walker`), each in its own worktree and branch. It has no boxes. It tries to break the app in its area: the paths no box names, hostile data, the keyboard, a second size, things done out of order, twice, or too fast.
2. **A defect is reported as a script that is red because of it**, kept under `<tracker>/<feature>/explore/<area>/`, outside the walk suite. The walker's branch therefore never makes the suite red, and can be committed and merged like any other.
3. **One implementer then works the exploration ticket.** It merges the walkers' branches into its own. For each defect it moves the walker's script into the walk suite, sees it red there, fixes the product until it is green, and adds a row to the escape ledger. A finding it judges not to be a defect stays where it is, with the reason written beside it.
4. **The ticket is reviewed and merged like any other.**

A walker writes scripts and reports defects; it does not fix product code and does not change the shared walk helper.

## 6. Cost

- **Subagents run walks in the foreground** with the Bash tool's `timeout` parameter; only the orchestrating session runs a job in the background (`every-agent.md`).
- **Walks never reach a real paid or external service.** A run against the real one is the user's, by hand.
- **On CI, if the repo has it:** walks are the expensive job, so they skip draft pull requests and run when dispatched. Pushing and workflow rules are in `ci-spend.md`.

## 7. What stays with the user

Only what a walk cannot judge: whether wording reads well, legibility of real map or chart data, first use by someone unfamiliar, real hardware and network, paper, battery, screen readers. These reach the user after everything else is green, with the walk's screenshots beside them: `gate.py handover <feature>` writes the list.
