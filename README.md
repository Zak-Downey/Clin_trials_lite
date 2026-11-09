# Clin_trials_lite

A thin wrapper over the [ClinicalTrials.gov v2 API](https://clinicaltrials.gov/data-api/api),
plus a prototype tool for monitoring competitors' trials for changes. No API key needed.

## Setup

You need Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

`ctgov.py` itself uses only the standard library; the requirements are `truststore`
(needed on this machine, see below), `pandas` (only for `to_frame()` / `--csv`) and
`pytest`.

## Browser walks (development only)

The app needs none of this. The walk suite drives the pages in a real browser:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium webkit
python walks/run_walks.py
```

`requirements-dev.txt` holds Playwright and pytest-xdist; the second line installs the
Chromium and WebKit builds the walks use. The unit tests run with `python -m pytest -q`
and need no browser.

## Trial Change Monitor

```bash
python run.py
```

This starts the app on your own computer and opens it in your browser. Leave the
terminal window open while you use it; press Ctrl+C there to stop it. `python run.py
--no-browser` starts it without opening a page, and `--port N` picks the port.

**Find trials** searches ClinicalTrials.gov by condition, intervention, sponsor and
phase, and can narrow by sponsor type, status and start date. The trials you tick are
filed into a watchlist you choose afterwards, or name on the spot. A box for an NCT ID
(for example `NCT03412565`) adds the study whose number you already have. Either way the
app fetches each trial and records a baseline of its current state.

**Watchlists** are the folders you keep: one per therapy area, say. A trial can sit in
several at once, and a trial in none stops being monitored. Each list has tabs: a summary,
the trials that need review, all trials, and new matches. A trial's page shows its full
profile, with a history of every change since monitoring began. A field that moved stays
highlighted until you mark the trial reviewed.

The Summary's **Export CSV** file opens in a spreadsheet with its characters intact. A
cell that would begin with `=`, `+`, `-`, `@`, a tab or a carriage return is written
with a leading `'` so a spreadsheet shows it as text rather than running it; the page
and the copied text show the value as it is.

A list can carry a **remembered search**. Each check re-runs it and offers back trials
that match but are not yet on the list, as new matches. Nothing joins the list until you
add it, and one you dismiss is not offered again. From a list's menu you can rename it,
delete it, or run a full recheck.

## Where your data lives

Everything you build up is kept in one file, `monitor.db`, in the folder you ran
`python run.py` from. Set the `MONITOR_DB` environment variable to use another file
(its folder must already exist).

**To back it up, copy that file** while the app is stopped, the same as any other
file. To move to another machine, copy it there. To start afresh, move it aside.

The app runs on this machine only. It listens on `127.0.0.1`, so nobody else on your
network can reach it, and there is no account or login. It runs one copy at a time per
database file; starting it a second time points you at the one already running.

The old version, which was published as a web page on GitHub Pages and kept its data
inside the browser, is retired. Lists made in it are not carried over. The reasoning is
in [ADR 0003](docs/adr/0003-the-app-runs-locally-with-a-database-file.md).

Run the tests with `python -m pytest`. They use a stand-in for the registry and never
touch the network.

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
