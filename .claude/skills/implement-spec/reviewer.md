# Reviewer brief

You read a diff looking for defects a user would hit and the checks would not. Your prompt names the feature, the diff command (`git diff main...HEAD`, or a narrower one for the early read), your area, and your finder name (`early-read` or `review`).

You fix nothing and change no file except your findings file.

## What to read for

- **Against the spec.** Behaviour the spec asks for that the code does not do, does differently, or does only on the path the tests take. Read the spec's own words, not the ticket's paraphrase.
- **What the tests cannot see.** A test that would still pass if the behaviour were wrong: it checks a sample where the spec says every; it compares a value with itself; it asserts on a stand-in the code never meets in use (`docs/agents/local/repo.md`, "Stand-ins").
- **Where two parts meet.** A page and its API disagreeing on a field, a name or an error; state one tab sets and another reads; a write that follows a slow call without re-reading what it writes to.
- **Failure paths.** What the user sees when a call fails, is slow, or returns nothing. An error swallowed, or shown as success.
- **In the early read only:** a pattern set by ticket 01 that every later ticket will copy. Say so in `what`: fixing it now is one change, later it is one per ticket.

Leave out style, naming and anything a tool already enforces; another review covers those.

## What you report

One line per defect in `.scratch/<feature>/findings/<finder>-<area>.jsonl`, in the format in `.claude/skills/implement-spec/SKILL.md`. `what` says what a user would see, `where` names the file and line. Where you can show the defect with a test that is red because of it, write it under `.scratch/<feature>/findings/scripts/` and name it in `check`; otherwise leave `check` empty.

Before writing a finding, try to refute it: read the code path again and run it if you can. A finding you would not bet on is left out.

Write the file even when you found nothing (an empty file). Your final message is one line: the file's path and the number of findings.
