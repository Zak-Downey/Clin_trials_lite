# 04: Trial page: read the changes and review them without losing your place

**Blocked by:** 02

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 31–42; Implementation Decisions › Domain changes ("Review by change ID", "Review events persist"), › API (A trial, Review); Design coverage 3/*, 4/1, 4/2, 4/F.

**What to build:** The trial page with its Changes tab: each unreviewed change as labelled Previously / Now values, registry-updated and detected dates, grouped by check. The action bar states the review's scope, including the other watchlists holding the trial, before the analyst acts. Mark reviewed marks exactly the change IDs shown and records a review event; the page stays put with a Reviewed label and Undo. Next trial moves through the queue. Back returns to the list position. The Trial details and History tabs exist as tabs here; their content is ticket 05.

- [ ] Walk: opening a trial from Needs review lands on its Changes tab with Trial details and History one click away, and "Back to <watchlist>" returns to the queue at the same scroll position (design 3/1)
- [ ] Walk: each change shows the field name with labelled Previously and Now values; a long value (an endpoint or eligibility text) stacks Previously first, Now second, and all text wraps (design 3/2)
- [ ] Walk: each check's group shows "Registry updated <date> · Detected <local time>", and a field that moved in two checks shows both transitions (design 3/3)
- [ ] Walk: the action bar reads "Review covers all N changes shown above", names the other watchlists holding the trial, stays visible while scrolling, and never covers the last change (design 3/4, 4/F)
- [ ] Test: marking reviewed takes the change IDs shown and marks exactly those; a change detected after the page loaded stays unreviewed (design 3/F)
- [ ] Test: a review applies to the trial in every watchlist holding it, records its time and change IDs, and undoing it returns exactly those changes to unreviewed and records the undo (design 4/2, 4/F)
- [ ] Walk: after Mark reviewed the page stays on Changes with each change labelled Reviewed, shows "N changes marked reviewed. This trial stays open." with Undo, the queue and sidebar counts drop in place, and the scroll position does not move (design 4/1, 4/2)
- [ ] Walk: Undo restores the changes to unreviewed and the counts; Undo is gone after leaving the trial or taking another action
- [ ] Walk: "Next trial" opens the next trial in Needs review and marks nothing reviewed (design 3/4)
- [ ] Walk: a trial with simulated changes shows the "Simulated changes" label on its Changes tab, on a database seeded by the simulator before the walk

## Comments
