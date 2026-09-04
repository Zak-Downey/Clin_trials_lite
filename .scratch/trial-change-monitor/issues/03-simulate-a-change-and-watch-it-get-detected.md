# 03: Simulate a change and watch it get detected

**What to build:** The first test trial is completed and will almost certainly never be revised again, so the alerting path cannot be demonstrated against real data. This slice adds a clearly-labelled developer control that alters the *stored previous* state of a trial — pushing a completion date out, changing enrolment, altering the drug list — so the live registry remains the source of truth and the next check detects a genuine difference through the ordinary code path.

After simulating, pressing "Check all" compares the current registry record against the altered history, records each field that differs, and the feed shows an entry naming the trial and how many fields changed. The feed names trials, not fields: a sponsor revising fifteen fields in one update produces one entry, not fifteen.

Everything the simulator writes is marked as synthetic in the database and carries a visible badge wherever it appears, so nobody in a demo mistakes fabricated data for real registry data, and all of it can be removed with certainty before the build is expanded. The synthetic marking lives alongside the data, never inside the field values themselves — otherwise a later genuine change would compare against a polluted baseline and cleanup would become string-matching rather than a reliable delete.

Two fields are deliberately never reported as changed: the registry's own last-updated timestamp, which moves by definition whenever anything else does and would be a circular alert, and the results link, which is derived from whether results exist and would duplicate that alert.

Lists of values are compared by membership rather than order, since the registry's ordering carries no meaning — a reordered list is not a change.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] A visibly developer-only control can alter a trial's stored previous state
- [ ] The simulator alters stored history, never the incoming registry response
- [ ] A simulated change is detected by the ordinary check, through the same code used for real changes
- [ ] Each differing field is recorded with its previous value, its new value, and when it was detected
- [ ] The feed shows one entry per changed trial, naming the trial and the number of fields that changed, with a timestamp
- [ ] The feed is ordered most-recent-first
- [ ] Comparison of two identical profiles reports nothing
- [ ] List-valued fields compare by membership, so reordering alone is not reported
- [ ] The registry's last-updated timestamp is never reported as a change
- [ ] The results link is never reported as a change
- [ ] Every record written by the simulator is marked synthetic in the database
- [ ] Synthetic data is visibly badged everywhere it appears in the UI
- [ ] Stored field values contain no synthetic marker text
- [ ] All synthetic data can be deleted in one operation, and doing so leaves real data intact
- [ ] Tests cover the comparison directly: scalar changes, list membership changes, reordering, identical profiles, and both excluded fields
- [ ] Tests cover the synthetic path: flagging, wholesale deletion, and absence of marker text in stored values
