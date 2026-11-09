"""Prices: the one reader of factory.json `prices` and the one cost function, used by the dashboard page and by `close`'s Facts."""
from __future__ import annotations

KINDS = ("input", "output", "cache_read", "cache_write")


def number(value) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def read_prices(config: dict) -> dict:
    """{model: {kind: dollars per million}} from a config's `prices`; an entry that is not an object is left out."""
    prices = config.get("prices") if isinstance(config, dict) else None
    return {m: p for m, p in prices.items() if isinstance(p, dict)} if isinstance(prices, dict) else {}


def priced_cost(record: dict, prices: dict):
    """The record's cost in dollars, or None when its model has no price or the price leaves out a kind the record used."""
    price = prices.get(record.get("model", ""))
    if not price:
        return None
    if any(number(record.get(kind)) and not isinstance(price.get(kind), (int, float)) for kind in KINDS):
        return None
    return sum(number(record.get(kind)) * number(price.get(kind)) for kind in KINDS) / 1e6
