# 04: The map of the pages, and the test that keeps it current

**What to build:** `docs/agents/local/walk-map.json`, this product's map, and the function that reads it. The map holds `shared` (files every page depends on), `always` (walk files that run in every picked run: the walk-guard tests and the acceptance walk), `areas` (each with a name, the source files that belong to it and the walk files that cover it) and `none` (files that reach no walk: records, docs, the unit tests). Files are paths or glob patterns. Start from the lists "Areas" and "Shared client plumbing" in `repo.md` and from what each walk file opens; when in doubt about a file, put it in `shared`, where the cost is time. The function that reads a map and says what is wrong with it is a kit file and names nothing of this product: a walk file in neither `always` nor an area; a file git tracks that `shared`, an area or `none` does not place; a pattern that matches nothing; a listed walk file that does not exist; an area with no walk. A unit test runs it on this repo's map, so a new source file or walk that the map does not place turns the ordinary checks red. The two prose lists in `repo.md` give way to one line that points to the map and says how to add to it. Spec: `.scratch/kit-phase-3/spec.md`, "The map" and "The map is kept current by a cheap test".

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Red first: each fault named above, in a hand-made map over a small repo in a temporary folder, is reported in words that name the file and the fault
- [ ] Red first: this repo's map is read by a unit test, which fails when a walk file is taken out of it and when a new file is added under `webapp/` without a place
- [ ] Every walk file and every tracked file of this repo is placed, and the comments say which files went to `shared` out of doubt
- [ ] `repo.md` points to the map in place of the two lists, and `python3 checks.py` ends green

## Comments
