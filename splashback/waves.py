"""Deciding what each wave contains and trickling it into the arena."""

from . import config as C
from .enemies import SPAWNABLE, SPECS

BIG_WAVE_EVERY = 5

def wave_budget(wave, difficulty="normal"):
    mult = C.DIFFICULTY.get(difficulty, C.DIFFICULTY["normal"])["count"]
    return max(3, round((6 + wave * 4) * mult))

def is_big_wave(wave):
    return wave > 0 and wave % BIG_WAVE_EVERY == 0

def build_wave(wave, difficulty, rng):
    """Spend the wave's budget on enemies the wave has unlocked.

    Cheap crawlers stay common, but later waves lean towards the costlier kinds.
    Every fifth wave opens with a pair of brutes.
    """
    wave = max(1, int(wave))
    budget = wave_budget(wave, difficulty)
    plan = []
    if is_big_wave(wave):
        for _ in range(2):
            plan.append("brute")
            budget -= SPECS["brute"].cost
    unlocked = [k for k in SPAWNABLE if SPECS[k].min_wave <= wave]
    weights = {k: (6.0 if k == "crawler" else 1.0 + 0.35 * (wave - SPECS[k].min_wave))
               for k in unlocked}
    while budget > 0:
        options = [k for k in unlocked if SPECS[k].cost <= budget]
        if not options:
            break
        kind = rng.choices(options, [weights[k] for k in options])[0]
        plan.append(kind)
        budget -= SPECS[kind].cost
    # Keep the first few spawns gentle; heavier kinds come later in the wave.
    head = [k for k in plan[:3] if k == "crawler"]
    rest = [k for k in plan[:3] if k != "crawler"] + plan[3:]
    rng.shuffle(rest)
    return head + rest

class WaveDirector:
    """Releases a wave's enemies in small groups, far from the player."""

    def __init__(self, wave, difficulty, rng):
        self.wave = wave
        self.rng = rng
        # Stored reversed so pop() hands them out in plan order.
        self.queue = build_wave(wave, difficulty, rng)[::-1]
        self.total = len(self.queue)
        self.timer = 1.4
        self.interval = max(0.45, 1.7 - wave * 0.08)
        self.max_alive = min(26, 5 + wave * 2)

    @property
    def finished(self):
        return not self.queue

    @property
    def remaining(self):
        return len(self.queue)

    def update(self, dt, world):
        if not self.queue:
            return
        self.timer -= dt
        if self.timer > 0.0 or world.enemy_count() >= self.max_alive:
            return
        self.timer = self.interval
        candidates = world.spawn_candidates(7) or world.spawn_candidates(3)
        if not candidates:
            return
        group = min(len(self.queue), self.rng.randint(1, 3))
        anchor = self.rng.choice(candidates)
        ax, ay = world.arena.center(anchor)
        for i in range(group):
            kind = self.queue.pop()
            jitter = 6.0 * i
            world.spawn_enemy(kind, ax + self.rng.uniform(-jitter, jitter),
                              ay + self.rng.uniform(-jitter, jitter))
