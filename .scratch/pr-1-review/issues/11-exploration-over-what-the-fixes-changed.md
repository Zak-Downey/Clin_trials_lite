# 11: Exploration: one round over what the fixes changed

**Blocked by:** 10

**Status:** ready-for-agent

**Touches:** *

**Kind:** exploration

**Spec sections (read these, not this ticket's paraphrase):** Findings › F3 to F11; Further Notes (a page defect found here becomes its own design ticket). Root: `docs/agents/walkthrough.md` section 5.

**What to build:** One exploratory walker per area the fixes touched tries to break them: watchlists and review (F3 to F7: redraws, late answers, the sidebar, the check header and status), and find trials and adding (F8 to F11: destinations, failed adds, sponsor types, refused searches). A defect that needs a change under `webapp/static/` is written up as a new `Kind: design` ticket of this spec with its Open list item; any other defect is fixed here from the walker's red check.

- [x] One findings file per area — doc: .scratch/pr-1-review/explore/watchlists-and-review.md; doc: .scratch/pr-1-review/explore/find-and-add.md
- [x] Every defect found is fixed, or written up as a `Kind: design` ticket with its Open list item, and the check that found it is in the walk suite and declared todo against its ticket — doc: .scratch/pr-1-review/explore/watchlists-and-review.md#Disposition (ticket 11); doc: .scratch/pr-1-review/explore/find-and-add.md#Disposition (ticket 11); doc: .scratch/pr-1-review/issues/13-a-late-check-or-review-answer-never-changes-what-the-analyst-moved-on-to.md; doc: .scratch/pr-1-review/issues/14-keyboard-focus-stays-on-check-for-updates-and-on-new-matches-controls.md; doc: .scratch/pr-1-review/issues/15-a-double-click-on-mark-reviewed-sends-one-request.md; doc: .scratch/pr-1-review/issues/16-find-bar-and-add-by-id-state-a-failed-add-as-an-error-and-clear-it-on-edit.md; doc: .scratch/pr-1-review/issues/17-find-trials-states-a-page-number-out-of-range-by-its-kind.md
- [x] Each defect has a row in the escape ledger (E-029 to E-037, each named in its ticket's boxes) — doc: .scratch/pr-1-review/issues/13-a-late-check-or-review-answer-never-changes-what-the-analyst-moved-on-to.md; doc: .scratch/pr-1-review/issues/14-keyboard-focus-stays-on-check-for-updates-and-on-new-matches-controls.md; doc: .scratch/pr-1-review/issues/15-a-double-click-on-mark-reviewed-sends-one-request.md; doc: .scratch/pr-1-review/issues/16-find-bar-and-add-by-id-state-a-failed-add-as-an-error-and-clear-it-on-edit.md; doc: .scratch/pr-1-review/issues/17-find-trials-states-a-page-number-out-of-range-by-its-kind.md

## Comments
