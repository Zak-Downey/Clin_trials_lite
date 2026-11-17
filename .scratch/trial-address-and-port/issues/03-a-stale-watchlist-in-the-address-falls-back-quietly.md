# 03: A trial address naming a watchlist that no longer holds the trial falls back quietly

**What to build:** When a trial address names a watchlist that does not hold the trial (the trial was removed, the watchlist was deleted, or the number is wrong), the trial page opens with the trial's first watchlist, as it does today with no watchlist in the address. The address is rewritten in place, with no extra Back step in the browser, to name the watchlist actually shown, with `from` dropped. A trial in no watchlist keeps "‹ Back to watchlists". No note is shown. Spec: `.scratch/trial-address-and-port/spec.md`, user stories 20–21, Implementation Decisions › Choosing the watchlist.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Walk, red first: an address naming a watchlist that does not hold the trial opens the trial with "Back to <its first watchlist>", and the address is rewritten to name that watchlist with no `from`
- [ ] Walk: after that rewrite, the browser's Back leaves the trial page (no extra history step)
- [ ] Walk: an address naming a deleted watchlist behaves the same way
- [ ] A trial in no watchlist still reads "Back to watchlists"

## Comments
