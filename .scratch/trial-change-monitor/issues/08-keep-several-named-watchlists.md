# 08: Keep several named watchlists

**What to build:** Everything monitored sits in one undifferentiated watchlist. Someone covering two therapy areas has no way to keep myeloma apart from lung, so the table they read every morning is half other people's business. There is also only one page, so adding a trial and reading what moved compete for the same screen.

Split the app into **two pages** and give the watchlist a **name**:

- A **Watchlist** page that reads one named list at a time. Which list is showing is picked from a control at the top; the table, the profile that opens under it, and the activity feed all narrow to that list. The count already in the subheading counts the list, not the database.
- A **Search** page, which for now holds the "paste an NCT ID" box moved off the watchlist page, plus the choice of which list the pasted trial joins. Adding is done here; reading is done there.

A trial can sit in **more than one list**: someone covering two overlapping indications should see the same study in both, and taking it out of one must leave the other alone. So membership is a relation between a trial and a list, not a column on the trial. Deleting a trial from a list stops it appearing there; it stops being monitored only when it belongs to no list at all.

Existing monitored trials have to keep working, so a database that predates lists gets a single default list holding everything it already had, the same way a late column is added on connect today. Nobody should have to re-add a trial.

Renaming a list keeps its membership. Two lists cannot share a name, since the name is how the reader tells them apart.

**Prototype:** branch `prototype/watchlist-query`, file `prototype_search.py`. Three ways of building a query and filing the results were compared on the real page against the live registry; **variant A won**. The verdict covers the query surface, which is ticket 09; what this ticket takes from it is the decision that the surface belongs on its own page, and that the destination list is chosen as an explicit step rather than implied by where you are standing. Do not promote its code: the prototype's lists live in session state and never reach the database, which is the gap this ticket closes.

The list and its membership are storage's business, and which trials a list holds is a question the monitor answers, so nothing new should need to reach for SQL. `app.py` stays a thin view, and the page split should not push view logic back into it.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] The app has a Watchlist page and a Search page, navigable from the sidebar, and the browser lands on the watchlist
- [ ] A named list can be created, renamed, and deleted, and two lists cannot share a name
- [ ] The watchlist page shows one named list at a time, chosen at the top, and its table, opened profile, and activity feed all narrow to that list
- [ ] The paste-an-NCT-ID box lives on the Search page and names the list the trial joins
- [ ] A trial can belong to several lists at once, and removing it from one leaves it in the others
- [ ] A trial belonging to no list is no longer monitored
- [ ] A database that predates lists opens with everything it already monitored in a single default list, with no re-adding
- [ ] "Check all" and "Mark as reviewed" behave as they do today, and a change detected on a trial in two lists is visible from both
- [ ] The walkable loop still runs end to end: create a list, add a trial to it, check, simulate a change, check, read what moved, open the row, read the cards, review it
- [ ] Tests cover lists and membership without running Streamlit: creating and renaming, the duplicate-name refusal, a trial in two lists, removal from one leaving the other, and the migration of a pre-lists database
