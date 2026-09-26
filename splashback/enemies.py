"""The gloom creatures: their stats and how each kind decides where to go."""

import math
from dataclasses import dataclass

from . import config as C
from .navigation import line_of_sight
from .physics import move_circle

SIGHT_RANGE = 360.0
SIGHT_RECHECK = 0.2

@dataclass(frozen=True)
class EnemySpec:
    kind: str
    hp: float
    speed: float
    radius: int
    cost: int       # budget points a wave spends on one of these
    score: int
    min_wave: int
    trail: int      # gloom left on each new tile it enters

SPECS = {
    "crawler": EnemySpec("crawler", 3, 80, 10, 1, 10, 1, 1),
    "spitter": EnemySpec("spitter", 4, 62, 11, 3, 25, 2, 0),
    "splitter": EnemySpec("splitter", 6, 56, 14, 3, 30, 3, 1),
    "brute": EnemySpec("brute", 18, 46, 18, 6, 60, 4, 2),
    "mini": EnemySpec("mini", 1.5, 112, 7, 0, 5, 999, 1),
}

SPAWNABLE = ("crawler", "spitter", "splitter", "brute")

def _refresh_sight(world, e, dt):
    """Line-of-sight checks are staggered per enemy rather than done every tick."""
    e.sight_timer -= dt
    if e.sight_timer > 0.0:
        return
    e.sight_timer = SIGHT_RECHECK
    p = world.player
    dx, dy = p.x - e.x, p.y - e.y
    e.sees_player = (dx * dx + dy * dy < SIGHT_RANGE * SIGHT_RANGE
                     and line_of_sight(world.arena, e.x, e.y, p.x, p.y))

def _chase_direction(world, e):
    """Straight at the player when visible, otherwise along the flow field."""
    p = world.player
    dx, dy = p.x - e.x, p.y - e.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0, dist
    if e.sees_player:
        return dx / dist, dy / dist, dist
    fx, fy = world.flow.steer(e.x, e.y)
    if fx == 0.0 and fy == 0.0:
        return dx / dist, dy / dist, dist
    return fx, fy, dist

def _separation(world, e):
    """Push away from overlapping neighbours so crowds spread out instead of stacking."""
    sx = sy = 0.0
    for other in world.query_enemies(e.x, e.y, e.radius + 24.0):
        if other is e or not other.alive:
            continue
        dx, dy = e.x - other.x, e.y - other.y
        min_d = e.radius + other.radius + 2.0
        d2 = dx * dx + dy * dy
        if 1e-6 < d2 < min_d * min_d:
            d = math.sqrt(d2)
            push = (min_d - d) / min_d
            sx += dx / d * push
            sy += dy / d * push
    return sx, sy

def _walk(world, e, dir_x, dir_y, speed, dt):
    sx, sy = _separation(world, e)
    mult = world.arena.speed_factor(e.x, e.y, C.ENEMY_SPEED_ON_PAINT, C.ENEMY_SPEED_ON_GLOOM)
    vx = (dir_x + sx * 1.4) * speed * mult
    vy = (dir_y + sy * 1.4) * speed * mult
    e.x, e.y, blocked = move_circle(world.arena, e.x, e.y, e.radius, vx * dt, vy * dt)
    return blocked

def _update_chaser(world, e, dt):
    dir_x, dir_y, _ = _chase_direction(world, e)
    _walk(world, e, dir_x, dir_y, e.speed, dt)

def _update_spitter(world, e, dt):
    dir_x, dir_y, dist = _chase_direction(world, e)
    if e.sees_player and dist < 300.0:
        e.cooldown -= dt
        if dist < 130.0:
            _walk(world, e, -dir_x, -dir_y, e.speed * 0.8, dt)
        else:
            # Circle-strafe slowly, flipping direction when bumping into walls.
            if _walk(world, e, -dir_y * e.wobble * 0.4, dir_x * e.wobble * 0.4, e.speed, dt):
                e.wobble = -e.wobble
        if e.cooldown <= 0.0:
            world.spit_glob(e)
            e.cooldown = 1.9 * world.difficulty["fire"]
    else:
        e.cooldown = max(e.cooldown, 0.6)
        _walk(world, e, dir_x, dir_y, e.speed, dt)

def _update_brute(world, e, dt):
    if e.state == "walk":
        dir_x, dir_y, dist = _chase_direction(world, e)
        e.cooldown -= dt
        if e.sees_player and dist < 230.0 and e.cooldown <= 0.0:
            e.state, e.timer = "windup", 0.55
            e.dir_x, e.dir_y = dir_x, dir_y
        else:
            _walk(world, e, dir_x, dir_y, e.speed, dt)
    elif e.state == "windup":
        e.timer -= dt
        if e.timer <= 0.0:
            e.state, e.timer = "charge", 0.5
    elif e.state == "charge":
        e.timer -= dt
        speed = e.speed * 7.0
        e.x, e.y, blocked = move_circle(world.arena, e.x, e.y, e.radius,
                                        e.dir_x * speed * dt, e.dir_y * speed * dt)
        if blocked or e.timer <= 0.0:
            e.state, e.timer = "rest", 0.7
            if blocked:
                world.events.append(("thud", e.x, e.y))
    else:
        e.timer -= dt
        if e.timer <= 0.0:
            e.state, e.cooldown = "walk", 1.2

BEHAVIOURS = {
    "crawler": _update_chaser,
    "mini": _update_chaser,
    "splitter": _update_chaser,
    "spitter": _update_spitter,
    "brute": _update_brute,
}

def update_enemy(world, e, dt):
    if e.hit_flash > 0.0:
        e.hit_flash -= dt
    if e.spawn_timer > 0.0:
        e.spawn_timer -= dt
        return
    _refresh_sight(world, e, dt)
    BEHAVIOURS[e.kind](world, e, dt)
    p = world.player
    dx, dy = p.x - e.x, p.y - e.y
    d = math.hypot(dx, dy)
    if d > 1e-6:
        e.look_x, e.look_y = dx / d, dy / d
    tile = world.arena.tile_at(e.x, e.y)
    if tile != e.last_tile:
        e.last_tile = tile
        if e.spec.trail:
            world.arena.add_paint(tile, -e.spec.trail)
