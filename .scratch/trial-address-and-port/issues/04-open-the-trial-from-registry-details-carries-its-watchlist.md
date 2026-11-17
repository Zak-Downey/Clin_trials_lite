# 04: "Open the trial" on the registry details page carries the watchlist just added to

**What to build:** After the analyst adds a trial from the registry details page, the "Open the trial" link opens the trial address with `list` naming the watchlist the trial was just added to, so the trial page's "‹ Back to <watchlist>" names that watchlist and Next trial walks its queue, even when the trial is also held in another watchlist. The registry page's own "‹ Back to results" is unchanged. Spec: `.scratch/trial-address-and-port/spec.md`, user story 23, Implementation Decisions › Registry details.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Walk, red first: adding a trial from the registry details page to a watchlist that is not the trial's first, then pressing "Open the trial", reads "Back to <that watchlist>", and the address names it
- [ ] The registry page's "Back to results" goes where it went before this change (existing walks stay green)

## Comments
