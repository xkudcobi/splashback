import random
import unittest

from splashback import config as C
from splashback.arena import Arena
from splashback.entities import Player
from splashback.world import Controls, World

DT = C.FIXED_DT

def open_world(seed=1, difficulty="normal"):
    solid = [False] * (C.COLS * C.ROWS)
    for col in range(C.COLS):
        solid[col] = solid[(C.ROWS - 1) * C.COLS + col] = True
    for row in range(C.ROWS):
        solid[row * C.COLS] = solid[row * C.COLS + C.COLS - 1] = True
    arena = Arena(C.COLS, C.ROWS, solid)
    return World(arena, Player(), random.Random(seed), difficulty)

def aim_at(world, x, y, fire=False, bomb=False):
    c = Controls()
    c.aim_x, c.aim_y = x, y
    c.fire, c.bomb = fire, bomb
    return c

class PlayerTests(unittest.TestCase):
    def test_player_starts_in_middle_and_moves(self):
        w = open_world()
        p = w.player
        start = (p.x, p.y)
        self.assertEqual(start, w.arena.spawn_point())
        c = aim_at(w, p.x + 100, p.y)
        c.move_x = 1.0
        for _ in range(30):
            w.step(DT, c)
        self.assertAlmostEqual(p.x - start[0], C.PLAYER_SPEED * 30 * DT, delta=1.0)

    def test_diagonal_input_is_not_faster(self):
        w = open_world()
        p = w.player
        x0, y0 = p.x, p.y
        c = aim_at(w, 0, 0)
        c.move_x = c.move_y = 1.0
        w.step(DT, c)
        moved = ((p.x - x0) ** 2 + (p.y - y0) ** 2) ** 0.5
        self.assertAlmostEqual(moved, C.PLAYER_SPEED * DT, places=3)

    def test_paint_floor_speeds_the_player_up(self):
        plain, painted = open_world(), open_world()
        for idx in range(len(painted.arena.paint)):
            painted.arena.add_paint(idx, 2)
        for w in (plain, painted):
            c = aim_at(w, 0, 0)
            c.move_x = 1.0
            w.step(DT, c)
        start = plain.arena.spawn_point()[0]
        self.assertGreater(painted.player.x - start, plain.player.x - start)

    def test_firing_respects_cooldown_and_paints(self):
        w = open_world()
        p = w.player
        c = aim_at(w, p.x + 300, p.y, fire=True)
        w.step(DT, c)
        self.assertEqual(len(w.projectiles), 1)
        w.step(DT, c)
        self.assertEqual(len(w.projectiles), 1)
        for _ in range(120):
            w.step(DT, c)
        self.assertGreater(w.arena.painted_count, 5)
        self.assertTrue(any(ev[0] == "splat" for ev in w.events))

    def test_spread_perk_fires_more_blobs(self):
        w = open_world()
        w.player.extra_shots = 2
        w.step(DT, aim_at(w, 0, 0, fire=True))
        self.assertEqual(len(w.projectiles), 3)

class EnemyTests(unittest.TestCase):
    def test_paint_kills_enemy_and_scores(self):
        w = open_world()
        p = w.player
        e = w.spawn_enemy("crawler", p.x + 150, p.y, spawn_time=0.0)
        c = aim_at(w, e.x, e.y, fire=True)
        for _ in range(240):
            c.aim_x, c.aim_y = (e.x, e.y) if e.alive else (c.aim_x, c.aim_y)
            w.step(DT, c)
            if not e.alive:
                break
        self.assertFalse(e.alive)
        kills = [ev for ev in w.events if ev[0] == "kill"]
        self.assertEqual(kills[0][3:], ("crawler", 10))
        self.assertEqual(w.enemy_count(), 0)

    def test_spawning_enemies_cannot_be_hit_or_hurt(self):
        w = open_world()
        p = w.player
        e = w.spawn_enemy("crawler", p.x, p.y, spawn_time=5.0)
        p.invuln = 0.0
        w.step(DT, Controls())
        self.assertEqual(p.hp, p.max_hp)
        self.assertTrue(e.alive)

    def test_enemies_walk_towards_player_and_leave_gloom(self):
        w = open_world()
        p = w.player
        e = w.spawn_enemy("crawler", 3 * C.TILE, 3 * C.TILE, spawn_time=0.0)
        before = ((e.x - p.x) ** 2 + (e.y - p.y) ** 2) ** 0.5
        for _ in range(60):
            w.step(DT, Controls())
        after = ((e.x - p.x) ** 2 + (e.y - p.y) ** 2) ** 0.5
        self.assertLess(after, before - 40)
        self.assertGreater(w.arena.gloom_count, 0)

    def test_splitter_splits_into_minis(self):
        w = open_world()
        e = w.spawn_enemy("splitter", 200, 200, spawn_time=0.0)
        w.damage_enemy(e, 1000)
        kinds = [x.kind for x in w.enemies if x.alive]
        self.assertEqual(kinds, ["mini", "mini"])

    def test_contact_hurts_once_then_invulnerable(self):
        w = open_world()
        p = w.player
        p.invuln = 0.0
        w.spawn_enemy("crawler", p.x + 5, p.y, spawn_time=0.0)
        w.step(DT, Controls())
        self.assertEqual(p.hp, p.max_hp - 1)
        self.assertGreater(p.invuln, 0.0)
        hp = p.hp
        w.step(DT, Controls())
        self.assertEqual(p.hp, hp)

    def test_player_dies_at_zero(self):
        w = open_world()
        p = w.player
        p.hp = 1
        p.invuln = 0.0
        self.assertTrue(w.hurt_player(p.x, p.y))
        self.assertFalse(p.alive)
        self.assertIn("dead", [ev[0] for ev in w.events])
        self.assertFalse(w.hurt_player(p.x, p.y))

    def test_spitter_shoots_globs_that_hurt(self):
        w = open_world()
        p = w.player
        p.invuln = 0.0
        w.spawn_enemy("spitter", p.x + 200, p.y, spawn_time=0.0)
        hurt = False
        for _ in range(60 * 6):
            w.step(DT, Controls())
            if p.hp < p.max_hp:
                hurt = True
                break
        self.assertTrue(hurt)

    def test_brute_charges(self):
        w = open_world()
        p = w.player
        brute = w.spawn_enemy("brute", p.x + 180, p.y, spawn_time=0.0)
        brute.cooldown = 0.0
        seen = set()
        for _ in range(120):
            w.step(DT, Controls())
            seen.add(brute.state)
        self.assertIn("windup", seen)
        self.assertIn("charge", seen)

class BombAndPickupTests(unittest.TestCase):
    def test_bomb_hits_everything_in_radius(self):
        w = open_world()
        p = w.player
        near = [w.spawn_enemy("crawler", p.x + 150 + dx, p.y, spawn_time=0.0) for dx in (-20, 0, 20)]
        far = w.spawn_enemy("crawler", p.x - 250, p.y, spawn_time=0.0)
        w.step(DT, aim_at(w, p.x + 150, p.y, bomb=True))
        self.assertEqual(p.bombs, C.PLAYER_BOMBS - 1)
        for _ in range(40):
            w.step(DT, aim_at(w, p.x + 150, p.y))
        self.assertTrue(all(not e.alive for e in near))
        self.assertTrue(far.alive)

    def test_no_bomb_without_charges(self):
        w = open_world()
        w.player.bombs = 0
        w.step(DT, aim_at(w, 0, 0, bomb=True))
        self.assertEqual(w.projectiles, [])

    def test_pickups(self):
        w = open_world()
        p = w.player
        p.hp = 2
        w.apply_pickup("heart")
        self.assertEqual(p.hp, 3)
        p.hp = p.max_hp
        w.apply_pickup("heart")
        self.assertEqual(p.hp, p.max_hp)
        w.apply_pickup("triple")
        w.step(DT, aim_at(w, 0, 0, fire=True))
        self.assertEqual(len(w.projectiles), 3)

    def test_walking_over_pickup_collects_it(self):
        from splashback.entities import Pickup
        w = open_world()
        p = w.player
        p.bombs = 0
        w.pickups.append(Pickup("bomb", p.x + 4, p.y))
        w.step(DT, Controls())
        self.assertEqual(p.bombs, 1)
        self.assertEqual(w.pickups, [])

if __name__ == "__main__":
    unittest.main()
