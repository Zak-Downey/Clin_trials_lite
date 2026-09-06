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

Paste an NCT ID (e.g. `NCT03412565`) to start monitoring a trial. The app fetches it,
records a baseline of its current state, and adds it to the watchlist: one line per
trial, carrying what identifies the study alongside what last moved on it and when.
Selecting a line opens that trial's full profile underneath. State lives in a local SQLite file, `monitor.db`, which is
git-ignored. Set `MONITOR_DB` to point somewhere else.

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
