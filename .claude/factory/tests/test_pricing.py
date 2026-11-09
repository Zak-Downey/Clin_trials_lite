"""Prices: the one reader and the one cost function.

Lacks: a real factory.json from a user's repo; prices in a currency other than dollars per million.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import unittest

import fixtures  # noqa: F401  (puts the gate package on the path)

from gate.pricing import priced_cost, read_prices

ALL = {"input": 3, "output": 15, "cache_read": 0.3, "cache_write": 3.75}


class Prices(unittest.TestCase):
    def test_read_prices_drops_entries_that_are_not_objects_and_a_prices_that_is_not_one(self):
        """read_prices drops entries that are not objects and a prices that is not one"""
        self.assertEqual(read_prices({"prices": {"a": ALL, "b": "x"}}), {"a": ALL})
        self.assertEqual(read_prices({"prices": "free"}), {})
        self.assertEqual(read_prices({}), {})

    def test_a_missing_kind_is_unpriced_only_when_the_record_used_it(self):
        """A kind the price leaves out makes a record unpriced only when the record used it"""
        used = {"model": "m", "input": 1000000, "cache_read": 1}
        self.assertIsNone(priced_cost(used, {"m": {"input": 3, "output": 15}}))
        self.assertEqual(priced_cost({"model": "m", "input": 1000000, "cache_read": 0}, {"m": {"input": 3}}), 3.0)
        self.assertIsNone(priced_cost({"model": "other", "input": 1}, {"m": ALL}))

    def test_all_four_kinds_are_priced(self):
        """Each of the four kinds is priced"""
        for kind, price in ALL.items():
            self.assertAlmostEqual(priced_cost({"model": "m", kind: 1000000}, {"m": ALL}), price)
