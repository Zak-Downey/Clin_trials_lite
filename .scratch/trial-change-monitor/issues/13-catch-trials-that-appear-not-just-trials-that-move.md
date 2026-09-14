# 13: Catch trials that appear, not just trials that move

**What to build:** The tool watches records it already knows about. It is blind to a competitor registering something new — which for a medical affairs team is at least as urgent as a completion date slipping. Today the only way to find a newly registered Phase 3 in your indication is to remember to re-run the same search by hand and eyeball the results for something unfamiliar. A list named "Myeloma — Janssen" is a therapy area, and the tool treats it as a bag of trial numbers.

Let a list remember the search that filled it. When the analyst checks that list for updates, the tool also re-runs that search and reports any matching trial not already in the list as a **new trial found** — the same feed, the same bell, the same review loop as a changed field, but a distinct kind of event, since "a competitor started something" and "a competitor revised something" are different news.

A found trial waits to be adopted rather than joining the list automatically. A loose query would otherwise quietly balloon a list with studies the analyst never judged relevant, and that judgement is the whole value of a curated watchlist. Adopting a found trial records its baseline and puts it in the list exactly as adding it from search does today. Dismissing one means it is not offered again.

A list's remembered search can be changed or cleared. A list with no remembered search behaves exactly as lists do now.

**Blocked by:** 10 (both change what a check run reports and how the run is summarised)

**Status:** done

- [x] A search that fills a list can be saved to that list, and the list shows what it is watching for
- [x] Checking a list with a remembered search also re-runs that search
- [x] A matching trial not already in the list is reported as a new trial found, distinctly from a changed field
- [x] A found trial appears in the feed with the same unreviewed marking as a change
- [x] A found trial is not added to the list until it is adopted
- [x] Adopting a found trial records its baseline and adds it, exactly as adding from search does
- [x] A dismissed trial is not offered again for that list
- [x] A trial already in the list is not reported as found
- [x] A list's remembered search can be changed or cleared, and a list without one behaves as it does today
- [x] A failed search does not abort the rest of the check run, and is reported honestly rather than as "nothing new"
- [x] Tests cover: a found trial, an already-present trial not being reported, adoption recording a baseline, dismissal persisting, and a failing search mid-run
