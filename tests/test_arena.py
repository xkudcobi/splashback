import unittest

from splashback import config as C
from splashback.arena import Arena
from splashback.arena_gen import generate_arena

def reachable(arena, start):
    seen = {start}
    stack = [start]
    while stack:
        idx = stack.pop()
        col, row = arena.cell(idx)
        for nc, nr in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)):
            if not arena.is_solid_cell(nc, nr):
                n = arena.index(nc, nr)
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
    return seen

class ArenaPaintTests(unittest.TestCase):
    def setUp(self):
        self.arena = Arena(6, 5)

    def test_rejects_bad_sizes(self):
        with self.assertRaises(ValueError):
            Arena(2, 5)
        with self.assertRaises(ValueError):
            Arena(4, 4, [False] * 3)

    def test_paint_is_clamped_and_counted(self):
        a = self.arena
        self.assertTrue(a.add_paint(0, 10, hue=2))
        self.assertEqual(a.paint[0], C.PAINT_MAX)
        self.assertEqual(a.hue[0], 2)
        self.assertEqual(a.painted_count, 1)
        self.assertFalse(a.add_paint(0, 1, hue=2))   # already full
        a.add_paint(0, -20)
        self.assertEqual(a.paint[0], -C.GLOOM_MAX)
        self.assertEqual((a.painted_count, a.gloom_count), (0, 1))

    def test_gloom_must_be_scrubbed_before_colour_shows(self):
        a = self.arena
        a.add_paint(3, -3)
        a.add_paint(3, 2, hue=1)
        self.assertEqual(a.paint[3], -1)
        self.assertEqual(a.painted_count, 0)
        a.add_paint(3, 2, hue=1)
        self.assertEqual(a.paint[3], 1)
        self.assertEqual(a.painted_count, 1)

    def test_walls_and_out_of_range_are_ignored(self):
        solid = [False] * 30
        solid[4] = True
        a = Arena(6, 5, solid)
        self.assertFalse(a.add_paint(4, 2))
        self.assertFalse(a.add_paint(-1, 2))
        self.assertEqual(a.walkable_count, 29)

    def test_splash_marks_tiles_and_dirty_set(self):
        a = self.arena
        x, y = a.center(a.index(2, 2))
        changed = a.splash(x, y, C.TILE * 1.05, 2, hue=0)
        self.assertEqual(changed, 5)   # centre plus four neighbours
        self.assertEqual(len(a.dirty), 5)
        self.assertAlmostEqual(a.coverage(), 5 / 30)

    def test_tiny_splash_still_marks_the_hit_tile(self):
        a = self.arena
        self.assertEqual(a.splash(10, 10, 1, 1), 1)
        self.assertEqual(a.paint[0], 1)

    def test_tile_lookup_and_bounds(self):
        a = self.arena
        self.assertEqual(a.tile_at(-1, 5), -1)
        self.assertEqual(a.tile_at(C.TILE * 6 + 1, 5), -1)
        self.assertEqual(a.tile_at(C.TILE + 1, C.TILE * 2 + 1), a.index(1, 2))
        self.assertTrue(a.is_solid_cell(-1, 0))
        self.assertTrue(a.is_solid_point(10_000, 10))

    def test_speed_factor_reads_tile(self):
        a = self.arena
        a.add_paint(0, 1)
        a.add_paint(1, -1)
        self.assertEqual(a.speed_factor(5, 5, 2.0, 0.5), 2.0)
        self.assertEqual(a.speed_factor(C.TILE + 5, 5, 2.0, 0.5), 0.5)
        self.assertEqual(a.speed_factor(C.TILE * 2 + 5, 5, 2.0, 0.5), 1.0)

class GeneratorTests(unittest.TestCase):
    def test_same_seed_same_layout(self):
        self.assertEqual(generate_arena(42).solid, generate_arena(42).solid)

    def test_layouts_are_playable(self):
        for seed in range(60):
            with self.subTest(seed=seed):
                a = generate_arena(seed)
                sx, sy = a.spawn_point()
                start = a.tile_at(sx, sy)
                self.assertFalse(a.solid[start])
                # Border is closed.
                for col in range(a.cols):
                    self.assertTrue(a.solid[col])
                    self.assertTrue(a.solid[a.index(col, a.rows - 1)])
                # Every floor tile is reachable from the spawn point.
                floors = {i for i in range(len(a.solid)) if not a.solid[i]}
                self.assertEqual(reachable(a, start), floors)
                self.assertGreater(a.walkable_count, (a.cols - 2) * (a.rows - 2) * 0.6)

    def test_spawn_area_is_clear(self):
        for seed in range(30):
            a = generate_arena(seed)
            sx, sy = a.spawn_point()
            for dx in (-40, 0, 40):
                for dy in (-40, 0, 40):
                    self.assertFalse(a.is_solid_point(sx + dx, sy + dy), (seed, dx, dy))

if __name__ == "__main__":
    unittest.main()
