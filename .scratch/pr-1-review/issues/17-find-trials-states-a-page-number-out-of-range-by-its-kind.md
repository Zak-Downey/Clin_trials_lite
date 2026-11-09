# 17: Find trials states a page number outside the search by its kind and never draws an empty page

**Blocked by:** None

**Status:** ready-for-agent

**Touches:** webapp/static/views/find.js, webapp/api_search.py, walks/

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F11; exploration defects E-036, E-037. Found by the exploration round of ticket 11 (`.scratch/pr-1-review/explore/`).

**What to build:** `bad_page` is shown as a refusal beside the form, with no Retry and the query kept in the form, as `bad_dates` and `nothing_asked` are. A page past the last of a search that has matches opens the last page (or says so), never "11-10 of 3 matches" over no results.

- [x] Walk: page=11 in the address shows the refusal sentence with no Retry and the query in the form — walk: test_explore_page_11_is_a_refusal_with_no_retry_and_keeps_the_query_in_the_form; red: .scratch/pr-1-review/red/17-walks-8306648.txt
- [x] Walk: page=2 of a one-page search draws the results, not an empty list — walk: test_explore_page_two_of_a_one_page_search_does_not_draw_an_empty_list; red: .scratch/pr-1-review/red/17-walks-8306648.txt

## Comments
