# 07: Drop pandas from the browser bundle

**What to build:** A faster first visit. Before the app can draw anything, the browser downloads a Python runtime and every library the app asks for, and the largest single thing in that list is a data analysis library used in exactly one place: assembling the watchlist table. The rows handed to it are already a plain list of records, and the table can be drawn from those directly.

Nothing about the table should change — the same columns, in the same order, reading the same way. This is purely the cost of getting there, paid by every visitor on their first load and on any load after their cache clears.

Worth doing if the first load feels slow enough to make people think the page is broken; worth skipping if it does not, which is why it sits last and blocks nothing.

**Blocked by:** 02

**Status:** wontfix

- [ ] The watchlist table renders identically — same columns, same order, same content
- [ ] The library is no longer requested by the browser build
- [ ] First load is measurably faster
- [ ] Anything still needing the library for local or command-line use keeps working
- [ ] The full test suite passes

## Comments

Closed unbuilt, on 2026-09-20, by the test the ticket itself named: "worth doing if the
first load feels slow enough to make people think the page is broken; worth skipping if
it does not". The published site was loaded cold in a browser during ticket 09's checks,
and the first load was not slow enough to be worth paying for. Skipped.

This is not a judgement that the saving was imaginary. pandas is the largest single thing
the browser fetches and it is used in one place, assembling the watchlist table from rows
that are already a plain list of records, so the work was real and the ticket was right
about it. It is a judgement that the cost being removed was not being felt.

What would reopen it: a first load slow enough that visitors think the page is broken --
most likely on a worse connection than the one it was judged on, which was a single
machine on one network and is the weakest part of this decision. The page says it is
starting up precisely because that load is long, so "long" was never the question, only
"long enough to look broken".

Nothing was built, so nothing has to be undone to change our minds. The ticket stands as
written and the analysis in it survives; only the priority was decided.
