# 12: Get a finding out of the tool

**What to build:** A medical affairs analyst's output is a briefing, not a dashboard. Today the last mile out of this tool is retyping: an analyst who spots that a competitor's Phase 3 completion date has slipped six months has to copy the trial number, look the values back up, and write the line by hand into an email or a slide. The tool holds every part of that line already.

Give the current list a change summary over a chosen date range — this week, this month, or a pair of dates. It reports one entry per trial that moved in that window, high-signal fields first, each naming the field, the value it moved from and the value it moved to, when the registry was revised, when the tool detected it, and a link back to the registry record. Reviewed and unreviewed alike: a briefing covers what happened, not what is still unread.

The summary is offered two ways from the same data. Copyable text, so it can go straight into an email or a slide without reformatting. And a CSV download, so it can go into a tracker or a spreadsheet somebody else maintains.

Anything simulated is marked as such in both, and stays marked — a briefing is exactly the place where fabricated data must not be able to pass as real.

**Blocked by:** 10 (the summary reports the registry date and the detection date separately, which 10 establishes)

**Status:** ready-for-agent

- [ ] A date range can be chosen, with sensible presets, and the summary covers only changes detected within it
- [ ] The summary covers the current list, and says which list it is for
- [ ] Each entry names the trial, the fields that moved, and both values for each
- [ ] Each entry carries the registry-updated date, the detected date, and a link to the registry record
- [ ] Fields are ordered high-signal first within each trial
- [ ] Reviewed and unreviewed changes both appear
- [ ] The same content is available as copyable text and as a CSV download
- [ ] Simulated changes are marked in both forms
- [ ] A range containing no changes says so rather than producing an empty file
- [ ] Tests cover: range filtering at both boundaries, field ordering, the synthetic marking surviving into both forms, and an empty range
