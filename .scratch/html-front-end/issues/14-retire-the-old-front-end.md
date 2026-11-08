# 14: Retire the Streamlit app and the GitHub Pages pipeline; rewrite the README

**Blocked by:** 06, 11, 12, 13

**Status:** ready-for-agent

**Touches:** *

**Spec sections (read these, not this ticket's paraphrase):** Implementation Decisions › Shape ("Retired in this spec"); Testing Decisions (tests for retired code); End State 2; User Stories 1, 102; ADR 0003.

**What to build:** Delete the Streamlit entry point and views, the stlite page, the site build, the in-browser transport, the Pages publish workflow, Streamlit in the requirements, and the tests that exist only for them. Reword comments in kept modules and tests that name Streamlit. Rewrite the README for the local app. Infrastructure: no design rows.

- [ ] `grep -rliE 'streamlit|stlite' --exclude-dir=.git --exclude-dir=.scratch --exclude-dir=adr .` finds nothing (End State 2)
- [ ] The requirements list no Streamlit; a fresh virtual environment installs from them and `gate.py checks` passes
- [ ] The Pages workflow, the site build, the stlite page and the in-browser transport are gone, with their tests
- [ ] The README says how to start the app (`python run.py`), where the database file lives and how to back it up by copying it, that it runs on this machine only, and that the old published site is retired
- [ ] `docs/agents/local/repo.md` no longer describes the Streamlit test harness or the Pages workflow

## Comments
