# 06: Say where the data lives

**What to build:** An honest account, in the two places people look, of what happens to an analyst's watchlists.

The README gains a deployment section: where the app lives, that it runs entirely in the reader's own browser, and — stated plainly rather than buried — that their watchlists are stored in that browser alone. They are not backed up. They do not follow them to another machine. Clearing site data destroys them. Someone who assumes otherwise will find out by losing months of monitoring, and the difference between a tool that forgets and a tool that lied is whether it said so up front. It should also say how to run the site locally, including the part that catches people out: opening the page as a file does not work, it has to be served.

Alongside it, an architecture decision record, following the one already in the repository, on why the app is deployed as WebAssembly with browser-local storage instead of hosted with accounts. The decision itself is short; what earns the record is the trade-off, because it is the kind a future reader will otherwise assume was an oversight. No login was the requirement, and no login means no sync, no backup and no shared watchlists. Anyone who later wants two analysts to share a list is not fixing a bug, they are revisiting this decision, and the record is what tells them that.

**Blocked by:** 05

**Status:** done

- [x] The README says where the app is published and how to run the site locally, including that it must be served rather than opened as a file
- [x] The README states plainly that watchlists live only in the visitor's browser, are not backed up, do not sync, and are lost if site data is cleared
- [x] An ADR records the decision to deploy as WebAssembly with browser-local storage, and follows the existing ADR's shape
- [x] The ADR states the trade-off accepted: no login, and therefore no sync, no backup, no sharing

## Comments

Done. The README gains a *Where your watchlists live* section and `docs/adr/0002`
records the decision behind it. Both are held to their promises by `tests/test_docs.py`,
which is new: this repository already tested the README in `test_deploy.py`, and a
documentation fact is the one kind this suite otherwise cannot catch going stale, since
the app behaves identically whether or not anybody was ever warned.

### Two claims were written wrong first, and both mattered

Neither was caught by reading the prose back -- only by checking it against the code it
describes, which is the habit this ticket is about.

- The README said that opening the page as a file leaves the app "on its starting-up
  message forever". It does not: `web/index.html` gives up after two minutes and removes
  the overlay, so what you actually get is a blank page. The stated cause was off too --
  a `file://` page is refused the stlite module it imports before it ever reaches the
  app's own `.py` files.
- The ADR said the browser build "changed no application code". True of `storage.py`,
  which reads `MONITOR_DB` and needed nothing, but `browser.py` exists precisely because
  the browser needed its own transport and its own pause between registry calls. The
  claim is now scoped to where the data lives, which is all it was ever true of.

### A test that passes is not the same as a test that checks

Two assertions in the first draft of `test_docs.py` could not fail. One accepted
`http.server`, which the README already contained at HEAD, as evidence that it explains
why the page must be served. The other looked for the substring `sync` anywhere in the
ADR, which is satisfied by the unrelated sentence about stlite syncing a directory to
IndexedDB -- so deleting the *No sync* trade-off entirely would have left it green.

Both now assert inside the section that owes the claim, and both were checked by deleting
the sentence they guard and confirming that test, and only that test, fails.

### Scope taken on deliberately

The README's deployment section claimed the repository "is developed on `master`" and
that `master` is what publishes. Ticket 05 renamed `master` -> `main`, and `main` is now
the only branch on the remote, so that was false two paragraphs above the live URL this
ticket required. Corrected here, along with the same stale claim in `deploy.yml`'s header
comment and in a `test_deploy.py` docstring. The workflow still watches both names -- that
is deliberate belt-and-braces and its test is unchanged.

### Checked in a browser

A human ran the live-site checks on 2026-09-20, against
https://zak-downey.github.io/Clin_trials_lite/, and they passed: the app loads, the
watchlist table draws with nothing broken in the console, a registry search returns
results, a watchlist survives a refresh, and renaming a list keeps it on screen.

That matters to this ticket for one criterion only. The README now prints that URL as
the place the app lives, and a URL in a README is a claim about something that works --
so the claim has been checked rather than assumed. The rest of what this ticket wrote
down is about what happens to data that nobody can see happening, which is why it is
written down at all.

Those same checks are three of ticket 09's criteria, and they have since been ticked and
approved there. One run, recorded in two tickets because it answered something in each --
not two runs.

### Not covered

**The file check in the README is still reasoned, not observed.** That opening
`site/index.html` as a file fails -- and that it fails the way now described, with the
starting-up message replaced by a blank page after two minutes when the module load from
a `null` origin is refused -- comes from reading `web/index.html` and from what a browser
permits a `file://` origin. The site was built and served locally so the check could be
run, and the served half worked; the file half was not among what was verified. It is the
most likely sentence in this change to be wrong.

Three tests in `tests/test_app.py` fail on this machine before and after this change:
`AppTest.download_button` does not exist in the Streamlit 1.50 that Python 3.9 pins here.
That is the local environment gap ticket 09 raises, not a regression from this work.
