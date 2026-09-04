# 04: Open a changed trial and see what moved

**What to build:** The feed tells the analyst that a trial changed; this slice tells them what. Expanding a changed trial shows its full monitored profile with the changed fields highlighted, so they can be found without reading line by line, and read in the context of the whole study rather than in isolation.

Each highlighted field shows its previous value alongside its current one. The direction and size of a move is the intelligence — an enrolment going 265 → 180 reads very differently from 265 → 400 — but no elapsed time is calculated. Where a field moved more than once since the analyst last looked, the previous value shown is the immediately preceding one, not the value at last review; chaining back to a field's original value is deferred to a later history feature.

A field that was previously empty and now has a value renders explicitly as empty rather than blank, so a newly-populated reason-for-stopping is unambiguous rather than looking like a rendering fault.

Not every change carries the same weight. A slipped primary completion date and a typo fix in the official title must not look identical. Fields that matter most to competitor monitoring — overall status, reason stopped, primary completion date, completion date, enrolment, arm groups, interventions, and whether results have appeared — are given greater visual prominence than the rest.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Expanding a changed trial shows its full monitored profile, not only the changed fields
- [ ] Changed fields are visually highlighted within that profile
- [ ] Each changed field shows both its previous and its current value
- [ ] No elapsed-time or duration arithmetic is performed on date changes
- [ ] Where a field changed more than once since last review, the previous value shown is the immediately preceding one
- [ ] A previously-empty field renders explicitly as empty rather than blank
- [ ] High-signal fields are visually more prominent than ordinary ones when changed
- [ ] Unchanged fields render plainly, with no highlight
- [ ] A trial with no changes expands to a plain profile with nothing highlighted
- [ ] Synthetic changes remain badged in this view
- [ ] Tests cover: which fields are marked for highlighting, empty-to-populated transitions, repeated changes resolving to the most recent, and high-signal designation
