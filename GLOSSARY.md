# Trial Change Monitor

Watches competitors' ClinicalTrials.gov records and shows a medical-affairs analyst what has moved since they last looked.

## Language

### Watching trials

**Watchlist**:
A named group of trials the analyst monitors together; a trial can be in several watchlists.
_Avoid_: List, collection, portfolio

**Monitored trial**:
A trial in at least one watchlist, whose registry record the app keeps comparing against what it saw before.
_Avoid_: Watched trial, tracked trial

**Baseline**:
The first registry record taken when a trial starts being monitored; nothing before it is known, and it is never reported as a change.
_Avoid_: Initial snapshot, starting point

**Check for updates**:
Re-fetching a watchlist's monitored trials and running its saved search, at the analyst's request; nothing is checked on a schedule.
_Avoid_: Refresh, sync, check all

**Full recheck**:
A check that compares every monitored field even when the registry's own update date has not moved.
_Avoid_: Compare every field, force check

**Last successful check**:
When a monitored trial's record was last fetched and compared without error; a failed check never moves it.
_Avoid_: Last checked (for a single trial)

### Changes and review

**Change**:
One monitored field whose value differs from the record seen at the previous check, with its previous and new values.
_Avoid_: Update, edit, diff

**Detected**:
When the app observed a change, as opposed to **Registry updated**, the date the sponsor's edit was posted to the registry.
_Avoid_: Changed on, found on

**Review**:
The analyst's act of marking specific changes as read; it applies to the trial in every watchlist that holds it, and never deletes a change.
_Avoid_: Acknowledge, dismiss, clear

**Needs review**:
A trial with at least one change not yet reviewed.
_Avoid_: Unread, flagged, alert

**Simulated change**:
A change fabricated by the developer's simulator to demonstrate alerting, always labelled as such.
_Avoid_: Synthetic change, fake change, test change

**Change summary**:
Every change detected in a watchlist over a chosen period, reviewed or not, grouped by trial and then by check, for copying into a briefing or exporting.
_Avoid_: Briefing, report, digest

### Finding trials

**Saved search**:
The one ClinicalTrials.gov query a watchlist re-runs at every check for updates, to find trials it does not yet monitor.
_Avoid_: Remembered search, new-trial search, alert

**New match**:
A trial the saved search found that the watchlist does not monitor, waiting for the analyst to add or dismiss it.
_Avoid_: Found trial, offer, new trial, suggestion

**Add to watchlist**:
Starting to monitor a trial in a watchlist, which takes its baseline.
_Avoid_: Adopt, follow, subscribe

**Dismiss**:
Declining a new match so the saved search does not offer it to that watchlist again, until restored.
_Avoid_: Reject, hide, delete
