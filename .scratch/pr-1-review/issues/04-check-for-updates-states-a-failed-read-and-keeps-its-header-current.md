# 04: Check for updates states a failed read, recovers its button, and keeps its header current

**Blocked by:** 01, 03

**Status:** needs-triage

**Touches:** webapp/static/app.js, webapp/static/views/check.js

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F6, F7. Root: User Stories 14–24, 82; Design coverage 1/4, 12/*.

**What to build:** A failed read of a check's state, at mount or in a poll, is stated in words in the status area and leaves Check for updates usable. The header (trial count, last checked, the button's label) is re-read when the watchlist's trials change, on the same `reviewchange` event the sidebar listens to.

- [ ] Walk: with `GET /api/watchlists/<id>/check` answering 500 when the watchlist opens (declared with `walk.expect`), the status area shows the failure in words, not an empty box
- [ ] Walk: with one progress poll failing during a running check, the status area says the progress could not be read and the button is usable again (`aria-disabled` not true) without leaving the page
- [ ] Walk: on a watchlist with a saved search and no trials, adding a match from New matches makes the header read "1 trial monitored" and the button "Check for updates"

## Comments
