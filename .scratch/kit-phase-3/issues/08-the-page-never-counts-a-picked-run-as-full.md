# 08: The page never counts a picked run as full

**What to build:** The hand-over page treats a picked run as it already treats a quick run: it appears in the history of runs, and it is never the full run the page reports, whatever it happened to run. Where the page says how many runs a build made, it says how many were picked, in the owner's words ("ran only the tests the change could reach"), without the word "picked" left unexplained. A build whose last run is picked has no full run to report, and the page says so as it does today for a quick one. A page built from a log with no `picked` field (an older build) reads exactly as it does now. Spec: `.scratch/kit-phase-3/spec.md`, "Full runs".

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] Red first: with a green full run followed by a green picked run, the page reports the full run as the last full run and counts the picked one apart
- [ ] Red first: with only picked runs after the last change, the page says there is no full run of every check
- [ ] A log with no `picked` field gives the same page as before this ticket
- [ ] `python3 checks.py` ends green on this ticket's commit

## Comments
