"""DEMO price simulator (pure logic, stdlib only). Prices are virtual and NEVER presented as real quotes."""
import math
import random
from datetime import datetime, timedelta
from decimal import Decimal

SIGMA = {"stable": 0.0008, "popular": 0.008, "nova": 0.012}  # per tick (log-return std)
REVERSION = 0.02                                              # pull back toward the anchor


def next_price(price: Decimal, anchor: Decimal, category: str, rng: random.Random) -> Decimal:
    if price <= 0 or anchor <= 0:
        return price
    sigma = SIGMA.get(category, 0.01)
    r = -REVERSION * math.log(float(price / anchor)) + rng.gauss(0, sigma)
    r = max(-0.05, min(0.05, r))  # hard cap per tick
    return max(Decimal("0.00000001"), (price * Decimal(str(math.exp(r)))).quantize(Decimal("0.00000001")))


def backfill(current: Decimal, category: str, points: int, step: timedelta, end: datetime, rng: random.Random) -> list[tuple[datetime, Decimal]]:
    """Random-walk path of `points` samples that ends exactly at `current` (bridge-adjusted)."""
    path, p = [], current
    for _ in range(points):
        p = next_price(p, current, category, rng); path.append(p)
    last = path[-1]
    out = []
    for i, v in enumerate(path):
        adj = Decimal(str(math.pow(float(current / last), (i + 1) / points)))
        out.append((end - step * (points - 1 - i) - step, (v * adj).quantize(Decimal("0.00000001"))))
    return out
