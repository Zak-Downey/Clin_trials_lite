# Clin_trials_lite

A thin wrapper over the [ClinicalTrials.gov v2 API](https://clinicaltrials.gov/data-api/api),
plus a prototype tool for monitoring competitors' trials for changes. No API key needed.

## Setup

```bash
pip install -r requirements.txt
```

`ctgov.py` itself is stdlib-only; the requirements are `truststore` (needed on this
machine, see below), `pandas` (only for `to_frame()` / `--csv`), and `streamlit` +
`pytest` for the monitoring app.

## Trial Change Monitor

```bash
streamlit run app.py
```

Two pages. On **Search**, query ClinicalTrials.gov on any of condition, intervention,
sponsor and phase; results come back as a table reading like the watchlist they feed,
and the rows you tick are filed into a list you choose *afterwards* — existing, or named
on the spot — so one search can be split across two lists. Below it, an NCT ID box
(e.g. `NCT03412565`) for the study whose number you already have. Either way the app
fetches each trial and records a baseline of its current state.

A second row of controls narrows what comes back rather than describing it. **Sponsor
type** is the registry's classification of the *lead* sponsor — a different question
from typing a sponsor's name, which finds one company rather than every company like
them. **Status** is where the study has got to, in lifecycle order. **Started on or
after / on or before** is a window on the study start date, either end of which may be
left blank; a study with no start date on record falls outside any window. All three
combine with each other and with the four above: on "chronic lymphocytic leukemia",
industry-sponsored and recruiting and started since 2024 takes 2,614 records down to 44.

None of the three asks a question on its own — a class, a status and a date window say
*which* studies of a kind you want, not which kind — so a search still has to name one
of condition, intervention, sponsor or phase.

One caveat worth knowing, because it is a property of the registry rather than of this
tool. A study is classified by its lead sponsor only. When a company funds a trial that
an academic centre runs, the company is a *collaborator* and the study is classed under
`OTHER` — offered here as *Other (incl. academic)*. So *Industry* is not the whole of
commercial activity: for CLL it returns 725 studies, and a further 326 with an industry
collaborator sit under *Other*. Tick both to see all of it.

On **Watchlist**, pick a list and read it: one line per trial, carrying what identifies
the study alongside what last moved on it and when, and selecting a line opens that
trial's full profile underneath.

Lists are how somebody covering two therapy areas keeps myeloma apart from lung. A trial
can sit in several at once, and taking it out of one leaves the others alone; a trial in
no list at all stops being monitored. A database written before lists existed opens with
everything it already had in one default list.

A list can also carry a **remembered search** — tick *Save this as the list's remembered
search* as you file the results, or press *Save the remembered search only* to point an
existing list at a new query without adding anything. The narrowing axes are saved with
it, and read back under *Manage lists* in words rather than registry codes. Every later
check re-runs that search and offers back whatever matches it that the list does not
already hold, as a **new trial found**: the same feed and the same bell a changed field
gets, reported separately because a competitor *starting* something is different news
from a competitor revising something. Nothing joins the list until you adopt it, and a
trial you dismiss is never offered again. Forget the search under *Manage lists* and the
list behaves exactly as it did before.

State lives in a local SQLite file, `monitor.db`, which is git-ignored. Set `MONITOR_DB`
to point somewhere else.

Run the tests with `python -m pytest`. They drive the app and the monitor through an
injectable fetcher and never touch the network.

## In a browser, with no Python installed

The same app also runs as a static page, with its Python compiled to WebAssembly by
[stlite](https://stlite.net) and executed in the visitor's own browser. There is no
server behind it: the page talks to ClinicalTrials.gov directly, which is possible
because the v2 API answers cross-origin requests.

```bash
python build_site.py            # assemble site/
python -m http.server -d site   # then open http://localhost:8000
```

`web/index.html` names, one at a time, the modules it mounts, and `build_site.py` copies
exactly those. Nothing else travels — not the working database, the tests, the internal
notes under `.scratch/`, or the simulator. A file nobody names is a file nobody ships.

Three things are different in the browser and nothing else is:

- **The transport.** There are no sockets, so `browser.py` asks the browser to make the
  request. It raises the same `urllib` errors the socket transport does, so a missing
  study still reads *"NCT99999999 was not found on ClinicalTrials.gov"* and an
  unreachable registry still reads *"Could not reach ClinicalTrials.gov"* — the two
  sentences an analyst needs to tell apart.
- **The pause between registry calls.** Working through a watchlist leaves half a second
  between trials, and that wait is the app's own — `browser.wait` spins on the clock rather
  than calling `time.sleep`, because whether sleeping waits at all under WebAssembly is a
  property of the runtime and not something to rest a courtesy to a public registry on.
- **Streamlit's version.** The published app runs whichever Streamlit its stlite
  carries, so the stlite version is pinned in `web/index.html` rather than floating:
  1.9.1, carrying Streamlit 1.62 on Python 3.13. A local checkout is not pinned and
  runs whatever its Python allows — Streamlit 1.62 needs Python 3.10, so a checkout on
  3.9 gets 1.50 instead. The app's top page navigation works in both; `sqlite3` is not
  in WebAssembly's standard library and is fetched as a package.

The first load pulls down a Python runtime and its libraries, which takes the better
part of a minute, so the page says it is starting up until the app is on screen.

## Published to GitHub Pages

Pushing to `main` or `master` builds the site and publishes it, through
`.github/workflows/deploy.yml`. There is no manual build step and nothing to remember:
the published app is whatever was last committed. The workflow runs `build_site.py` and
uploads only what it wrote, so the same list that governs a local build governs the
public one. It needs no secret, token or account — the only credential involved is the
one GitHub mints for the run itself.

Two things cannot be done from the code, and somebody has to do them once, in the
repository's **Settings → Pages**:

1. **Turn Pages on and set its source to *GitHub Actions***, not to a branch. Until that
   is done the workflow runs green and publishes nothing, which is the failure worth
   knowing about because it does not look like one.
2. **Check which branch you actually push to.** This repository records `main` as its
   default branch and is developed on `master`, and the workflow watches both, because a
   workflow watching only the wrong one of those publishes nothing and says nothing.
   `master` is the branch the site is published from today. If both branches ever carry
   work, the live site is whichever was pushed last — so if they diverge, narrow the
   `branches:` list to the one you mean. If you push to a third name, add it, or nothing
   will ever publish.

The site is then live at `https://<owner>.github.io/<repo>/`, and the Actions tab shows
the run and the URL it deployed to. **Run workflow** on the *Publish the site* workflow
publishes on demand, without inventing a commit to trigger one.

It is worth repeating the local checks against the real URL once it is up — search the
registry, add a trial, refresh the page and confirm the watchlist is still there —
because the deployed thing is what people use.

## From the command line

```bash
python explore.py "lung cancer"
python explore.py "lung cancer" --limit 100 --status RECRUITING
python explore.py "lung cancer" --csv trials.csv
python explore.py --nct NCT02305173     # full JSON for one study
```

## From Python

```python
import ctgov

ctgov.count(cond="lung cancer")                 # 14501
studies = ctgov.search(cond="lung cancer", limit=50)
df = ctgov.to_frame(studies)                    # flattened DataFrame

ctgov.get("NCT02305173")                        # one full study record
ctgov.flatten(studies[0])                       # nested -> dotted keys
```

`search()` takes `cond` (condition), `term` (free text), `intr` (intervention), and
passes any other keyword through as an API param with underscores turned into dots:

```python
ctgov.search(cond="lung cancer", filter_overallStatus="RECRUITING", limit=200)
```

It pages automatically until it has `limit` studies.

By default it requests the `DEFAULT_FIELDS` slice rather than whole records. Pass
`fields=None` for the complete study document (much larger).

## Notes

- **TLS**: this machine sits behind a proxy that re-signs certificates. Its CA is in
  the Windows certificate store, which Python ignores by default, so `ctgov.py` uses
  `truststore` to verify against the OS store. Certificates are still verified.
- `to_frame()` flattens lists of objects positionally, so columns like
  `interventions[2].name` are ragged across studies. Fine for browsing; reshape if
  you need to analyse interventions properly.
