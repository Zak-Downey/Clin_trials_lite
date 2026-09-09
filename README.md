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

On **Watchlist**, pick a list and read it: one line per trial, carrying what identifies
the study alongside what last moved on it and when, and selecting a line opens that
trial's full profile underneath.

Lists are how somebody covering two therapy areas keeps myeloma apart from lung. A trial
can sit in several at once, and taking it out of one leaves the others alone; a trial in
no list at all stops being monitored. A database written before lists existed opens with
everything it already had in one default list.

A list can also carry a **remembered search** — tick *Save this as the list's remembered
search* as you file the results, or press *Save the remembered search only* to point an
existing list at a new query without adding anything. Every later check re-runs that
search and offers back whatever matches it that the list does not already hold, as a **new
trial found**: the same feed and the same bell a changed field gets, reported separately
because a competitor *starting* something is different news from a competitor revising
something. Nothing joins the list until you adopt it, and a trial you dismiss is never
offered again. Forget the search under *Manage lists* and the list behaves exactly as it
did before.

State lives in a local SQLite file, `monitor.db`, which is git-ignored. Set `MONITOR_DB`
to point somewhere else.

Run the tests with `python -m pytest`. They drive the app and the monitor through an
injectable fetcher and never touch the network.

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
