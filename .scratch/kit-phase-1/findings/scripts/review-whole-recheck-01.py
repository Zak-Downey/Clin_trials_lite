"""review-whole-recheck-01: handover.py, a starter-kit file, names nothing of this product in what it prints.

Run from the repo root: .venv/bin/python -m pytest -p tests.conftest .scratch/kit-phase-1/findings/scripts/review-whole-recheck-01.py -q
Red today: TERMS_OWN and TERMS both say the walk-through runs "against a stand-in for the trials registry".
"""

import re

import handover


def test_the_page_s_explanation_of_the_walk_through_names_nothing_of_this_product():
    for text in (handover.TERMS_OWN, handover.TERMS):
        assert not re.search(r"trial|registry|watchlist|clinical", text, re.I), text
