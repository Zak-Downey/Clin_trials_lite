# Evidence: what green means

Facts for any agent that writes a test, ticks a box, reviews a ticket or reports a result. Every check in this repo runs against a stand-in for something, so "green" means "green against the stand-ins". One build had 204 tests green, two review waves done, and its main form drawn behind the map: the tests ran in Node, the reviews read code, and nobody had opened the page (2026-11-06). The rules below are about knowing what a green does not cover.

## Boxes carry their evidence

- **An acceptance box is ticked only with evidence**, written after the box text and an em dash (or ` -- `), several separated by `; `:

  | Kind | Points to | The gate checks |
  |---|---|---|
  | `test: <title>` | a unit or integration test, by its title or the title's leading words | the title is found in the test folder |
  | `walk: <title>` | a walk check (`walkthrough.md`) | the title is found in the walk folder |
  | `doc: <path>` | a document the box asks for | the file exists, and it is new: see Red below |
  | `check: <name>` | a whole suite, by its name in `docs/agents/local/factory.json` | the name is configured |
  | `red: <file>` | the committed run in which a new `test:` or `walk:` check failed | see Red below |
  | `shot: <path>` | a screenshot, for what a check cannot hold | nothing: screenshots are not tracked |
  | `needs-human: <what to judge>` | the user | nothing |

  `- [x] A failed save keeps the form — walk: 02f failed save; needs-human: judge the Not saved wording on 02f-01-not-saved.png`

- **A ticked box has at least one of the first five. An unticked box has `needs-human`, or it is open.** A box can have both: the part an agent checked and the part a person judges.
- **The box audit is mechanical**: `python3 .claude/factory/gate.py boxes <feature>`. It does not judge whether the evidence is any good. The per-ticket review does that.

## Every check can fail

- **Each new check is shown to fail on the regression it names, and the run is committed** (Red, below): break the code locally, run `gate.py red`, see the check red, restore the code. The first walk written after that build passed against the broken page until it sampled the whole viewport instead of the form's centre, and only this rule exposed it (2026-11-06).
- **No always-true check**: a "before" value taken before the action; no value compared with itself; fixtures whose answers differ, so an ignored input shows. One walk assertion there had been always true as written (`!x === null`) and was noticed only when the code under it was fixed.
- **Every ticket gets a mutation sample**: three changed lines of logic broken one at a time, the ticket's tests run after each. A break no test notices needs a test before the report. The implementer takes its own sample (`implementer.md#the-hand-sample`); a `Kind: foundational` or `walk-tooling` ticket also gets a `ticket-reviewer`, whose sample skips the implementer's lines and whose surviving mutant is a blocking finding. Under test-first work the same agent writes the test and the code, so they share its misunderstanding; the whole-branch review is every other ticket's independent look.

## Red

Seen red used to be reported in prose, and a report cannot be opened. The run is a file.

- **`red: <file>` on every box whose `test:` or `walk:` title is new on the ticket's branch** (absent from the integration branch's test and walk folders). `gate.py ticket` refuses the box without it. A box citing a check that already exists needs none. Several runs are written `red: <a>; red: <b>`; each new title must be shown failing in at least one.
- **The file is made by `python3 .claude/factory/gate.py red <feature> <NN> <check>`**, with the code broken and the new check in place: it runs the named check from `factory.json`, and keeps the output as `<tracker>/<feature>/red/<NN>-<check>-<tip>.txt` with `# tip <hash>` as its first line. Do not paste a run. The repo's runners begin their output the same way (see The runner contract below).
- **What the gate reads in it**: the first line names a commit on the branch; the check's title sits beside the check's failure marker (`red_marker` in `factory.json`); and the tip is before the commit that made the check pass, so a run of passing code, or one made after, is refused.
- **`doc: <path>` must be able to fail.** It is accepted only when the path did not exist at the integration tip, or it carries `#<anchor>` and that anchor (a heading's slug, or a line starting with that text) is absent at the integration tip and present on the branch. A `doc:` naming only a file the ticket changed is refused: the file existing says nothing about the change.
- **Against the integration branch `feature/<feature>`.** Where there is no such branch the gate has nothing to compare with and skips these two rules.

## The runner contract

`gate.py red`, the red audit and the ready gate read what a repo's runners write, so the runners keep to one contract. It is stated by its properties; the commands that run them are the repo's own, in `factory.json` and `local/repo.md`.

- **The first line is `# tip <hash>`**, the commit the run was made at. `gate.py red` replaces the runner's own first line with its own `# tip` line when it copies the output, so the file carries exactly one, and the red audit reads it to place the run before the commit that made the check pass.
- **The check's own output names the walk output file** in one line, `Walk output written to <path> (exit <code>)`, where `<path>` is a single word with no spaces: `checks.walk_results` finds the file through it and reads the `## Result` section there.
- **The output ends with a `## Result` section** holding one line per check that needed a second look: the file, the title, and the verdict (`red alone`, or `red under load, green alone`) with the path of the retained output.
- **A failing check's title sits beside the check's `red_marker`** (the pattern in `factory.json`), so the gate can match a title to a failure. A run where the title and a failure marker are apart proves nothing and is refused.
- **A walk run writes into the folder `WALK_FEATURE` names**, set by the gate to the feature it is merging, so a feature's walk output is found under that feature.
- **A check file says at its top what its data lacks**, in a line that begins `Lacks:` (see Fixtures bound what a check proves, below).
- **A walk for a known, unfixed defect is declared `todo`** and tied to the ledger row naming its title; `gate.py ready` lists each open defect with the `todo` walk that carries it, or says none does.
- **A red walk is re-run alone once.** Red alone is a defect; red under load and green alone is a flake, recorded as such in the ledger. The ready gate reads the verdict from the `## Result` section and nothing else.

## Stand-ins

- **Every stand-in is a row in the stand-ins table** in `local/repo.md`: what it stands in for, what checks that it still behaves like the real thing, and when that last ran. A runtime standing in for the browser, fake timers for real ones, a stub for an outside service, a fixture for real data, a test harness for the real start command, one browser at one size for the user's.
- **The ticket that introduces a stand-in adds its row.** A review that finds one without a row reports it.
- **A stand-in with no fidelity check is a known gap**, not a hidden one: `gate.py handover` lists every such row for the user beside the release checks.
- **Fixtures bound what a check proves.** A test or walk says at its top which data it uses and what that data lacks. A fixture of four tidy records proves nothing about none, hundreds, the longest name, or two markers in the same place: a repo with a user-facing list or map keeps a hostile fixture for those.
- **Something runs the real start path**: the documented start command, from a clean clone, with nothing but the documented prerequisites. A harness that starts the app in-process stands in for the entry point until something does.
- **A stub of an outside service is checked against the service**: one recorded real response kept as a fixture the stub is tested against, and a by-hand contract check that re-records it. The by-hand check is outside the gate and says so at its top.

## Test doubles for platform functions

In the same build the map-view saver threw `Illegal invocation` on every pan and zoom. A debounce helper called `setTimeout` as a method of a plain object; the unit tests injected fake timers, and they ran in Node, whose `setTimeout` does not check its receiver. Two stand-ins hid one defect.

- **An injected platform function gets one check with nothing injected, in the real runtime.** Timers, `fetch`, storage, the clock, the clipboard. Injection moves the defect from the logic to the wiring, and only the default wiring runs in production.
- **Platform functions are bound in one module and passed as bare functions.** Never stored as a property of your own object and called through it: that changes the receiver.
- **A fake clock in a test of timing is a stand-in, and has a row.**

## Reports

- **Every claim in a report was observed or is marked not checked.** A walk or review report ends with "Not checked": what it could not see.
- **A finding names its gate.** When a defect is found after its ticket merged, whoever fixes it adds a row to the escape ledger (`local/ledger.md`): what it was, what found it, and which earlier gate should have.
