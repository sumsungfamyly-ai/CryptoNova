import time
from collections import defaultdict, deque


class RateLimited(Exception):
    pass


class Limiter:
    """Sliding window, per-process. Use Redis-backed limiter when running several backend instances."""
    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: int, now: float | None = None) -> None:
        t = time.time() if now is None else now
        q = self.hits[key]
        while q and q[0] <= t - window:
            q.popleft()
        if len(q) >= limit:
            raise RateLimited()
        q.append(t)

    def reset(self, key: str) -> None:
        self.hits.pop(key, None)


limiter = Limiter()


def can_manage(actor_rank: int, target_rank: int, new_rank: int | None = None) -> bool:
    """Lower rank number = more power. Actors may only manage strictly weaker admins and only grant strictly weaker roles."""
    return target_rank > actor_rank and (new_rank is None or new_rank > actor_rank)
