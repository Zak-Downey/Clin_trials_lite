# 03: Keep a watchlist across a refresh

**What to build:** A watchlist that is still there tomorrow. In the browser the app's filesystem is ordinarily wiped the moment the page reloads, which would make the tool worse than useless for its actual purpose: monitoring is a thing you come back to, and a monitor that forgets every trial on a stray refresh silently destroys the analyst's work without ever admitting it.

The database is instead kept in the browser's own persistent storage, so it survives a refresh, a closed tab and a restarted machine, with no account and nothing transmitted anywhere. The app's storage layer already reads its database location from the environment and needs no changes at all — this is a matter of pointing it somewhere that persists.

Persistence in a browser is not always immediate: written files may sit in memory until they are flushed to the browser's store. Whether that flush happens on its own or has to be asked for needs establishing rather than assuming, because the failure mode is the worst kind — everything looks right for the whole session and the data is gone on reload. If it must be asked for, the place to do it is where the app already commits, once, rather than scattered through the code.

A first-time visitor should land on the same working, empty default watchlist they get locally, with nothing to set up.

What this does not do, and should not pretend to do, is sync. The data belongs to one browser on one machine. That is the cost of asking nobody to log in.

**Blocked by:** 02

**Status:** done

- [x] Trials filed into a list are still there after a hard refresh of the page
- [x] They are still there after closing the tab and reopening the app
- [x] A first-time visitor lands on a working, empty default watchlist with no setup
- [x] Opening the app in a private window shows an empty watchlist, confirming data is scoped to the browser
- [x] Whether the browser store needs an explicit flush is established, and if so it happens wherever the app commits
- [x] The app still runs locally under Streamlit against its ordinary database file

## Comments

Done by pointing the app at a directory the browser keeps: the page mounts `/watchlist`
on IndexedDB and sets `MONITOR_DB` to a file inside it. `storage.py` reads that variable
and always has, so not a line of the app changed -- and with nothing set, locally, it
still opens the ordinary `monitor.db` next to the code.

**The flush question, which the ticket asked to establish rather than assume: nothing has
to ask for it.** stlite reads the directory back out of the browser's store before the app
starts, and writes it back every time a script run finishes -- Streamlit runs the script on
every interaction, so every commit is followed by a write-out on its own. Read out of the
shipped bundle and then watched happening in the browser console ("The script has finished.
Syncing the filesystem."). So there is no explicit sync anywhere in the app, and none is
wanted: a hand-rolled one would be a second, worse copy of something already correct.

Checked by driving the built site in Chrome rather than by reasoning about it, since the
failure mode this ticket exists to prevent is one that looks fine right up until the data
is gone:

- A first visit lands on "My watchlist (0)" -- a working, empty default list, nothing to set up.
- `NCT03412565` filed away, then a hard refresh: still there, with its sponsor, title and phase.
- Browser closed and reopened on the same profile: still there.
- A private window: "My watchlist (0)". The data is scoped to the one browser, as promised.

`tests/test_site.py` holds the database path to sitting *inside* a mounted directory,
which is the mistake that would otherwise be made silently: a path a hair outside it is an
app that works perfectly until the tab closes, and no test above the page would notice.

What those tests cannot do is hold the browser to the page, and it is worth being plain
about it. They read the page's own text and the variable `storage.py` reads; a release of
stlite that renamed either option, or quietly stopped honouring it, would pass all of them
while the app fell back to memory. Only driving the built site catches that, and driving a
browser is not something this suite does -- `tests/conftest.py` opens with "Nothing here
touches the network", and a test that downloads a Python runtime to prove a config line
would be the slowest and least reliable thing in it by a wide margin. So the browser check
is a thing done when this page changes, not a thing the suite does. Ticket 05 puts the
build in a workflow, and that workflow is where a smoke test would belong if one is ever
wanted.

Two edges found while doing this, both worth knowing and neither worth fixing here:

- **One tab at a time.** The write-out is the whole file, so two tabs of the app open at
  once are two copies drifting apart and the one that acts last wins. Recorded in the page
  beside the mount, since that is where the reason lives.
- **The app reads `MONITOR_DB` when `storage.py` is imported**, which works because stlite
  sets the environment before it mounts the files and runs the app -- read out of the
  bundle, in that order. It is load-bearing, and the app would fall back to `monitor.db` on
  a filesystem made of memory if that order ever changed.

What this is not is sync, and the app should not be read as offering it. Saying so in the
README and recording the trade-off as an ADR is ticket 06's.
