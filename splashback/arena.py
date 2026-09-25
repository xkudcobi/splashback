"""The tile grid: which tiles are walls and how much paint or gloom each floor tile holds."""

import math

from . import config as C

class Arena:
    """A fixed-size grid of tiles.

    ``paint`` holds one integer per tile: positive values are the player's paint,
    negative values are grey gloom, zero is bare floor. Tiles that change are
    collected in ``dirty`` so a renderer only needs to repaint those.
    """

    def __init__(self, cols, rows, solid=None, seed=0):
        if cols < 3 or rows < 3:
            raise ValueError("arena must be at least 3x3")
        count = cols * rows
        if solid is None:
            solid = [False] * count
        elif len(solid) != count:
            raise ValueError("solid map has the wrong size")
        self.cols = cols
        self.rows = rows
        self.seed = seed
        self.solid = [bool(s) for s in solid]
        self.paint = [0] * count
        self.hue = [0] * count
        self.dirty = set()
        self.walkable_count = count - sum(self.solid)
        self.painted_count = 0
        self.gloom_count = 0

    # --- geometry -------------------------------------------------------------

    def index(self, col, row):
        return row * self.cols + col

    def cell(self, index):
        return index % self.cols, index // self.cols

    def tile_at(self, x, y):
        """Index of the tile under a world point, or -1 outside the grid."""
        col = int(x // C.TILE)
        row = int(y // C.TILE)
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return row * self.cols + col
        return -1

    def center(self, index):
        col, row = index % self.cols, index // self.cols
        return (col + 0.5) * C.TILE, (row + 0.5) * C.TILE

    def is_solid_cell(self, col, row):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.solid[row * self.cols + col]
        return True

    def is_solid_point(self, x, y):
        return self.is_solid_cell(int(x // C.TILE), int(y // C.TILE))

    def spawn_point(self):
        """The middle of the arena, which the generator always keeps open."""
        return self.cols * C.TILE / 2.0, self.rows * C.TILE / 2.0

    # --- paint ------------------------------------------------------------------

    def add_paint(self, index, amount, hue=0):
        """Add paint (amount > 0) or gloom (amount < 0) to one tile.

        Returns True when the tile's value actually changed.
        """
        if index < 0 or self.solid[index] or amount == 0:
            return False
        old = self.paint[index]
        new = max(-C.GLOOM_MAX, min(C.PAINT_MAX, old + amount))
        if amount > 0 and new > 0 and self.hue[index] != hue:
            self.hue[index] = hue
            self.dirty.add(index)
        if new == old:
            return False
        self.paint[index] = new
        self.painted_count += (new > 0) - (old > 0)
        self.gloom_count += (new < 0) - (old < 0)
        self.dirty.add(index)
        return True

    def splash(self, x, y, radius, amount, hue=0):
        """Apply paint or gloom to every floor tile whose centre lies within radius.

        The tile directly under the point is always affected, so tiny splashes
        still leave a mark. Returns the number of tiles that changed.
        """
        ts = C.TILE
        changed = 0
        hit = self.tile_at(x, y)
        if hit >= 0 and self.add_paint(hit, amount, hue):
            changed += 1
        c0 = max(0, int((x - radius) // ts))
        c1 = min(self.cols - 1, int((x + radius) // ts))
        r0 = max(0, int((y - radius) // ts))
        r1 = min(self.rows - 1, int((y + radius) // ts))
        r2 = radius * radius
        for row in range(r0, r1 + 1):
            cy = (row + 0.5) * ts - y
            for col in range(c0, c1 + 1):
                cx = (col + 0.5) * ts - x
                if cx * cx + cy * cy > r2:
                    continue
                idx = row * self.cols + col
                if idx != hit and self.add_paint(idx, amount, hue):
                    changed += 1
        return changed

    def coverage(self):
        """Share of walkable floor currently holding paint (0..1)."""
        if self.walkable_count == 0:
            return 0.0
        return self.painted_count / self.walkable_count

    def gloom_share(self):
        if self.walkable_count == 0:
            return 0.0
        return self.gloom_count / self.walkable_count

    def speed_factor(self, x, y, on_paint, on_gloom):
        """Pick a speed multiplier depending on what the point is standing on."""
        idx = self.tile_at(x, y)
        if idx < 0:
            return 1.0
        value = self.paint[idx]
        if value > 0:
            return on_paint
        if value < 0:
            return on_gloom
        return 1.0

    def distance_to_center(self, index):
        cx, cy = self.center(index)
        sx, sy = self.spawn_point()
        return math.hypot(cx - sx, cy - sy)
