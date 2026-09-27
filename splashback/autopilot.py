"""A simple computer player. It runs the title-screen demo and lets tests play whole waves."""

import math
import random

from .navigation import line_of_sight
from .world import Controls

THREAT_RANGE = 170.0
GLOB_RANGE = 90.0
FIRE_RANGE = 360.0

class Autopilot:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.controls = Controls()
        self.goal = None
        self.goal_timer = 0.0

    def _pick_goal(self, world):
        """Head for grey or bare floor that is not crowded, preferring nearby tiles."""
        arena, p = world.arena, world.player
        best, best_score = None, -math.inf
        for _ in range(10):
            idx = self.rng.randrange(arena.cols * arena.rows)
            if arena.solid[idx] or world.flow.distance(idx) >= 1 << 29:
                continue
            x, y = arena.center(idx)
            score = -arena.paint[idx] * 2.0 - math.hypot(x - p.x, y - p.y) / 120.0
            for e in world.enemies:
                if e.alive and abs(e.x - x) + abs(e.y - y) < 120.0:
                    score -= 2.0
            if score > best_score:
                best, best_score = (x, y), score
        return best

    def control(self, world, dt):
        c = self.controls
        p = world.player
        c.bomb = False
        push_x = push_y = 0.0
        target, target_d2 = None, math.inf
        crowd = 0
        for e in world.enemies:
            if not e.alive:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d2 = dx * dx + dy * dy
            if e.spawn_timer <= 0.0 and d2 < target_d2:
                target, target_d2 = e, d2
            reach = THREAT_RANGE + e.radius * 2.0
            if d2 < reach * reach:
                d = math.sqrt(d2) or 1.0
                w = 1.0 - d / reach
                push_x += dx / d * w * w * 3.0
                push_y += dy / d * w * w * 3.0
                if d < 120.0 and e.spawn_timer <= 0.0:
                    crowd += 1
        for pr in world.projectiles:
            if pr.kind != "glob":
                continue
            dx, dy = p.x - pr.x, p.y - pr.y
            d = math.hypot(dx, dy)
            if 1e-6 < d < GLOB_RANGE:
                # Sidestep across the glob's path rather than running along it.
                speed = math.hypot(pr.vx, pr.vy) or 1.0
                side = 1.0 if (pr.vx * dy - pr.vy * dx) > 0 else -1.0
                push_x += -pr.vy / speed * side * 2.0
                push_y += pr.vx / speed * side * 2.0

        self.goal_timer -= dt
        if (self.goal is None or self.goal_timer <= 0.0
                or math.hypot(self.goal[0] - p.x, self.goal[1] - p.y) < 20.0):
            self.goal = self._pick_goal(world)
            self.goal_timer = 2.5
        move_x = move_y = 0.0
        if self.goal is not None:
            gx, gy = self.goal[0] - p.x, self.goal[1] - p.y
            gd = math.hypot(gx, gy)
            if gd > 1e-6:
                move_x, move_y = gx / gd * 0.6, gy / gd * 0.6
        move_x += push_x
        move_y += push_y
        c.move_x, c.move_y = self._avoid_walls(world, p, move_x, move_y)

        if target is not None:
            c.aim_x, c.aim_y = target.x, target.y
            c.fire = (target_d2 < FIRE_RANGE * FIRE_RANGE
                      and line_of_sight(world.arena, p.x, p.y, target.x, target.y))
        else:
            c.aim_x, c.aim_y = p.x + p.face_x * 50.0, p.y + p.face_y * 50.0
            c.fire = False
        if crowd >= 4 and p.bombs > 0 and target is not None:
            c.bomb = True
        return c

    def _avoid_walls(self, world, p, mx, my):
        length = math.hypot(mx, my)
        if length < 1e-6:
            return 0.0, 0.0
        ux, uy = mx / length, my / length
        probe = p.radius + 14.0
        for turn in (0.0, 0.6, -0.6, 1.2, -1.2, 1.9, -1.9):
            ca, sa = math.cos(turn), math.sin(turn)
            rx, ry = ux * ca - uy * sa, ux * sa + uy * ca
            if not world.arena.is_solid_point(p.x + rx * probe, p.y + ry * probe):
                return rx * min(length, 1.0), ry * min(length, 1.0)
        return ux, uy
