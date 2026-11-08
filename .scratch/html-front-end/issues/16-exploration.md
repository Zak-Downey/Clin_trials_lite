# 16: Exploration: one round of trying to break it

**Blocked by:** 15

**Status:** ready-for-agent

**Touches:** *

**Kind:** exploration

**Spec sections (read these, not this ticket's paraphrase):** End State 5; Further Notes (areas).

**What to build:** One exploratory walker per area, once: watchlists and review; trial page; find trials; saved search and new matches; summary and export; dialogs and administration. Then one implementer fixes, starting from each walker's red check, only the findings that break an acceptance box of this spec, an In or Partly-in row of the Design coverage table, or a walk guard. Every other finding is added to the spec's Further Notes for the follow-up spec and is not fixed. No second round.

- [ ] One findings file per area — doc: .scratch/html-front-end/explore/<area>.md
- [ ] Every defect found is fixed, and the check that found it is in the walk suite and green — check: walks
- [ ] Each defect has a row in the escape ledger — doc: docs/agents/local/ledger.md
- [ ] Every finding that is not a defect against this spec is listed under the spec's Further Notes as follow-up, not fixed

## Comments
