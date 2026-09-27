import unittest

from splashback import config as C
from splashback.arena import Arena
from splashback.navigation import (INF, ORTHO_COST, FlowField, build_neighbors,
                                   line_of_sight)
from splashback.physics import SpatialHash, move_circle

def arena_from(rows):
    """Build an arena from strings where '#' is a wall."""
    solid = [ch == "#" for row in rows for ch in row]
    return Arena(len(rows[0]), len(rows), solid)

MAZE = [
    "#######",
    "#.....#",
    "#.###.#",
    "#...#.#",
    "#######",
]

class FlowFieldTests(unittest.TestCase):
    def test_distances_follow_walls(self):
        a = arena_from(MAZE)
        flow = FlowField(a)
        target = a.index(1, 3)
        self.assertTrue(flow.update(target))
        self.assertEqual(flow.distance(target), 0)
        self.assertEqual(flow.distance(a.index(3, 3)), 2 * ORTHO_COST)
        # (5,3) must go all the way round the top; the wall blocks every diagonal shortcut.
        self.assertEqual(flow.distance(a.index(5, 3)), 8 * ORTHO_COST)
        self.assertEqual(flow.distance(a.index(5, 2)), 7 * ORTHO_COST)
        self.assertEqual(flow.distance(a.index(2, 2)), INF)   # wall
        self.assertFalse(flow.update(target))                # unchanged target is a no-op

    def test_next_tile_walks_downhill_to_target(self):
        a = arena_from(MAZE)
        flow = FlowField(a)
        target = a.index(1, 3)
        flow.update(target)
        idx, steps = a.index(5, 3), 0
        while idx != target:
            nxt = flow.next_tile[idx]
            self.assertLess(flow.dist[nxt], flow.dist[idx])
            idx, steps = nxt, steps + 1
            self.assertLess(steps, 20)

    def test_no_corner_cutting(self):
        a = arena_from(["#####", "#.#.#", "##..#", "#####"])
        neighbors = dict(build_neighbors(a)[a.index(3, 2)])
        self.assertNotIn(a.index(2, 1), neighbors)   # would slip between two walls
        self.assertIn(a.index(2, 2), neighbors)

    def test_unreachable_tiles_and_steer(self):
        a = arena_from(["#######", "#..#..#", "#######"])
        flow = FlowField(a)
        flow.update(a.index(1, 1))
        self.assertEqual(flow.distance(a.index(5, 1)), INF)
        self.assertEqual(flow.steer(*a.center(a.index(5, 1))), (0.0, 0.0))
        sx, sy = flow.steer(*a.center(a.index(2, 1)))
        self.assertAlmostEqual(sx, -1.0)
        self.assertAlmostEqual(sy, 0.0)
        self.assertEqual(flow.tiles_farther_than(10), [a.index(2, 1)])

    def test_wall_target_clears_field(self):
        a = arena_from(MAZE)
        flow = FlowField(a)
        flow.update(a.index(0, 0))
        self.assertTrue(all(n == -1 for n in flow.next_tile))

class SightTests(unittest.TestCase):
    def test_line_of_sight(self):
        a = arena_from(MAZE)
        t = C.TILE
        self.assertTrue(line_of_sight(a, 1.5 * t, 1.5 * t, 5.5 * t, 1.5 * t))
        self.assertFalse(line_of_sight(a, 1.5 * t, 1.5 * t, 3.5 * t, 3.5 * t))
        self.assertTrue(line_of_sight(a, 1.5 * t, 3.5 * t, 1.5 * t, 1.5 * t))
        self.assertTrue(line_of_sight(a, 2.0 * t, 1.5 * t, 2.0 * t, 1.5 * t))

class PhysicsTests(unittest.TestCase):
    def test_circle_stops_at_wall_and_slides(self):
        a = arena_from(MAZE)
        t = C.TILE
        x, y, blocked = move_circle(a, 1.5 * t, 1.5 * t, 10, -40, 0)
        self.assertTrue(blocked)
        self.assertAlmostEqual(x, t + 10, places=5)
        # Pushing diagonally into the top wall still slides sideways.
        x, y, blocked = move_circle(a, 3.5 * t, 1.5 * t, 10, 8, -30)
        self.assertTrue(blocked)
        self.assertAlmostEqual(x, 3.5 * t + 8)
        self.assertAlmostEqual(y, t + 10, places=5)

    def test_free_move_is_not_blocked(self):
        a = arena_from(MAZE)
        x, y, blocked = move_circle(a, 48, 48, 8, 5, 0)
        self.assertFalse(blocked)
        self.assertEqual((x, y), (53, 48))

    def test_spatial_hash(self):
        h = SpatialHash(640, 480, 64)
        out = []
        h.insert("a", 10, 10)
        h.insert("b", 300, 300)
        h.insert("c", 5000, -40)   # clamped into an edge cell
        self.assertEqual(h.query(20, 20, 30, out), ["a"])
        self.assertIn("b", h.query(320, 320, 50, out))
        self.assertNotIn("a", out)
        self.assertEqual(h.query(630, 5, 10, out), ["c"])
        h.clear()
        self.assertEqual(h.query(10, 10, 1000, out), [])

if __name__ == "__main__":
    unittest.main()
