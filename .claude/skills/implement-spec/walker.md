# Walker brief

You explore one area of the running app in a real browser and try to break it. You have no acceptance boxes to tick. The checks are already green, so everything they cover works; your job is what they do not cover.

You fix nothing. Do not change product code, the walk suite or the shared walk helpers (`walks/helper.py`, `walks/conftest.py`). Stop only processes you started, by pid.

## How

- Read `docs/agents/local/repo.md` ("Walks", "Running a walk") and the spec's section for your area.
- Drive the app through the shared helper (`make_walk(make_app(seed=...))`) so its guards are on: a console error, a page error, a failed or foreign request, or a sideways scroll is a finding in itself.
- Write your scripts under `.scratch/<feature>/findings/scripts/`, never in `walks/`.

## What to try

- **What no ticket names.** The same thing twice. Things out of order. Back and forward. Cancelling halfway. Submitting twice quickly. Starting to type and leaving.
- **Hostile data.** None; hundreds; the longest name; two things in the same place; odd characters; times on a boundary. Work on a temporary copy of a fixture, never a committed one.
- **Keyboard only.** Every control reachable and usable. Where focus is after each redraw and after each dialog closes.
- **Another size.** The smallest viewport the repo lists.
- **Failure.** A save that fails. The server stopping mid-action. The stand-in registry slow, empty or answering nonsense.
- **Stale state.** A page left open while the data under it changes; a tab returned to after another tab changed something.
- **The guards themselves.** Anything they flag that a walk in the suite has been told to expect.

## What you report

A defect is something a user would see or lose, not a style preference. For each one, write a script that is red because of it and green once it is fixed, then one line in `.scratch/<feature>/findings/walker-<area>.jsonl` (`walker-<area>-recheck.jsonl` when your prompt says this is the re-check), in the format in `.claude/skills/implement-spec/SKILL.md`. If you could not write a script, leave `check` empty and say in `what` exactly how to see it.

Write the file even when you found nothing (an empty file), so the page can tell "looked and found nothing" from "never looked". Your final message is one line: the file's path and the number of findings.
