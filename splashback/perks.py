"""Between-wave boosts. Each perk changes the player's stats; some can be taken more than once."""

from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Perk:
    id: str
    max_stacks: int
    apply: Callable
    available: Callable = lambda player: True

def _swift(p):
    p.speed *= 1.12

def _rapid(p):
    p.fire_cooldown *= 0.82

def _wide(p):
    p.splash += 10.0

def _heavy(p):
    p.damage += 0.6

def _spread(p):
    p.extra_shots += 1

def _tough(p):
    p.max_hp += 1
    p.hp = min(p.max_hp, p.hp + 1)

def _bomber(p):
    p.max_bombs += 1
    p.bombs = p.max_bombs

def _heal(p):
    p.hp = min(p.max_hp, p.hp + 2)

def _rich(p):
    p.paint_amount += 1

PERKS = {
    perk.id: perk for perk in (
        Perk("swift", 4, _swift),
        Perk("rapid", 4, _rapid),
        Perk("wide", 3, _wide),
        Perk("heavy", 4, _heavy),
        Perk("spread", 2, _spread),
        Perk("tough", 3, _tough),
        Perk("bomber", 3, _bomber),
        Perk("heal", 99, _heal, lambda p: p.hp < p.max_hp),
        Perk("rich", 2, _rich),
    )
}

def offer_perks(rng, taken, player, count=3):
    """Pick distinct perks the player can still take. May return fewer than count."""
    pool = sorted(pid for pid, perk in PERKS.items()
                  if taken.get(pid, 0) < perk.max_stacks and perk.available(player))
    rng.shuffle(pool)
    return pool[:count]

def apply_perk(player, perk_id, taken):
    perk = PERKS.get(perk_id)
    if perk is None:
        raise KeyError(perk_id)
    if taken.get(perk_id, 0) >= perk.max_stacks:
        return False
    perk.apply(player)
    taken[perk_id] = taken.get(perk_id, 0) + 1
    return True

def rebuild_player(player, taken):
    """Re-apply saved perks to a fresh player (used when continuing a saved game)."""
    for perk_id in sorted(taken):
        perk = PERKS.get(perk_id)
        if perk is None:
            continue
        for _ in range(min(int(taken[perk_id]), perk.max_stacks)):
            perk.apply(player)
