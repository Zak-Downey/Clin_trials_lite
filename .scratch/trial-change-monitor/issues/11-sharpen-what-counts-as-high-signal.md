# 11: Sharpen what counts as high signal

**What to build:** Two problems with what the tool treats as important.

First, a gap. The eligibility criteria — the inclusion and exclusion list that defines who can enter the study — are requested from the registry but never kept, so an amendment widening or narrowing a competitor's target population is invisible today. Only sex and minimum age are monitored, which are the two least likely parts of it to move. Start monitoring the criteria and show them on the disease and eligibility card.

They are long free text, often forty lines of bullets, so they are rendered truncated: an excerpt and a clear statement that the criteria were amended, rather than a full before-and-after that would swamp the card it sits in and every other change on the page with it. The analyst who needs the exact wording follows the registry link.

Second, the ranking. A change to the primary endpoint, the trial's phase, or the eligible population can matter more to competitor monitoring than an edit to the intervention wording, yet all three currently sit in the low-signal group and can be the ones dropped under the "+n more" overflow. Promote primary outcomes, phase and eligibility criteria to the same prominence as a slipped completion date.

Third, a readability fix. The tool already monitors whether a date or an enrolment figure is estimated or actual, but reports a transition as two unrelated entries — the date moved, and separately its type moved. A primary completion date going from estimated to actual is one event and the single most informative thing that can happen to that field. Read the two together, so the change column and the profile say so in one entry rather than two.

**Blocked by:** 10 (both reshape how a change is named in the watchlist column)

**Status:** done

- [x] Eligibility criteria are part of the monitored profile and appear on the disease and eligibility card
- [x] An amendment to the criteria is detected as a change
- [x] The criteria render truncated, with the full text one registry link away, and an amendment does not swamp the card
- [x] Primary outcomes, phase and eligibility criteria carry the same prominence as the existing high-signal fields
- [x] A date or enrolment figure moving between estimated and actual reads as one entry alongside its value, not as a separate unexplained entry
- [x] Adding eligibility criteria to the profile does not report every already-monitored trial as changed on its next ordinary check
- [x] Tests cover: an eligibility amendment being detected, the truncated rendering, the new high-signal ordering, and an estimated-to-actual transition reading as one entry
