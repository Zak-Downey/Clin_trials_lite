# 11: Exploration: one round over what the fixes changed

**Blocked by:** 10

**Status:** ready-for-agent

**Touches:** *

**Kind:** exploration

**Spec sections (read these, not this ticket's paraphrase):** Findings › F3 to F11; Further Notes (a page defect found here becomes its own design ticket). Root: `docs/agents/walkthrough.md` section 5.

**What to build:** One exploratory walker per area the fixes touched tries to break them: watchlists and review (F3 to F7: redraws, late answers, the sidebar, the check header and status), and find trials and adding (F8 to F11: destinations, failed adds, sponsor types, refused searches). A defect that needs a change under `webapp/static/` is written up as a new `Kind: design` ticket of this spec with its Open list item; any other defect is fixed here from the walker's red check.

- [x] One findings file per area — doc: .scratch/pr-1-review/explore/watchlists-and-review.md; doc: .scratch/pr-1-review/explore/find-and-add.md
- [x] Every defect found is fixed, or written up as a `Kind: design` ticket with its Open list item, and the check that found it is in the walk suite and green or declared `todo` against its ticket (the walks check) — doc: docs/agents/local/ledger.md#Escapes; the nine defects are tickets 13 to 17 (design, needs-triage); their walks are in walks/ as xfail(strict) todo walks, 18 xfailed at both viewports (walks/test_explore_wr_*.py, walks/test_explore_find_and_add_*.py)
- [x] Each defect has a row in the escape ledger — doc: docs/agents/local/ledger.md

## Comments
