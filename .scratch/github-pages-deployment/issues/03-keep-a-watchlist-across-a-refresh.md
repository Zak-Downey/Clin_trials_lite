# 03: Keep a watchlist across a refresh

**What to build:** A watchlist that is still there tomorrow. In the browser the app's filesystem is ordinarily wiped the moment the page reloads, which would make the tool worse than useless for its actual purpose: monitoring is a thing you come back to, and a monitor that forgets every trial on a stray refresh silently destroys the analyst's work without ever admitting it.

The database is instead kept in the browser's own persistent storage, so it survives a refresh, a closed tab and a restarted machine, with no account and nothing transmitted anywhere. The app's storage layer already reads its database location from the environment and needs no changes at all — this is a matter of pointing it somewhere that persists.

Persistence in a browser is not always immediate: written files may sit in memory until they are flushed to the browser's store. Whether that flush happens on its own or has to be asked for needs establishing rather than assuming, because the failure mode is the worst kind — everything looks right for the whole session and the data is gone on reload. If it must be asked for, the place to do it is where the app already commits, once, rather than scattered through the code.

A first-time visitor should land on the same working, empty default watchlist they get locally, with nothing to set up.

What this does not do, and should not pretend to do, is sync. The data belongs to one browser on one machine. That is the cost of asking nobody to log in.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Trials filed into a list are still there after a hard refresh of the page
- [ ] They are still there after closing the tab and reopening the app
- [ ] A first-time visitor lands on a working, empty default watchlist with no setup
- [ ] Opening the app in a private window shows an empty watchlist, confirming data is scoped to the browser
- [ ] Whether the browser store needs an explicit flush is established, and if so it happens wherever the app commits
- [ ] The app still runs locally under Streamlit against its ordinary database file
