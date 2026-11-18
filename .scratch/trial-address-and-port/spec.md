# Spec: A trial's address keeps its watchlist, and the app keeps its port

Status: ready-for-agent

Follows `.scratch/pr-1-review/spec.md`, Open list items 9 (the trial address does not carry the watchlist the analyst came from; finding client-shell 6) and 11 (the app starts on a new port each run; finding seams 5). Both were deferred there to a later spec; this is that spec.

## Problem Statement

The analyst opens a trial from a watchlist and works through it with "‹ Back to <watchlist>" and Next trial. Both depend on which watchlist the trial was opened from, and the app remembers that only for as long as the page stays loaded. After a reload, in a new tab, or from a saved or shared link, a trial held in two watchlists forgets which one the analyst was working in. "Back to" then names the trial's first watchlist, and Next trial walks that watchlist's Needs review queue instead. The review that found this reproduced it with NCT00000003, which is held in two watchlists: after a reload, Back named the other one.

Separately, `python run.py` starts on a new port every time. A link the analyst saved, and the tab each watchlist remembers (Needs review, All trials, New matches, Summary), belong to that port, so they last one run. After a restart every saved link fails to open and every watchlist opens on its default tab again.

## Solution

1. **A fixed port.** `python run.py` starts at `http://127.0.0.1:8765/` every time unless `--port` names another one. If another program holds 8765, the app stops with the plain message it gives today for a busy port, telling the analyst to choose another with `--port`. It never moves to a different port without saying so. A second start of this app still points at the copy already running. Saved links and remembered tabs now last across restarts.

2. **The trial address names the watchlist.** A trial opened from a watchlist has an address such as `#/trials/NCT03412565/details?list=3&from=all-trials`. `list` is the watchlist and `from` the tab it was opened from; `from` is left out when it is Needs review. The page reads both from the address, so "Back to" and Next trial work the same after a reload, in a new tab and from a saved link. An address that names no watchlist, including every link saved before this change, behaves exactly as today.

## User Stories

1. As an analyst, I want the app to start at the same address every time, so that a link I saved yesterday still opens.
2. As an analyst, I want each watchlist to reopen on the tab I left it on after I restart the app, so that a restart does not undo my layout.
3. As an analyst, I want `--port` to still choose another port, so that I can run the app when 8765 is unavailable.
4. As an analyst, I want a plain message naming the port and `--port` when 8765 is taken by another program, so that I know why the app did not start and what to do.
5. As an analyst, I want the app never to switch to a different port without telling me, so that my saved links never fail without an explanation.
6. As an analyst, I want starting the app a second time to point me at the copy already running, as it does today, so that the fixed port does not turn a second start into an error.
7. As an analyst, I want the README to say which address the app starts at and that links and remembered tabs last across restarts, so that I know I can bookmark it.
8. As an analyst, I want a trial opened from a watchlist to carry that watchlist in its address, so that the page knows where I came from without relying on memory a reload clears.
9. As an analyst, I want "‹ Back to <watchlist>" to name the watchlist I opened the trial from after I reload the page, so that a reload does not send me to a different watchlist.
10. As an analyst, I want Next trial to walk the Needs review queue of the watchlist I opened the trial from after a reload, so that I keep working through the same queue.
11. As an analyst, I want a trial I open in a new tab from a watchlist to know that watchlist, so that I can review several trials side by side without losing my place.
12. As an analyst, I want a trial link I saved or shared to reopen with the same watchlist, so that "Back to" and Next trial are right for whoever opens it.
13. As an analyst, I want "Back to" to return to the tab I opened the trial from (Needs review, All trials or Summary), even after a reload, so that I land where I was reading.
14. As an analyst, I want a trial opened from Needs review to have the shorter address with no `from`, so that the most common link stays short.
15. As an analyst, I want the trial's own Changes, Details and History tabs to keep the watchlist in the address, so that switching tabs on the trial page does not forget where I came from.
16. As an analyst, I want Next trial to keep the watchlist and the tab I came from in the next trial's address, so that working through a queue never loses its place.
17. As an analyst, I want Next trial to keep walking that watchlist's Needs review queue whichever tab I came from, as it does today, so that its behaviour does not change.
18. As an analyst holding a trial in two watchlists, I want the address to decide which one "Back to" names, so that the same trial can be worked from either list without confusion.
19. As an analyst, I want a trial address with no watchlist (an old saved link, or a page reached another way) to behave exactly as today, so that nothing I saved before stops working.
20. As an analyst, I want a trial address naming a watchlist that no longer holds the trial (removed, deleted, or a wrong number) to open the trial quietly with its first watchlist, so that a stale link still opens the trial.
21. As an analyst, I want the address in that case to be rewritten in place to name the watchlist actually shown, with no extra Back step in the browser, so that the address never claims a watchlist the page is not using.
22. As an analyst, I want removing the trial from the watchlist I came from, on the trial page, to leave "Back to" and Next trial pointing at that watchlist, so that I can keep working through its queue (Undo puts the trial back).
23. As an analyst, I want "Open the trial" on the registry details page, after I add a trial there, to open it with the watchlist I just added it to, so that "Back to" names that watchlist.
24. As an analyst, I want the browser's Back button from a trial to restore my scroll position in the watchlist as it does today, so that the new address does not cost me my place.
25. As an analyst, I want the sidebar's "you are here" mark on the trial page to behave as today, so that the new address does not change what the sidebar shows.
26. As a keyboard user, I want every link and button affected here to stay reachable and named as today, so that the change is invisible apart from the address.

## Implementation Decisions

- **Port: one new default.** `run.py`'s `--port` default changes from a free port chosen by the system to 8765. The busy-port message, the second-start redirect through `instance.claim` and the `127.0.0.1`-only listening are unchanged. `make_server`'s own default (a free port) stays, because the API tests and the walks start their servers through it and need free ports to run side by side.
- **Port: no fallback.** A taken 8765 stops with the existing message. Silently moving to a free port would bring back the broken links this fixes.
- **The trial address.** `#/trials/<NCT>[/<tab>]?list=<watchlist id>&from=<watchlist tab>`. The path keeps today's shape, so every existing trial link still routes. `from` is one of the watchlist tab names already used in watchlist addresses (`all-trials`, `summary`, and so on) and is left out for `needs-review`. Query parameters in the hash are already how Summary carries its period and Find trials its query, so this follows existing practice.
- **The address replaces the page-only memory.** Today the app remembers the watchlist and tab the analyst came from in a module variable set by a click listener, and a reload clears it. The trial page now reads `list` and `from` from the address instead. Links into a trial page are built with them where a watchlist is in scope: Needs review cards, the All trials table and the Summary trial headings. The click listener's job of saving the queue's scroll position for the browser's Back button stays.
- **Choosing the watchlist.** The trial page uses `list` when the trial's watchlists include it. Otherwise it falls back to the trial's first watchlist, as today, and rewrites the address in place (`replaceState`) to name that watchlist with `from` dropped. A trial in no watchlist keeps "‹ Back to watchlists".
- **Carrying it forward.** The trial page's own tab links and Next trial build their addresses with the same `list` and `from`. Next trial still walks the chosen watchlist's Needs review queue.
- **Remove from this list.** Unchanged: the page does not recompute "Back to" or Next trial after a removal on the page, and the address keeps naming the watchlist. Only a later reload falls back, by the rule above.
- **Registry details.** "Open the trial", shown after a trial is added from the registry details page, carries `?list=<the watchlist it was added to>`. The registry page's own memory of where it was opened from (Find trials or New matches) is not changed here.
- **Glossary.** No new domain term. "Watchlist", "Needs review" and "Monitored trial" are used in the glossary's sense.

## Testing Decisions

- **What makes a good test here:** it states what the analyst sees after an action (a reload, a new page opened at a saved address, a click), or what `run.py` prints and serves. It never states how the address is parsed.
- **Seams (the repo's settled two):** walks for the pages, and for `run.py` the subprocess tests already in the unit suite. No new seam.
- **Port.** The subprocess tests in `tests/test_run.py` that start `run.py` with no `--port` and rely on the free default each pass a port explicitly, so they still run side by side and alongside a copy of the app the owner has open. A new test shows that a plain start chooses 8765 without that test fighting a copy already running on 8765; for example, it checks the address a start would use, or holds 8765 itself and expects the busy-port message naming 8765. The existing busy-port and second-start tests keep passing.
- **Trial address, walks, written red first:**
  - Opening a trial from a watchlist that is not the trial's first, then reloading, keeps "Back to <that watchlist>", and Next trial goes to the next trial in that watchlist's queue. This reproduces client-shell 6 with a trial held in two watchlists.
  - A fresh page opened directly at a saved trial address with `list` and `from=all-trials` shows "Back to <that watchlist>", and the link returns to its All trials tab.
  - Switching to the trial's Details and History tabs, and pressing Next trial, keep the watchlist in the address.
  - An address naming a watchlist that does not hold the trial opens the trial with its first watchlist, and the address is rewritten to name it.
  - An address with no `list` behaves as today.
  - "Open the trial" after adding from the registry details page opens it with that watchlist.
- **Prior art:** `walks/test_trial_page_walk.py` (Back and Next trial), `walks/test_origin_walk.py` (where the analyst came from, and its Back link), and the subprocess tests in `tests/test_run.py`.
- **Existing walks** that assert a trial link's exact address are changed to the new shape, and only where this spec changed the address they assert.

## Out of Scope

- The registry details page remembering its own "‹ Back to results" (Find trials or New matches) across a reload.
- All trials' filter and sort, and Summary's period, in the trial address.
- Next trial following All trials' order instead of the Needs review queue.
- A note on the trial page saying the trial is no longer in the watchlist the address names.
- Recomputing "Back to" and Next trial after Remove from this list on the trial page.
- Moving to a free port when 8765 is taken.
- Tabs remembered under earlier, random ports. They belonged to a different address and are not carried over.

## Tickets

- `issues/01`: the app starts on port 8765. Blocked by nothing. It is built first, because links that keep their watchlist only last past a restart once the port is fixed.
- `issues/02`: a trial's address keeps the watchlist and tab it was opened from. Blocked by nothing, since it works within one run without the fixed port. It is built after 01.
- `issues/03`: a stale watchlist in the address falls back quietly. Blocked by 02.
- `issues/04`: "Open the trial" from registry details carries its watchlist. Blocked by 02.

## Further Notes

- The owner agreed every decision above on 2026-11-17: one spec with two tickets, port first; the address keeps the watchlist and the tab, not filter or sort; an address with no watchlist behaves as today; 8765 as the default with `--port` to override it; the query-parameter shape; a quiet fallback with the address rewritten; Remove from this list unchanged; registry "Open the trial" carries its watchlist; a taken port stops with the existing message.
- `pr-1-review` Open list item 11 suggested the README could say links last one run until a fixed port arrived. With this spec the README says the opposite.
