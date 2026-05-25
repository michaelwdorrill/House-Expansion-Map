"""Huntington-Hill apportionment: assign N House seats among the states.

This is the exact method the US uses. Each state gets at least one seat;
remaining seats are handed out one at a time to whichever state has the
highest priority value  pop / sqrt(n*(n+1))  where n is its current seat
count. Deterministic and cheap.
"""
from __future__ import annotations

import math

from states import STATES, TOTAL_APPORTIONMENT_POP


def apportion(house_size: int, populations: dict[str, int] | None = None) -> dict[str, int]:
    """Return {state_name: seats} for the given House size."""
    pops = populations or {name: p for name, (_f, _u, p) in STATES.items()}
    n_states = len(pops)
    if house_size < n_states:
        raise ValueError(f"house_size {house_size} < number of states {n_states}")

    seats = {name: 1 for name in pops}
    remaining = house_size - n_states

    # Priority queue would be ideal; for N up to a few thousand a heap is plenty.
    import heapq

    heap = []  # (-priority, name)
    for name, pop in pops.items():
        # next seat would be the 2nd, so n=1 -> divisor sqrt(1*2)
        priority = pop / math.sqrt(1 * 2)
        heapq.heappush(heap, (-priority, name))

    while remaining > 0:
        neg_priority, name = heapq.heappop(heap)
        seats[name] += 1
        n = seats[name]
        next_priority = pops[name] / math.sqrt(n * (n + 1))
        heapq.heappush(heap, (-next_priority, name))
        remaining -= 1

    return seats


def people_per_rep(house_size: int) -> float:
    return TOTAL_APPORTIONMENT_POP / house_size


def wyoming_rule_size() -> int:
    """House size if every state's seats = round(state_pop / smallest_state_pop)."""
    from states import SMALLEST_STATE_POP

    total = 0
    for _name, (_f, _u, pop) in STATES.items():
        total += max(1, round(pop / SMALLEST_STATE_POP))
    return total


def cube_root_size() -> int:
    """Cube-root rule: House size ~= cube root of national population."""
    return round(TOTAL_APPORTIONMENT_POP ** (1 / 3))


if __name__ == "__main__":
    import json

    result = apportion(435)
    print(json.dumps(result, indent=2, sort_keys=True))
    print("total:", sum(result.values()))
    print("wyoming rule:", wyoming_rule_size())
    print("cube root:", cube_root_size())
