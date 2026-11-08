# 3. The app runs locally, with its data in a database file

**Status:** accepted (2026-11-08). Supersedes ADR 0002.

The Streamlit front end is replaced by a plain HTML page, and the app now runs as a small Python server on the analyst's own machine, bound to `localhost` and opened in their browser, with the watchlists in a SQLite file on disk. The GitHub Pages site, its stlite/WebAssembly runtime, the site build and the publish workflow are retired.

ADR 0002's constraint, no login and no copy of anyone's watchlist on a server we run, still holds and is met more simply: the server is the analyst's own process and nobody else can reach it. What changes is the cost side. The browser-storage consequences 0002 accepted (no backup, two tabs overwriting each other, data lost with site data) go away: the database is an ordinary file that can be copied, and one server process serializes every write. The cost now is that the analyst needs Python and one command to start the app, which 0002 existed to avoid. The user accepted that ("it can run locally") in exchange for an HTML front end free of the in-browser runtime.

What would reopen this: the app being needed by someone who cannot run Python, or by two people at once. The second is ADR 0002's own reopening condition (a shared list needs a login) and is unchanged.
