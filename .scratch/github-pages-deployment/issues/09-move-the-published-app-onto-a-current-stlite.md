# 09: Move the published app onto a current stlite

**What to build:** A published app running a Streamlit close to the one the repository is
written against, instead of one twelve versions behind it.

Which Streamlit the site runs is decided by a single pinned version in `web/index.html`.
It pins stlite `0.90.12`, which carries Streamlit 1.50. The current stlite is `1.9.1` and
carries 1.62 — near enough the 1.63 the repository was developed against that the gap
between what a developer sees and what a visitor gets mostly closes. Ticket 08 exists
because of that gap: a defect that cannot be reproduced on 1.63 is live on the site.

The pin is deliberate and should stay a pin. What is being asked for here is to move it
once, on purpose, with the app checked afterwards — not to let it float, which would hand
a visitor's refresh the power to change the runtime underneath them.

Two things make the move worth doing beyond closing the version gap:

- **A crash this app is shaped to hit.** stlite 1.9.1 fixed a fault where a page that
  rendered a dataframe before a 5.5 MB WebAssembly module had finished loading died
  outright. The watchlist *is* a dataframe and it is the first thing drawn, so the app
  may be winning that race by luck rather than by design.
- **The migration looks cheap.** The only breaking change across the 1.0.0 boundary was
  renaming the `mountDocumentStyles` option to `disableDocumentStyles`, and this page does
  not use it. Every option the page does pass — `entrypoint`, `requirements`, `files`,
  `idbfsMountpoints`, `env`, `streamlitConfig` — is unchanged.

Cheap to write is not the same as cheap to trust, and the checking is most of this
ticket. The jump crosses roughly seventy stlite releases and moves the bundled Python
runtime, so what has to be established is not that the version number changed but that
the app still works — and in particular that **watchlists written before the upgrade
still open after it**. They live in the browser's own storage as a SQLite file, and a
visitor who loses months of monitoring to a version bump is owed better than an
apology. That check needs a watchlist created on the old version and read on the new one,
which means doing it in that order and not reinstalling the browser in between.

The spec for this feature records "the app must live within Streamlit 1.50" as an
established fact. That stops being true here, and the spec should say so rather than
leaving a future reader to wonder which of the two is current.

One thing this ticket does not settle: the repository's own development environment
cannot run 1.62 on Python 3.9, which is what a mac clone gets by default. Whether to
raise the local Python so tests run against what visitors run is a real question and a
separate one — this ticket only moves the site.

**Blocked by:** None, but do 08 first — its fix should be version-independent, and
landing it after this one removes the only environment where its test can fail.

**Status:** ready-for-agent

- [ ] `web/index.html` pins one current stlite version, in both the stylesheet and the
      module import, and still pins rather than floats
- [ ] A watchlist created on the published site before the upgrade opens, intact, after it
- [ ] The published app loads, searches the registry, and keeps a watchlist across a
      refresh — checked in a browser at the live URL, not in a build directory
- [ ] The watchlist table draws on first load, with nothing broken in the browser console
- [ ] Renaming a list keeps the list on screen
- [ ] The comment in `web/index.html` says which Streamlit the new pin carries, and why
      the pin is a pin
- [ ] The README and the feature spec no longer say the app must live within Streamlit 1.50
