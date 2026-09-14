# 14: Narrow a search by who is running it, where it has got to, and when it started

**What to build:** The search form asks four things — condition, intervention, sponsor, phase — and every one of them names *what kind of study* the analyst wants. None of them says which of those studies are worth reading. A competitor scan on "chronic lymphocytic leukemia" returns 2,614 records; 725 of them have an industry sponsor, and the rest are investigator-led, registry housekeeping and academic follow-ups that nobody covering a commercial therapy area is paid to read. The analyst's own filter today is to eyeball forty rows and tick the ones with a company name in the sponsor column, which is exactly the judgement a filter should have made for them.

Three more axes, each narrowing a search rather than defining one:

**Sponsor type.** The registry classifies every lead sponsor, and that class is the difference between competitor intelligence and everything else. Offered as the classes themselves, tickable in any combination, so "industry only" is one tick and "who else is in this space" is still answerable. Typing a sponsor's *name* already works and is a different question: name finds Janssen, class finds every company like them.

**Trial status.** Where a study has got to. A recruiting Phase 3 and a study withdrawn in 2009 are not the same news, and a search that cannot tell them apart makes the analyst read both.

**Start date.** A window on when the study began, either end open. What a competitor started since January is a different question from what they have ever run, and the second is the only one the tool can currently ask.

All three narrow; none of them asks. A class, a status and a date window describe *which* studies of a kind are wanted, not which kind — they cannot name a programme on their own, so a search naming none of the original four is still refused, and still refused in the same words.

The three travel with a query everywhere one already travels: run from the form now, saved as a list's remembered search and re-run on every check, and read back to the analyst as what the list is watching for. A remembered search saved before these axes existed still runs, and still means what it meant.

**Blocked by:** nothing (13 is in; this extends the query shape it stores)

**Status:** ready-for-human

- [x] A search can be narrowed to one or more sponsor classes, and industry is one tick
- [x] A search can be narrowed to one or more trial statuses
- [x] A search can be narrowed to a start-date window with either end left open
- [x] The three combine with each other and with the original four, and narrow rather than widen
- [x] A search naming only the new axes is refused in the same words as an empty one
- [x] The new axes are saved with a list's remembered search and re-run on every check
- [x] A remembered search stored before these axes existed still runs and still means what it meant
- [x] What a list is watching for reads back the new axes in the analyst's words, not registry codes
- [x] Tests cover: the registry parameters each axis builds, the axes combining, the refusal, an old stored query still running, and the page driving all three
