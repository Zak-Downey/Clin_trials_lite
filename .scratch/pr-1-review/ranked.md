# Ranked findings: whole-branch review of PR #1 (html-front-end, tip e77cb9c)

Every finding of the six files in `findings/`, once. Two reviewers reporting one root cause are one row citing both. Source abbreviations: **srv** `server-and-domain.md`, **cli** `client-shell-and-watchlists.md`, **disc** `discovery-and-export.md`, **seams** `seams.md`, **walk** `walks-and-retirement.md`, **std** `standards.md`. F-numbers are the fix spec's findings (`spec.md`); E-numbers are ledger rows; Open numbers are the spec's Open list.

Counts: blocking 17 · design 10 · sweep 7 · nit 28. Reviewer classes were changed where the rule here differs: a finding whose fix could change what a user sees is not sweep, and a check that does not check what its box claims is blocking.

## Blocking

| # | Finding | Sources | Ticket | Why blocking |
|---|---|---|---|---|
| 1 | Trial details preset Add to the first watchlist, not the one the analyst came from; trials land in the wrong list (F8) | disc S1 | 05 | Data wrong on a common path: the analyst sees one destination and the trial goes to another. Reviewer said sweep; it changes what a user sees and spans two views. |
| 2 | A saved search with two lead sponsor types is narrowed to one on Edit search (F10) | seams 3 | 06 | Data lost: Replace saved search stores the narrower query. Reviewer said sweep. |
| 3 | The Summary's "Latest:" line can name an older check's fields (F2) | srv 1 | 08 | Wrong data on the line the analyst briefs from; reproduced. |
| 4 | The walk runner's "alone" re-run runs the whole suite (F1) | walk B1 | 01 | A gate does not check what it claims: the defect/flake verdict the ready gate reads is wrong. |
| 5 | A finished check rebuilds the tab: Summary's period and custom dates, New matches' ticks, pending dismiss and View dismissed are dropped (F3) | cli 1; seams 1 | 02 | A user meets it at every check on those tabs; story 8. One root cause (refresh rebuilds from captured state). Seams said sweep. Recurs E-004. |
| 6 | The exported CSV has no byte-order mark; Excel garbles the em dash and accents (F14) | disc S4 | 08 | The briefing file shows wrong values the first time it is opened in Excel. Reviewer said sweep; inferred from known Excel behaviour. |
| 7 | A trial added while its watchlist is deleted gets an orphan membership row and a 200 "added" (F12) | disc S2; srv 8 | 07 | Data wrong: a monitored trial no list holds. Both reviewers said sweep; it spans storage and handler and is reproduced. |
| 8 | A check still checks a trial removed, or a watchlist deleted, mid-run (F13) | srv 7 | 07 | Data wrong: changes recorded for an unmonitored trial, against the spec's "skipped by every check". Same class as 7. |
| 9 | Adding from New matches leaves the header at "0 trials monitored · Check for new matches" (F7) | seams 2 | 04 | A user meets it on every fill from a saved search (stories 24, 82); the button's label is wrong. Seams said sweep. |
| 10 | Add by NCT ID: a failed add clears the ID and shows the failure in the success banner (F9) | disc S3 | 05 | A failure presented as a success; story 71. Reviewer said sweep. |
| 11 | A failed read of a check's state: empty error box, and one failed poll leaves the button refused (F6) | cli 3; cli 4 | 04 | Failure not stated and the control stuck; the two compound. Reviewer said sweep for both. |
| 12 | An inverted date window is shown as a registry failure with a useless Retry; the server picks the refusal's kind by message text (F11) | seams 4; srv 4 | 06 | A user meets it on dates typed the wrong way round; one contract broken on both sides. srv 4 alone was sweep but spans three files. |
| 13 | A slow answer for a trial, queue, All trials or Summary draws over the page the analyst moved to (F4) | cli 2 | 03 | Page and address disagree; ticket 16 fixed the class for Find only. A "known" class nothing acted on here. Recurs E-003. |
| 14 | The sidebar loses `aria-current` and its highlight after Rename, New watchlist, Remove, Undo (F5) | cli 5 | 03 | A user meets it on every rename; screen readers lose the current page. One line, but visible, so not sweep. |
| 15 | The acceptance walk measures sideways scroll only at screenshots (F16) | walk S1 | 10 | Its box claims every step; exploration then found widened dialogs it never measured (E-002). |
| 16 | The acceptance walk checks only the controls it aimed at (F17) | walk S2 | 10 | Its box claims every control reached. |
| 17 | The Summary walk compares a value with itself and leans on the clock (F15) | cli 10; walk N3 | 09 | A gate does not check what it claims, in the always-true form `evidence.md` forbids. Both reviewers said nit. |

## Design (the Open list in `spec.md`)

| # | Finding | Sources | Open | Why design |
|---|---|---|---|---|
| 18 | CSV cells beginning `=`, `+`, `-`, `@` | disc D1; srv 6; root Further Notes summary 6 | 6 | Escaping trades the file's literal exactness for Excel safety; the root spec deferred it as a decision. srv 6 said sweep; it is the user's call. Recommended do, in ticket 08's `as_csv`. |
| 19 | The saved-search cap reads the first 100 results, not 100 new | srv 2 | 7 | Two readings of the spec, each with a cost. |
| 20 | Story 103's simulator CLI has no ticket | srv 3 | 8 | Build it or move the story. |
| 21 | The trial address does not carry the origin watchlist | cli 6 | 9 | Changes the address shape every link uses. |
| 22 | Tab and menu ARIA roles lack their keyboard model | cli 8 | 10 | Arrow keys or plain roles; each has a cost. Reviewer said sweep; it spans three views and changes what assistive technology reports. |
| 23 | A new port each start: tab memory and links last one run | seams 5 | 11 | Two stories pull opposite ways. |
| 24 | A removed trial drops out of the period's summary | disc D2 | 12 | No story decides it. |
| 25 | No live fidelity check of search | walk D1 | 13 | A by-hand live check outside the gate. |
| 26 | Guards cannot declare an expected network failure | walk D2 | 14 | Helper change every walk rests on. |
| 27 | Shared helpers duplicated (`el` ×13, watchlist 404 ×5, lock release ×3, monitor's private functions) | std Duplicated Code, Feature Envy | 15 | A refactor across most files that no defect needs; the cost is the user's. |

## Sweep (ticket 12, a box each)

| # | Finding | Sources | Box | Why sweep |
|---|---|---|---|---|
| 28 | `repo.md` stale: Find trials "not built", stub row says no endpoint calls the registry, `fail` switch missing, no row for the patched `time.sleep` | srv 5; walk S4 | S-1 | One doc file, no behaviour. |
| 29 | `ctgov.find_page` has no unit test | srv 5 | S-2 | A new test, no behaviour change. |
| 30 | The stand-in registry ignores search parameters; its row does not say so and no walk asserts filters reach it | walk S3 | S-3 | A row line and one walk; no behaviour change. The live side is Open 13. |
| 31 | `requirements-dev.txt` names only Chromium; the README omits the walk setup | walk S5 | S-4 | Setup notes only. |
| 32 | No walk presses Check for updates while a check runs | walk S6 | S-5 | One walk; `if (!busy)` already holds. |
| 33 | The WebKit acceptance run accepts the copy-failed notice | walk N1 | S-6 | One assertion in one file; passes today for the right reason. Reviewer said nit. |
| 34 | Guard tests match a guard's message anywhere in the output | walk N4 | S-7 | One file, tightening only. Reviewer said nit. |

## Nit (dropped, with why)

| # | Finding | Sources | Why dropped |
|---|---|---|---|
| 35 | The run's `finally` has no inner guard; a failing `finish_run` leaves the watchlist refusing checks | srv 9 | Carried anyway: its fix is in `api_checks._work`, which ticket 07 changes (last box there). |
| 36 | A crash mid-run is not retryable | srv 10 | The state reads "incomplete", never an all-clear; needs a non-registry exception. |
| 37 | Undoing a removal after another list re-added the trial leaves a lone "resumed" | srv 11 | Rare ordering; each event shown is true. |
| 38 | A malformed request body gets a 500, not a 400 | srv 12 | Only the page sends requests. |
| 39 | Deleting every watchlist recreates "My watchlist" at the next start; stale docstring | srv 13 | Empty list, no trial re-homed. |
| 40 | Escape during Create watchlist (and rename, delete) still applies the change | cli 7 | The local POST answers in milliseconds; it took a 1.5 s artificial delay to see. |
| 41 | An empty This week offers a month that can be narrower than the week | cli 9 | Only in the first days of a month; the offer still shows a real period. |
| 42 | `api.js` shows a non-JSON reply's `SyntaxError` verbatim; the held decisions re-checked (header Last checked, tab counts, simulated-label flake, design 11's second panel) | cli 11 | Belongs with the root spec's logged "Failed to fetch" follow-up; every held decision's reason still holds. |
| 43 | Copied summary marks simulated changes "🧪 SYNTHETIC", the page and CSV "Simulated" | disc N1 | Labelled simulated either way; wording only. |
| 44 | Find results and New matches head a trial by its official title; its pages by acronym | disc N2 | Read only; the NCT ID is on both. |
| 45 | Dismiss parses every offered record once per selected ID under the lock | disc N3 | Inferred, not timed; local and bounded by the cap. |
| 46 | The Find bar drops why a trial could not be added; a bulk add has no pause | disc N4 | The count and IDs are shown; the rate limit is inferred. |
| 47 | View details on a monitored trial opens the registry page, without the Changes tab | seams 6 | The page says "In: <list>"; nothing hidden. |
| 48 | A deleted watchlist's address shows only the server's sentence | seams 7 | The sentence is true and the sidebar works. |
| 49 | The focus-ring check would pass a control with a resting shadow | walk N2 | No control has one. |
| 50 | "Enter in any field submits" shown for three fields | walk N5 | One form-level submit serves every field. |
| 51 | Explore walks exist twice; docstrings point at the `.scratch` copy; doubled names | walk N6 | The suite's copy runs; cosmetic. |
| 52 | The stale-response walk's timing; one unidentified flake under load | walk N7 | 30 of 30 alone; the flake verdict needs ticket 01 first. |
| 53 | `api_trials._require` shares a name with the watchlist guards | std | Style; no coding standard exists. |
| 54 | Tagged tuples for `Run.steps`, repeated `int(list_id)` | std | Style. |
| 55 | `find.js`, `trial.js`, `monitor.py` mix rendering, state and orchestration | std | Skimmed, judgement only. |
| 56 | The hand-over ticket is open | std spec (a) | Expected: root ticket 17 is the user's. |
| 57 | Story 87's "how many checks found changes" not confirmed | std spec (a) | Checked: `summary.js` draws "N checks with changes" from `check_count`. |
| 58 | Stray local `views/` and `PROTOTYPE_*.db` | std spec (b) | Untracked and ignored, not in the branch (walk reviewer confirmed). |
| 59 | The summary names today's zone abbreviation for a range across a daylight-saving change | std spec (c) | The stamps are right; only the label, only across the change. |
| 60 | Story 8 tab memory not verified | std spec (c) | Held by ticket 03's "stays on its tab" walk; the check-refresh part is blocking 5. |
| 61 | The CSV collapses whitespace in titles | std spec (c) | Unconfirmed; goes with Open 6 if the CSV's exactness is revisited. |
| 62 | Acceptance walk keyboard-only and viewports not checked | std spec (c) | The walk reviewer ran it: Chromium at both sizes and WebKit at 1440. |

## Decided earlier, not re-classed

- **The nine exploration follow-ups in the root spec's Further Notes** (std spec (a) and (c), disc "Classing of logged items", cli 11). Decided under the root's End State 5; the branch has not changed their reason. The CSV formula item among them was left as "needs a decision" and is Open 6.
- **Per-ticket reviews 01 and 02** (`.scratch/html-front-end/reviews/`): every item left there has a reason that still holds (srv and walk reviewers both checked). The 02 follow-up's note that `expect` ignores the method still has no walk that meets it.
