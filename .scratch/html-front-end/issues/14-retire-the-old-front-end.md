# 14: Retire the Streamlit app and the GitHub Pages pipeline; rewrite the README

**Blocked by:** 06, 11, 12, 13

**Status:** ready-for-agent

**Touches:** *

**Spec sections (read these, not this ticket's paraphrase):** Implementation Decisions › Shape ("Retired in this spec"); Testing Decisions (tests for retired code); End State 2; User Stories 1, 102; ADR 0003.

**What to build:** Delete the Streamlit entry point and views, the stlite page, the site build, the in-browser transport, the Pages publish workflow, Streamlit in the requirements, and the tests that exist only for them. Reword comments in kept modules and tests that name Streamlit. Rewrite the README for the local app. Infrastructure: no design rows.

- [x] `grep -rliE 'streamlit|stlite' --exclude-dir=.git --exclude-dir=.scratch --exclude-dir=adr .` finds nothing (End State 2) — check: unit (grep also run excluding .venv and .claude, the only match is the .git worktree pointer file whose path holds the worktree's name)
- [x] The requirements list no Streamlit; a fresh virtual environment installs from them and `gate.py checks` passes — check: unit; check: walks (fresh venv under TMPDIR installed from the requirements with no streamlit: 452 unit and 189 walks passed)
- [x] The Pages workflow, the site build, the stlite page and the in-browser transport are gone, with their tests — check: unit (all deleted, monitor and api_checks now use time.sleep)
- [x] The README says how to start the app (`python run.py`), where the database file lives and how to back it up by copying it, that it runs on this machine only, and that the old published site is retired — test: test_the_readme_says_how_to_start_the_app; test: test_the_readme_says_where_the_database_file_lives_and_how_to_back_it_up; test: test_the_readme_says_the_app_runs_on_this_machine_only; test: test_the_readme_says_the_old_published_site_is_retired; red: .scratch/html-front-end/red/14-unit-e6b4ca4.txt
- [x] `docs/agents/local/repo.md` no longer describes the Streamlit test harness or the Pages workflow — check: unit (Tooling and CI sections rewritten)

## Comments
