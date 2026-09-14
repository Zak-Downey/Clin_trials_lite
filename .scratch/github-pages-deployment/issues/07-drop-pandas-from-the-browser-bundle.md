# 07: Drop pandas from the browser bundle

**What to build:** A faster first visit. Before the app can draw anything, the browser downloads a Python runtime and every library the app asks for, and the largest single thing in that list is a data analysis library used in exactly one place: assembling the watchlist table. The rows handed to it are already a plain list of records, and the table can be drawn from those directly.

Nothing about the table should change — the same columns, in the same order, reading the same way. This is purely the cost of getting there, paid by every visitor on their first load and on any load after their cache clears.

Worth doing if the first load feels slow enough to make people think the page is broken; worth skipping if it does not, which is why it sits last and blocks nothing.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] The watchlist table renders identically — same columns, same order, same content
- [ ] The library is no longer requested by the browser build
- [ ] First load is measurably faster
- [ ] Anything still needing the library for local or command-line use keeps working
- [ ] The full test suite passes
