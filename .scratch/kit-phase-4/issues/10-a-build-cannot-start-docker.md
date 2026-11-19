# 10: A build cannot start Docker

**What to build:** During `kit-phase-3` a builder started Docker Desktop and pulled a Python image to try a test on Linux, unasked, and left Docker running. `.claude/settings.json` gains deny lines that refuse the building agent `docker`, `docker-compose` and opening the Docker app (`open -a Docker`), placed after the refusal of `--no-verify` from ticket 07; the test of the settings pins them. Nothing else in the file changes. `docs/agents/local/repo.md` says, in its "Not checkable by a walk here" line or beside it, that a build starts no program outside this repo's own, that Linux is not checkable on the owner's machine, and that a fault which needs Linux to be seen is named first in `now_what`: the run on GitHub is where Linux is checked. The refusals stop those commands only, and the sentence does not claim more. **If the session is not allowed to edit a file under `.claude/`**, do not wait and do not try another way round: add the lines and where they go to `.scratch/kit-phase-4/settings-edit.md`, beside ticket 07's if that is there; the ticket is complete in either form, and `now_what` says which. Spec: `.scratch/kit-phase-4/spec.md`, "Docker".

**Blocked by:** 07

**Status:** done

- [x] Red first: the test of the settings fails until `docker`, `docker-compose` and opening the Docker app are refused, or `settings-edit.md` holds the edit in full
- [x] `.claude/settings.json` is otherwise unchanged and still valid JSON, and no other file under `.claude/` changed
- [x] `repo.md` has the sentence, true whichever form the ticket took
- [ ] `python3 checks.py` ends green on this ticket's commit, and `python3 checks.py --comments` lists nothing

## Comments
