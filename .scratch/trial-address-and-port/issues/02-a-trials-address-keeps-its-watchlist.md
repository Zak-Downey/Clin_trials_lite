# 02: A trial's address keeps the watchlist and tab it was opened from

**What to build:** A trial opened from a watchlist has the address `#/trials/<NCT>[/<tab>]?list=<id>&from=<watchlist tab>`, with `from` left out for Needs review. The links on Needs review cards, in the All trials table and on Summary's trial headings build it. The trial page reads `list` and `from` from the address instead of from the page-only memory a reload clears. "‹ Back to <watchlist>" returns to the `from` tab, and Next trial walks that watchlist's Needs review queue, so both are the same after a reload, in a new tab and from a saved link. The trial page's own Changes, Details and History tabs and Next trial carry `list` and `from` forward. An address with no `list` behaves exactly as today. Remove from this list on the trial page leaves Back and Next as they are. The browser's Back still restores the watchlist's scroll position. Spec: `.scratch/trial-address-and-port/spec.md`, user stories 8–19, 22 and 24–26, Implementation Decisions › The trial address, The address replaces the page-only memory, Carrying it forward, Remove from this list.

**Blocked by:** None (can start immediately). The order is 01 first; nothing here needs the fixed port.

**Status:** done

- [x] Walk, red first: a trial held in two watchlists, opened from the one that is not its first and then reloaded, still reads "Back to <that watchlist>", and Next trial goes to the next trial in that watchlist's Needs review queue
- [x] Walk: a new page opened at a trial address with `list` and `from=all-trials` reads "Back to <that watchlist>", and the link opens that watchlist's All trials tab
- [x] Walk: links from Needs review, All trials and Summary open trial addresses carrying `list`, and `from` except from Needs review
- [x] Walk: the trial's Details and History tabs and Next trial keep `list` and `from` in the address
- [x] Walk: a trial address with no `list` behaves as today
- [x] The browser's Back from a trial still restores the watchlist's scroll position (existing walk stays green)
- [x] Existing walks asserting a trial link's address are changed only where this ticket changed that address

## Comments
