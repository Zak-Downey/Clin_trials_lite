# 06: Say where the data lives

**What to build:** An honest account, in the two places people look, of what happens to an analyst's watchlists.

The README gains a deployment section: where the app lives, that it runs entirely in the reader's own browser, and — stated plainly rather than buried — that their watchlists are stored in that browser alone. They are not backed up. They do not follow them to another machine. Clearing site data destroys them. Someone who assumes otherwise will find out by losing months of monitoring, and the difference between a tool that forgets and a tool that lied is whether it said so up front. It should also say how to run the site locally, including the part that catches people out: opening the page as a file does not work, it has to be served.

Alongside it, an architecture decision record, following the one already in the repository, on why the app is deployed as WebAssembly with browser-local storage instead of hosted with accounts. The decision itself is short; what earns the record is the trade-off, because it is the kind a future reader will otherwise assume was an oversight. No login was the requirement, and no login means no sync, no backup and no shared watchlists. Anyone who later wants two analysts to share a list is not fixing a bug, they are revisiting this decision, and the record is what tells them that.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] The README says where the app is published and how to run the site locally, including that it must be served rather than opened as a file
- [ ] The README states plainly that watchlists live only in the visitor's browser, are not backed up, do not sync, and are lost if site data is cleared
- [ ] An ADR records the decision to deploy as WebAssembly with browser-local storage, and follows the existing ADR's shape
- [ ] The ADR states the trade-off accepted: no login, and therefore no sync, no backup, no sharing
