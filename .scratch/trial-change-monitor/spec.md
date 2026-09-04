# Spec: Trial Change Monitor

Status: ready-for-agent

## Problem Statement

A medical affairs team monitors competitors' clinical trials on ClinicalTrials.gov. Sponsors revise their registry records continuously — completion dates slip, enrolment targets move, arms are added, a trial is quietly terminated — and each of those edits is competitive intelligence with a short shelf life.

Today the only way to notice is for an analyst to open each trial's page and read it against their memory of what it said last time. That does not scale past a handful of trials, it misses changes entirely, and it gives no way to distinguish "this is new since I last looked" from "I already actioned this".

## Solution

A lightweight web app holding a shared watchlist of trials. An analyst pastes an NCT ID to start monitoring it. Pressing "Check all" re-fetches every watched trial, detects which monitored fields have changed since the previous check, and records them.

The main page shows the watchlist and a reverse-chronological feed of trials that have changed. Expanding a trial shows its full monitored profile with changed fields highlighted, each showing its previous and current value. Once an analyst has read the changes, they mark the trial as reviewed and the highlighting clears — so the highlight always means "new since you last looked".

Because the first test case is a completed trial that will never change again, the prototype includes a clearly-labelled developer control that mutates stored history to simulate a change, so the alerting path can be demonstrated end to end.

## User Stories

1. As a medical affairs analyst, I want to paste an NCT ID to start monitoring a trial, so that I can begin tracking a competitor's study without learning a search syntax.
2. As an analyst, I want to see confirmation that a trial was added along with its sponsor and title, so that I can be sure I monitored the trial I intended.
3. As an analyst, I want an obvious error when I paste an invalid NCT ID, so that I don't believe I'm monitoring something that doesn't exist.
4. As an analyst, I want an obvious error when ClinicalTrials.gov is unreachable, so that I don't mistake an outage for "no changes".
5. As an analyst, I want adding a trial to record a baseline without raising 41 change alerts, so that my feed isn't flooded the moment I start monitoring.
6. As an analyst, I want "started monitoring" to appear in the feed when I add a trial, so that I get visible confirmation the tool is working even before anything changes.
7. As an analyst, I want to see every trial I'm monitoring in one list, so that I can review coverage at a glance.
8. As an analyst, I want each watchlist row to show NCT ID, sponsor, title, overall status and when it was last checked, so that I can identify trials without expanding them.
9. As an analyst, I want a single "Check all" button, so that I can refresh the whole watchlist in one action.
10. As an analyst, I want a progress indicator during a check, so that I know the app is working rather than frozen.
11. As an analyst, I want checking to skip the expensive comparison when the registry record hasn't been touched, so that checks stay fast as the watchlist grows.
12. As an analyst, I want to see which trials have changed since I last reviewed them, so that I can prioritise where to spend attention.
13. As an analyst, I want the feed to name trials rather than individual fields, so that a sponsor revising fifteen fields at once produces one feed entry and not fifteen.
14. As an analyst, I want each feed entry to say how many fields changed and when, so that I can judge whether it's worth opening.
15. As an analyst, I want to expand a trial to see its full monitored profile, so that I can read a changed field in the context of the whole study.
16. As an analyst, I want changed fields visually highlighted within that profile, so that I can find what moved without comparing line by line.
17. As an analyst, I want a changed field to show its previous value alongside its current one, so that I can judge the direction and size of the change.
18. As an analyst, I want a field that was previously empty to render clearly as empty rather than blank, so that a newly-populated field like a termination reason is unambiguous.
19. As an analyst, I want changes to fields that matter most — status, key dates, enrolment, arms, drugs — flagged more prominently, so that a slipped completion date doesn't look like a typo fix in the official title.
20. As an analyst, I want to mark a trial as reviewed, so that I can separate new intelligence from what I've already actioned.
21. As an analyst, I want highlighting to clear once I've marked a trial reviewed, so that the next highlight I see is genuinely new.
22. As an analyst monitoring a competitor, I want to know when a trial's overall status changes, so that I learn a study was terminated or completed.
23. As an analyst, I want to know when a reason for stopping appears, so that I capture rare, high-value intelligence about why a competitor's trial failed.
24. As an analyst, I want to know when the primary completion date moves, so that I can anticipate when readout data will appear at congress.
25. As an analyst, I want to know when enrolment changes, so that I can infer whether a competitor is struggling to recruit or expanding a study.
26. As an analyst, I want to know when arms or interventions change, so that I detect a competitor's shift in combination strategy.
27. As an analyst, I want to know when results are first posted, so that I can review them promptly.
28. As an analyst, I want a link to the trial's results page rather than results data in the tool, so that I read outcomes in their full clinical context on the registry.
29. As an analyst, I want that results link to be absent when no results exist, so that I never follow a dead link.
30. As an analyst, I want the tool not to alert me that the registry's own "last updated" timestamp changed, so that I don't get a circular alert on every single update.
31. As a developer demonstrating the prototype, I want to simulate a change on a completed trial, so that I can show the alerting path working without waiting for a real sponsor edit.
32. As a developer, I want simulated changes to flow through the same detection code as real ones, so that the demo proves the real path works.
33. As a developer, I want every piece of synthetic data marked as synthetic in the database, so that I can delete all of it with certainty before expanding the build.
34. As a developer, I want synthetic data visibly badged in the UI, so that nobody in a demo mistakes fabricated data for real registry data.
35. As a developer, I want synthetic marking kept out of the stored field values themselves, so that a later genuine change diffs against a clean baseline.
36. As a developer, I want raw registry records retained, so that if the team asks to monitor a field we currently discard, historic data is still available.
37. As a developer, I want every individual change recorded even when nobody reviewed the intervening state, so that a per-field history view can be added later without backfilling.
38. As a developer, I want to run the app with a single command against a local database, so that I can demo it without provisioning infrastructure.
39. As a developer, I want the checking loop to be polite to a public government API, so that the prototype doesn't risk being blocked.

## Implementation Decisions

### Existing modules, unchanged

- The API client exposes fetching, searching and counting against ClinicalTrials.gov v2. It requires no API key and verifies TLS via the OS certificate store, which this machine needs because a proxy re-signs certificates.
- The medical affairs view maps a raw study record to a flat profile of 41 fields spanning sponsor identity, drugs, disease, design, endpoints, dates, and a results link. This is the set of monitored fields.

Neither module gains any knowledge of monitoring, storage, or the UI.

### New modules

**Storage.** Owns the SQLite schema and all reads and writes. Three tables:

- `trials` — one row per watched trial: NCT ID, when monitoring began, when last checked, when last reviewed.
- `snapshots` — one row per fetch: NCT ID, fetch timestamp, the raw registry record as JSON with the results section removed, and a synthetic flag.
- `changes` — one row per field that moved: NCT ID, field name, previous value, current value, detection timestamp, and a synthetic flag.

Snapshots retain the raw record rather than the derived profile, so fields not currently monitored remain recoverable. The results section is stripped because results are linked rather than tracked, and it is the bulk of the payload.

Every individual change is written to `changes` even when several occur between reviews, so a per-field history view can be built later from data already collected.

**Diff.** A pure function comparing two profiles and returning the fields that differ. Lists compare by membership, not order, since registry ordering carries no meaning. Two fields are excluded from comparison: the registry's own last-updated timestamp, which changes by definition whenever anything else does and would be a circular alert, and the results URL, which is derived from the has-results flag and would duplicate it. A named subset is designated high-signal for prominent display: overall status, reason stopped, primary completion date, completion date, enrolment, arm groups, interventions, and has-results.

**Monitor.** Orchestrates one check: compare the registry's last-updated timestamp against the stored snapshot's; if unchanged, record the check and stop. Otherwise fetch, derive the profile, diff against the previous snapshot's profile, write the new snapshot and any change rows. Adding a trial writes a baseline snapshot and no change rows.

The study-fetching function is injectable, defaulting to the real API call. This is the module's only seam.

**Synthetic data.** Mutates the most recent *stored* snapshot rather than faking an incoming API response, so the live registry stays the source of truth and the next real check produces genuine change rows through the normal path. Rows it writes carry the synthetic flag. The flag is a column, never text embedded in a field value, so cleanup is a delete by predicate rather than string matching, and a later genuine change to that field diffs against an uncorrupted baseline.

**Web app.** A single Streamlit page. Streamlit is chosen because it reaches user-viewable output fastest and imports the existing Python directly; the diff engine and storage are UI-agnostic, so a later move to a conventional web framework replaces only the view layer.

### Interaction decisions

- Trials are added by pasting an NCT ID. Search exists in the API client and can be surfaced later.
- One shared watchlist. No authentication and no per-user state, which is honest for a prototype running locally against a local database.
- Checks run sequentially with a short delay between trials and a progress bar.
- Failures surface inline and leave the watchlist untouched. No retries — a prototype should fail visibly.
- The feed lists trials, not fields. Expanding a trial reveals the profile with changed rows highlighted.
- A changed field shows its previous and current value for the most recent change only. Where a field changed more than once between reviews, the previous value shown is the immediately preceding one, not the value at last review. No elapsed-time arithmetic. Chaining back to a field's original value is deferred to a history feature.
- Marking a trial reviewed clears highlighting for that trial.
- The app runs locally via a single command against a SQLite file. The database file is git-ignored.

## Testing Decisions

There is no existing test suite; this spec establishes the first one. `pytest` is the framework.

A good test here exercises externally observable behaviour — given this stored history and this incoming record, what changes are detected and what does storage contain afterwards — and never asserts on internal call sequences or private helpers. Tests must not touch the network.

**Tested through one seam.** Tests drive the monitor's check operation with a stub fetcher returning fixture records, against a temporary SQLite file. This covers gating, diffing, and persistence together through the path the app actually uses. SQLite is exercised for real rather than mocked, because the schema is part of the behaviour under test.

**Coverage:**

- The diff function directly, being pure: scalar changes, list membership changes irrespective of order, empty-to-populated transitions, the two excluded fields never reported, high-signal fields correctly designated.
- The monitor through its seam: adding a trial writes a baseline and no changes; an unchanged last-updated timestamp short-circuits without diffing; a changed timestamp produces exactly the expected change rows; successive unreviewed changes each write a row while display resolves to the most recent; marking reviewed clears highlighting without deleting history.
- Synthetic data: rows written carry the flag, deleting by that flag removes all of them, and stored field values contain no synthetic marker text.
- Failure handling: an unreachable API and an unknown NCT ID both leave storage unchanged.

Fixtures are captured from the real NCT03412565 record so tests run against genuine registry shape, with mutated copies for the change cases.

## Out of Scope

- Extracting or storing results data. Results are linked to on ClinicalTrials.gov.
- Automatic or scheduled checking. Manual only; a scheduler is the obvious next step and requires no data model change.
- Notifications outside the app — email, Slack, digests.
- Searching or browsing for trials to add.
- Authentication, user accounts, per-user watchlists.
- Hosting or deployment. Local only, which means the watchlist is not genuinely shared until it is hosted.
- Per-field change history, and any view showing a field's original value across multiple changes.
- Elapsed-time calculations on date changes.
- Bulk import of trials.
- Monitoring the fields deliberately cut from the profile: sites, countries, publications, documents.

## Further Notes

The first test case is NCT03412565 (PLEIADES) — Janssen's Phase 2 study of subcutaneous daratumumab across four standard multiple myeloma regimens. It is completed, has results posted, and its record was last updated 2025-04-29. It will almost certainly never change again, which is precisely why the synthetic data path exists.

Two decisions are worth revisiting once the prototype is in front of users. Manual checking is not the real product — nobody logs in daily to press a button — and the shared watchlist is aspirational while the app runs on one analyst's laptop. Both were accepted deliberately to reach viewable output faster, and neither requires a schema change to fix.

The choice to retain raw records rather than derived profiles is a hedge against scope growth in the monitored field set. That set has already been revised twice during design.
