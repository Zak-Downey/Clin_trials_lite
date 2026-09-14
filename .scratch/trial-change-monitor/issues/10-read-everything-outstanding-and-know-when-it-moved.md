# 10: Read everything outstanding, and know when it moved

**What to build:** The watchlist's "What changed" column reports less than the tool already knows. It shows only the fields that moved in the *most recent* detection, so a primary completion date that slipped on Monday vanishes from the column the moment a title typo is corrected on Wednesday. Nothing is lost — the trial still wears its bell, and opening it still highlights the completion date — but the column is the thing an analyst scans across thirty trials, and it under-reports exactly when there is most to report. Change it to name every field still awaiting review, however many checks those moves are spread across. A trial whose changes have all been read still says what last moved, since "what has changed on this trial" remains a fair question once the news is old.

Two different dates are currently collapsed into one column. "Changed on" is the day somebody pressed Check, which is not the day the sponsor edited the record — a watchlist checked weekly can show a fortnight-old revision as though it landed this morning. The registry publishes its own posting date and the tool already fetches it. Show both: **Registry updated**, meaning when the sponsor revised the record, and **Detected**, meaning when this tool noticed. Both sort by time, and a trial that has never changed leaves both empty rather than erroring.

A check currently short-circuits when the registry's own last-updated date has not moved, which is correct for registry changes and wrong for one case: after the monitored profile's extraction logic changes, every stored profile is stale and there is no way to force a fresh comparison. Offer a forced full comparison alongside "Check all" that ignores the short-circuit and compares every field.

Finally, a check that finds the registry untouched and a check that finds the registry revised but no monitored field moved are reported identically today, as "no changes". They are different facts: the second says a sponsor edited something the tool has chosen not to watch. Report them distinctly, keeping the existing "could not be reached" warning exactly as it is — an outage must still never read as good news.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] "What changed" names every field awaiting review, including fields that moved in earlier checks than the most recent one
- [x] A trial whose changes have all been reviewed still shows what last moved
- [x] Field names stay ordered high-signal first, so a slipped completion date is never the one hidden under the overflow
- [x] The watchlist carries separate "Registry updated" and "Detected" columns
- [x] Both date columns sort by time rather than alphabetically
- [x] A trial that has never changed renders both date columns as empty, not as an error
- [x] A forced full comparison is offered alongside "Check all" and ignores the last-updated short-circuit
- [x] A check finding the registry revised but no monitored field moved is reported differently from one finding the registry untouched
- [x] A trial that fails to fetch is still reported as a failure, and a run containing one still warns
- [x] Tests cover: outstanding fields spanning two detections, the fallback for a fully reviewed trial, a forced comparison bypassing the short-circuit, and the new outcome reaching the end-of-run summary
