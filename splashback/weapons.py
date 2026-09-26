"""Creating projectiles: the player's paint blobs and bombs, and the gloom spit of enemies."""

import math

from . import config as C
from .entities import Projectile

SPREAD_STEP = 0.17
JITTER = 0.05

def fire_paint(world):
    """Fire one volley from the player's nozzle towards where they face."""
    p = world.player
    shots = 1 + p.extra_shots + (2 if p.triple_timer > 0.0 else 0)
    base = math.atan2(p.face_y, p.face_x)
    life = p.shot_range / p.shot_speed
    nozzle = p.radius + 4.0
    first = -SPREAD_STEP * (shots - 1) / 2.0
    for i in range(shots):
        angle = base + first + SPREAD_STEP * i + world.rng.uniform(-JITTER, JITTER)
        ca, sa = math.cos(angle), math.sin(angle)
        world.projectiles.append(Projectile(
            "paint", p.x + ca * nozzle, p.y + sa * nozzle,
            ca * p.shot_speed, sa * p.shot_speed,
            5, p.damage, life, p.splash, p.paint_amount, world.hue))

def throw_bomb(world, target_x, target_y):
    """Lob a bomb that bursts where the player aimed (or at the maximum throw)."""
    p = world.player
    dx, dy = target_x - p.x, target_y - p.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        dx, dy, dist = p.face_x, p.face_y, 1.0
    travel = min(max(dist, 40.0), C.BOMB_MAX_THROW)
    ux, uy = dx / dist, dy / dist
    world.projectiles.append(Projectile(
        "bomb", p.x, p.y, ux * C.BOMB_SPEED, uy * C.BOMB_SPEED,
        8, C.BOMB_DAMAGE, travel / C.BOMB_SPEED, C.BOMB_RADIUS, 3, world.hue))

def spit_glob(world, enemy):
    p = world.player
    dx, dy = p.x - enemy.x, p.y - enemy.y
    dist = math.hypot(dx, dy) or 1.0
    speed = C.GLOB_SPEED * world.difficulty["speed"]
    world.projectiles.append(Projectile(
        "glob", enemy.x, enemy.y, dx / dist * speed, dy / dist * speed,
        C.GLOB_RADIUS, 1, 2.4, 26.0, -2))
