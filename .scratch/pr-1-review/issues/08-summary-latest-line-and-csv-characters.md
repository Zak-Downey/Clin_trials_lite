# 08: The Summary's Latest line names the newest check, and the CSV opens with its characters intact

**Blocked by:** None

**Status:** needs-triage

**Touches:** webapp/api_summary.py, briefing.py

**Spec sections (read these, not this ticket's paraphrase):** Findings › F2, F14; Open list item on CSV formula cells. Root: User Stories 87, 89; Design coverage 10/3, 10/4.

**What to build:** `_latest` takes the newest check as the latest `detected` stamp over the trial's moves, whatever order the fields are sorted in. `as_csv` starts with a byte-order mark so a spreadsheet reads it as UTF-8. If the Open list item on formula cells stands (its recommendation is do), `as_csv` also prefixes `'` to any cell starting with `=`, `+`, `-`, `@`, a tab or a carriage return, and the README says so.

- [ ] Test: a trial whose newest check moved only the brief title and whose older check moved the completion date reads "Latest: brief title updated."
- [ ] Test: the CSV starts with U+FEFF, and read with `utf-8-sig` its first header is the first column's name and an empty value is the em dash
- [ ] Test: a title beginning `=`, `+`, `-` or `@` is written to the CSV prefixed with `'`, and the copied text and the page keep it exact (only if the Open list item on formula cells is not rejected)

## Comments
