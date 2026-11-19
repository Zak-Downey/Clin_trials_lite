# 06: The standards and the notes carry two rules

**What to build:** Two sentences, each where its reader will meet it. First, `CODING_STANDARDS.md` gains R-007, in the form of the six lines already there: a constraint the code depends on, which no name states, is held by a test that fails when it is broken. It comes from four findings of `kit-phase-4` (`review-whole-01` to `review-whole-04`): each was a reason only a removed comment had recorded, such as why a registry code must stay a bare word and why a forced check that finds nothing stores nothing, and in each the line could be changed with every test still green. The file cites defects by their id in the defect log: use the ids those four have there, and if the log does not hold them, add them by the log's own rules, each naming the test that now holds its reason. Second, `docs/agents/local/repo.md` gains one line where a builder writing a walk will read it (under "Running a walk" or beside the stand-in row for GitHub's machine): GitHub runs the checks on Linux, where text is drawn in another font (DejaVu Sans) and a page draws later under load, so a walk waits for the thing it is about to read and never judges by how much room a font takes; it points at E-038, E-039 and E-040. Spec: `.scratch/kit-phase-5/spec.md`, "R-007" and "GitHub's machine".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `CODING_STANDARDS.md` has R-007 in the form of the lines before it, citing defects that are in the defect log
- [x] Each cited line of the defect log names a test that exists, and the `escapes` check is green
- [x] `repo.md` has the line on GitHub's machine, pointing at the three entries
- [x] `python3 checks.py` ends green on this ticket's commit

## Comments

- The defect log did not hold the four kit-phase-4 findings, so this ticket added them as E-044 (review-whole-01), E-045 (review-whole-02), E-046 (review-whole-03) and E-047 (review-whole-04), each naming the test its fate records as holding its reason; all four tests exist (tests/test_search.py, tests/test_check_trials.py, tests/test_lists.py, tests/test_trial_page_details.py). R-007 cites E-044 to E-047. The repo.md line sits at the end of "Running a walk" and cites E-038, E-039, E-040.
- `python3 checks.py --quick --pick` was green on this change (escapes green; unit 838 of 838; walks 2 of 42 picked). The full run waits for the build's full run.
