"""One wave's worth of simulation: player, enemies, projectiles and pickups on an arena.

The world knows nothing about windows or menus. It is advanced with
``step(dt, controls)`` and reports what happened through ``events``, a list of
tuples that the game layer drains after every step:

    ("kill", x, y, kind, score)   ("hit", x, y)          ("hurt", x, y)
    ("dead", x, y)                ("splat", x, y, hue, radius)
    ("gloom", x, y, radius)       ("bomb", x, y, hue)    ("pickup", x, y, kind)
    ("spawn", x, y, kind)         ("thud", x, y)
"""

import math

from . import config as C
from .enemies import SPECS, update_enemy
from .entities import Enemy, Pickup
from .navigation import FlowField
from .physics import SpatialHash, move_circle
from .weapons import fire_paint, spit_glob, throw_bomb

PICKUP_KINDS = ("heart", "bomb", "rapid", "triple")
PICKUP_WEIGHTS = (3, 3, 2, 2)
MAX_ENEMY_RADIUS = max(spec.radius for spec in SPECS.values())

class Controls:
    """What the player wants this tick. Aim is a point in world coordinates."""

    __slots__ = ("move_x", "move_y", "aim_x", "aim_y", "fire", "bomb")

    def __init__(self):
        self.move_x = 0.0
        self.move_y = 0.0
        self.aim_x = 0.0
        self.aim_y = 0.0
        self.fire = False
        self.bomb = False

class World:
    def __init__(self, arena, player, rng, difficulty="normal", hue=0, wave=1):
        self.arena = arena
        self.player = player
        self.rng = rng
        self.difficulty = C.DIFFICULTY.get(difficulty, C.DIFFICULTY["normal"])
        self.hue = hue
        # Later waves bring tougher and slightly quicker creatures.
        growth = max(0, wave - 1)
        self.enemy_hp_mult = self.difficulty["hp"] * (1.0 + 0.07 * growth)
        self.enemy_speed_mult = self.difficulty["speed"] * min(1.25, 1.0 + 0.015 * growth)
        self.flow = FlowField(arena)
        self.enemies = []
        self.projectiles = []
        self.pickups = []
        self.events = []
        self.time = 0.0
        self._hash = SpatialHash(arena.cols * C.TILE, arena.rows * C.TILE, 64)
        self._near = []
        self._deaths = False
        player.x, player.y = arena.spawn_point()
        player.alive = player.hp > 0
        self.flow.update(arena.tile_at(player.x, player.y))

    # --- queries ----------------------------------------------------------------

    def query_enemies(self, x, y, radius):
        """Enemies that may overlap a circle. The returned list is reused; do not keep it."""
        return self._hash.query(x, y, radius + MAX_ENEMY_RADIUS, self._near)

    def enemy_count(self):
        return sum(1 for e in self.enemies if e.alive)

    def spawn_candidates(self, min_tiles=7):
        """Floor tiles far enough (by walking distance) from the player to spawn on."""
        return self.flow.tiles_farther_than(min_tiles * 10)

    # --- spawning ---------------------------------------------------------------

    def spawn_enemy(self, kind, x, y, spawn_time=0.8):
        e = Enemy(SPECS[kind], x, y, self.enemy_hp_mult, self.enemy_speed_mult, spawn_time)
        e.wobble = 1.0 if self.rng.random() < 0.5 else -1.0
        e.sight_timer = self.rng.random() * 0.2
        self.enemies.append(e)
        self.events.append(("spawn", x, y, kind))
        return e

    def spit_glob(self, enemy):
        spit_glob(self, enemy)

    # --- stepping ---------------------------------------------------------------

    def step(self, dt, controls):
        self.time += dt
        p = self.player
        if p.alive:
            self._update_player(dt, controls)
            tile = self.arena.tile_at(p.x, p.y)
            if tile >= 0:
                self.flow.update(tile)
        self._rebuild_hash()
        enemies = self.enemies
        for i in range(len(enemies)):   # splitters may append while we iterate
            e = enemies[i]
            if e.alive:
                update_enemy(self, e, dt)
        self._update_projectiles(dt)
        self._update_pickups(dt)
        if p.alive:
            self._touch_enemies()
        self._compact()

    def _rebuild_hash(self):
        h = self._hash
        h.clear()
        for e in self.enemies:
            if e.alive:
                h.insert(e, e.x, e.y)

    def _update_player(self, dt, controls):
        p = self.player
        mx, my = controls.move_x, controls.move_y
        length = math.hypot(mx, my)
        if length > 1.0:
            mx, my = mx / length, my / length
        p.moving = length > 0.05
        if p.moving:
            speed = p.speed * self.arena.speed_factor(p.x, p.y, C.SPEED_ON_PAINT, C.SPEED_ON_GLOOM)
            p.x, p.y, _ = move_circle(self.arena, p.x, p.y, p.radius, mx * speed * dt, my * speed * dt)
        ax, ay = controls.aim_x - p.x, controls.aim_y - p.y
        aim_len = math.hypot(ax, ay)
        if aim_len > 2.0:
            p.face_x, p.face_y = ax / aim_len, ay / aim_len
        p.fire_timer -= dt
        p.invuln = max(0.0, p.invuln - dt)
        p.rapid_timer = max(0.0, p.rapid_timer - dt)
        p.triple_timer = max(0.0, p.triple_timer - dt)
        if controls.fire and p.fire_timer <= 0.0:
            fire_paint(self)
            p.fire_timer = p.fire_cooldown * (0.5 if p.rapid_timer > 0.0 else 1.0)
        if controls.bomb and p.bombs > 0:
            p.bombs -= 1
            throw_bomb(self, controls.aim_x, controls.aim_y)

    def _update_projectiles(self, dt):
        arena = self.arena
        p = self.player
        for pr in self.projectiles:
            if not pr.alive:
                continue
            pr.x += pr.vx * dt
            pr.y += pr.vy * dt
            pr.life -= dt
            if pr.kind == "paint":
                if arena.is_solid_point(pr.x, pr.y):
                    self._burst_paint(pr, pr.x - pr.vx * dt, pr.y - pr.vy * dt)
                    continue
                # Blobs drip a thin line of paint on every tile they fly over.
                tile = arena.tile_at(pr.x, pr.y)
                if tile != pr.last_tile:
                    pr.last_tile = tile
                    arena.add_paint(tile, 1, pr.hue)
                for e in self.query_enemies(pr.x, pr.y, pr.radius):
                    if not e.active:
                        continue
                    reach = e.radius + pr.radius
                    dx, dy = e.x - pr.x, e.y - pr.y
                    if dx * dx + dy * dy <= reach * reach:
                        self.damage_enemy(e, pr.damage, pr.vx, pr.vy)
                        self._burst_paint(pr, pr.x, pr.y)
                        break
                if pr.alive and pr.life <= 0.0:
                    self._burst_paint(pr, pr.x, pr.y)
            elif pr.kind == "glob":
                if arena.is_solid_point(pr.x, pr.y) or pr.life <= 0.0:
                    self._burst_gloom(pr, pr.x - pr.vx * dt, pr.y - pr.vy * dt)
                    continue
                if p.alive:
                    reach = p.radius + pr.radius
                    dx, dy = p.x - pr.x, p.y - pr.y
                    if dx * dx + dy * dy <= reach * reach:
                        self._burst_gloom(pr, pr.x, pr.y)
                        self.hurt_player(pr.x, pr.y)
            else:
                if arena.is_solid_point(pr.x, pr.y):
                    pr.x -= pr.vx * dt
                    pr.y -= pr.vy * dt
                    self._explode(pr)
                elif pr.life <= 0.0:
                    self._explode(pr)

    def _burst_paint(self, pr, x, y):
        pr.alive = False
        self.arena.splash(x, y, pr.splash, pr.amount, pr.hue)
        self.events.append(("splat", x, y, pr.hue, pr.splash))

    def _burst_gloom(self, pr, x, y):
        pr.alive = False
        self.arena.splash(x, y, pr.splash, pr.amount)
        self.events.append(("gloom", x, y, pr.splash))

    def _explode(self, pr):
        pr.alive = False
        r = pr.splash
        self.arena.splash(pr.x, pr.y, r, pr.amount, pr.hue)
        self.events.append(("bomb", pr.x, pr.y, pr.hue))
        hits = list(self.query_enemies(pr.x, pr.y, r))
        for e in hits:
            if not e.alive:
                continue
            dx, dy = e.x - pr.x, e.y - pr.y
            if dx * dx + dy * dy <= (r + e.radius) ** 2:
                if e.spawn_timer > 0.0:
                    e.spawn_timer = 0.0
                self.damage_enemy(e, pr.damage, dx, dy)
        # Bombs also wash away gloom spit in the blast.
        for other in self.projectiles:
            if other.alive and other.kind == "glob":
                dx, dy = other.x - pr.x, other.y - pr.y
                if dx * dx + dy * dy <= r * r:
                    other.alive = False

    def damage_enemy(self, e, amount, push_x=0.0, push_y=0.0):
        e.hp -= amount
        e.hit_flash = 0.09
        push = math.hypot(push_x, push_y)
        if push > 1e-6 and e.kind != "brute":
            e.x, e.y, _ = move_circle(self.arena, e.x, e.y, e.radius,
                                      push_x / push * 4.0, push_y / push * 4.0)
        if e.hp > 0.0:
            self.events.append(("hit", e.x, e.y))
            return
        e.alive = False
        self._deaths = True
        self.arena.splash(e.x, e.y, e.radius + 22.0, 2, self.hue)
        self.events.append(("kill", e.x, e.y, e.kind, e.spec.score))
        if e.kind == "splitter":
            for sign in (-1.0, 1.0):
                mini = self.spawn_enemy("mini", e.x + sign * 8.0, e.y, spawn_time=0.0)
                mini.x, mini.y, _ = move_circle(self.arena, mini.x, mini.y, mini.radius, 0.0, 0.0)
        elif self.rng.random() < C.PICKUP_CHANCE:
            self._drop_pickup(e.x, e.y)

    def _drop_pickup(self, x, y):
        kind = self.rng.choices(PICKUP_KINDS, PICKUP_WEIGHTS)[0]
        if kind == "heart" and self.player.hp >= self.player.max_hp:
            kind = "bomb"
        if kind == "bomb" and self.player.bombs >= self.player.max_bombs:
            kind = "rapid"
        self.pickups.append(Pickup(kind, x, y))

    def _update_pickups(self, dt):
        p = self.player
        for pk in self.pickups:
            if not pk.alive:
                continue
            pk.life -= dt
            if pk.life <= 0.0:
                pk.alive = False
                continue
            reach = p.radius + 12.0
            dx, dy = p.x - pk.x, p.y - pk.y
            if p.alive and dx * dx + dy * dy <= reach * reach:
                pk.alive = False
                self.apply_pickup(pk.kind)
                self.events.append(("pickup", pk.x, pk.y, pk.kind))

    def apply_pickup(self, kind):
        p = self.player
        if kind == "heart":
            p.hp = min(p.max_hp, p.hp + 1)
        elif kind == "bomb":
            p.bombs = min(p.max_bombs, p.bombs + 1)
        elif kind == "rapid":
            p.rapid_timer = C.POWERUP_TIME
        elif kind == "triple":
            p.triple_timer = C.POWERUP_TIME

    def _touch_enemies(self):
        p = self.player
        if p.invuln > 0.0:
            return
        for e in self.query_enemies(p.x, p.y, p.radius):
            if not e.active:
                continue
            reach = e.radius + p.radius - 2.0
            dx, dy = p.x - e.x, p.y - e.y
            d2 = dx * dx + dy * dy
            if d2 <= reach * reach:
                self.hurt_player(e.x, e.y)
                d = math.sqrt(d2) or 1.0
                p.x, p.y, _ = move_circle(self.arena, p.x, p.y, p.radius, dx / d * 22.0, dy / d * 22.0)
                return

    def hurt_player(self, from_x, from_y):
        p = self.player
        if p.invuln > 0.0 or not p.alive:
            return False
        p.hp -= 1
        p.invuln = C.INVULN_TIME
        self.arena.splash(p.x, p.y, 30.0, -1)
        self.events.append(("hurt", p.x, p.y))
        if p.hp <= 0:
            p.hp = 0
            p.alive = False
            self.events.append(("dead", p.x, p.y))
        return True

    def _compact(self):
        if self._deaths:
            self.enemies[:] = [e for e in self.enemies if e.alive]
            self._deaths = False
        projectiles = self.projectiles
        if projectiles and not all(pr.alive for pr in projectiles):
            projectiles[:] = [pr for pr in projectiles if pr.alive]
        pickups = self.pickups
        if pickups and not all(pk.alive for pk in pickups):
            pickups[:] = [pk for pk in pickups if pk.alive]
