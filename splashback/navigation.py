"""Pathfinding and sight lines on the tile grid.

Every enemy needs a way to reach the player. Instead of running a search per
enemy, one Dijkstra flow field is built outward from the player's tile; each
enemy then just steps to its tile's best neighbour. The field is rebuilt only
when the player moves onto a different tile.
"""

import heapq
import math

from . import config as C

INF = 1 << 30
ORTHO_COST = 10
DIAG_COST = 14

def build_neighbors(arena):
    """Precompute walkable neighbours per tile. Diagonals never cut wall corners."""
    cols, rows = arena.cols, arena.rows
    solid = arena.solid
    table = []
    for idx in range(cols * rows):
        entries = []
        if not solid[idx]:
            col, row = idx % cols, idx // cols
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if dc == 0 and dr == 0:
                        continue
                    if arena.is_solid_cell(col + dc, row + dr):
                        continue
                    if dc and dr and (arena.is_solid_cell(col + dc, row)
                                      or arena.is_solid_cell(col, row + dr)):
                        continue
                    cost = DIAG_COST if dc and dr else ORTHO_COST
                    entries.append(((row + dr) * cols + col + dc, cost))
        table.append(tuple(entries))
    return table

class FlowField:
    def __init__(self, arena):
        self.arena = arena
        count = arena.cols * arena.rows
        self.neighbors = build_neighbors(arena)
        self.dist = [INF] * count
        self.next_tile = [-1] * count
        self._blank_dist = [INF] * count
        self.target = -1

    def update(self, target):
        """Rebuild the field towards a tile. Returns False if nothing had to change."""
        if target == self.target:
            return False
        self.target = target
        dist = self.dist
        dist[:] = self._blank_dist
        next_tile = self.next_tile
        if target < 0 or self.arena.solid[target]:
            for i in range(len(next_tile)):
                next_tile[i] = -1
            return True
        neighbors = self.neighbors
        dist[target] = 0
        heap = [(0, target)]
        pop, push = heapq.heappop, heapq.heappush
        while heap:
            d, idx = pop(heap)
            if d > dist[idx]:
                continue
            for n, cost in neighbors[idx]:
                nd = d + cost
                if nd < dist[n]:
                    dist[n] = nd
                    push(heap, (nd, n))
        for idx in range(len(dist)):
            best = -1
            best_d = dist[idx]
            if best_d < INF:
                for n, _ in neighbors[idx]:
                    if dist[n] < best_d:
                        best_d = dist[n]
                        best = n
            next_tile[idx] = best
        return True

    def distance(self, index):
        return self.dist[index] if index >= 0 else INF

    def steer(self, x, y):
        """Unit vector from a point towards the next tile on the way to the target.

        Returns (0, 0) when the point is already on the target tile or cannot reach it.
        """
        idx = self.arena.tile_at(x, y)
        if idx < 0:
            return 0.0, 0.0
        nxt = self.next_tile[idx]
        if nxt < 0:
            return 0.0, 0.0
        tx, ty = self.arena.center(nxt)
        dx, dy = tx - x, ty - y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return 0.0, 0.0
        return dx / length, dy / length

    def tiles_farther_than(self, min_cost):
        """Reachable tiles at least ``min_cost`` away from the target (for spawning)."""
        dist = self.dist
        return [i for i in range(len(dist)) if min_cost <= dist[i] < INF]

def line_of_sight(arena, x0, y0, x1, y1):
    """True when the straight segment between two points crosses no wall tile.

    Walks the grid cell by cell (a voxel traversal), so the cost grows with the
    number of tiles crossed, not with the distance in pixels.
    """
    ts = C.TILE
    col, row = int(x0 // ts), int(y0 // ts)
    end_col, end_row = int(x1 // ts), int(y1 // ts)
    dx, dy = x1 - x0, y1 - y0
    step_c = 1 if dx > 0 else -1
    step_r = 1 if dy > 0 else -1
    if dx != 0:
        boundary = (col + 1) * ts if dx > 0 else col * ts
        t_max_x = (boundary - x0) / dx
        t_delta_x = ts / abs(dx)
    else:
        t_max_x = t_delta_x = math.inf
    if dy != 0:
        boundary = (row + 1) * ts if dy > 0 else row * ts
        t_max_y = (boundary - y0) / dy
        t_delta_y = ts / abs(dy)
    else:
        t_max_y = t_delta_y = math.inf
    for _ in range(arena.cols + arena.rows + 2):
        if arena.is_solid_cell(col, row):
            return False
        if col == end_col and row == end_row:
            return True
        if t_max_x < t_max_y:
            t_max_x += t_delta_x
            col += step_c
        else:
            t_max_y += t_delta_y
            row += step_r
    return True
