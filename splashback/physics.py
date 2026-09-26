"""Circle-versus-tile movement and a reusable spatial hash for quick neighbour lookups."""

import math

from . import config as C

def _push_out(arena, x, y, r):
    ts = C.TILE
    c0, c1 = int((x - r) // ts), int((x + r) // ts)
    r0, r1 = int((y - r) // ts), int((y + r) // ts)
    for row in range(r0, r1 + 1):
        for col in range(c0, c1 + 1):
            if not arena.is_solid_cell(col, row):
                continue
            left, top = col * ts, row * ts
            nx = min(max(x, left), left + ts)
            ny = min(max(y, top), top + ts)
            dx, dy = x - nx, y - ny
            d2 = dx * dx + dy * dy
            if d2 >= r * r:
                continue
            if d2 > 1e-9:
                d = math.sqrt(d2)
                push = (r - d) / d
                x += dx * push
                y += dy * push
            else:
                # Centre is inside the tile: leave along the shallowest side.
                exits = ((x - left + r, -1, 0), (left + ts - x + r, 1, 0),
                         (y - top + r, 0, -1), (top + ts - y + r, 0, 1))
                depth, ex, ey = min(exits)
                x += ex * depth
                y += ey * depth
    return x, y

def move_circle(arena, x, y, r, dx, dy):
    """Move a circle by (dx, dy), sliding along walls.

    Returns (new_x, new_y, blocked) where blocked tells whether a wall got in the way.
    Each axis is resolved separately, which keeps sliding along walls smooth.
    Moves may be longer than a tile; they are stepped internally.
    """
    tx, ty = x + dx, y + dy
    # Long moves are split into steps shorter than half the radius so nothing tunnels.
    steps = int(max(abs(dx), abs(dy)) / (r * 0.5)) + 1
    sx, sy = dx / steps, dy / steps
    for _ in range(steps):
        x, y = _push_out(arena, x + sx, y, r)
        x, y = _push_out(arena, x, y + sy, r)
    blocked = abs(x - tx) + abs(y - ty) > 0.01
    return x, y, blocked

class SpatialHash:
    """Buckets objects by the cell their centre falls in.

    The bucket lists are allocated once and cleared in place every tick.
    ``query`` widens the search by ``margin`` so objects with a radius are not missed.
    """

    def __init__(self, width, height, cell=64):
        self.cell = cell
        self.cols = max(1, int(math.ceil(width / cell)))
        self.rows = max(1, int(math.ceil(height / cell)))
        self.buckets = [[] for _ in range(self.cols * self.rows)]
        self._used = []

    def _bucket_index(self, x, y):
        col = min(self.cols - 1, max(0, int(x // self.cell)))
        row = min(self.rows - 1, max(0, int(y // self.cell)))
        return row * self.cols + col

    def clear(self):
        buckets = self.buckets
        for idx in self._used:
            buckets[idx].clear()
        self._used.clear()

    def insert(self, item, x, y):
        idx = self._bucket_index(x, y)
        bucket = self.buckets[idx]
        if not bucket:
            self._used.append(idx)
        bucket.append(item)

    def query(self, x, y, radius, out):
        """Fill ``out`` (cleared first) with items whose cell overlaps the circle."""
        out.clear()
        cell = self.cell
        c0 = max(0, int((x - radius) // cell))
        c1 = min(self.cols - 1, int((x + radius) // cell))
        r0 = max(0, int((y - radius) // cell))
        r1 = min(self.rows - 1, int((y + radius) // cell))
        buckets = self.buckets
        for row in range(r0, r1 + 1):
            base = row * self.cols
            for col in range(c0, c1 + 1):
                bucket = buckets[base + col]
                if bucket:
                    out.extend(bucket)
        return out
