"""Seeded arena layouts: symmetric obstacle patterns that are always fully connected."""

import random

from . import config as C
from .arena import Arena

MIN_OPEN = 0.62
MAX_OPEN = 0.93
SPAWN_CLEARANCE = 3

def _blank(cols, rows):
    solid = [False] * (cols * rows)
    for col in range(cols):
        solid[col] = True
        solid[(rows - 1) * cols + col] = True
    for row in range(rows):
        solid[row * cols] = True
        solid[row * cols + cols - 1] = True
    return solid

def _stamp(solid, cols, rows, col, row, w, h, mirror_x, mirror_y):
    """Fill a rectangle and its mirror images."""
    for r in range(row, row + h):
        for c in range(col, col + w):
            targets = [(c, r)]
            if mirror_x:
                targets.append((cols - 1 - c, r))
            if mirror_y:
                targets.append((c, rows - 1 - r))
            if mirror_x and mirror_y:
                targets.append((cols - 1 - c, rows - 1 - r))
            for tc, tr in targets:
                if 0 <= tc < cols and 0 <= tr < rows:
                    solid[tr * cols + tc] = True

def _style_pillars(rng, solid, cols, rows):
    step = rng.choice((4, 5))
    size = rng.choice((1, 2))
    skip = rng.random() * 0.35
    for row in range(3, rows // 2 + 1, step):
        for col in range(3, cols // 2 + 1, step):
            if rng.random() > skip:
                _stamp(solid, cols, rows, col, row, size, size, True, True)

def _style_blocks(rng, solid, cols, rows):
    for _ in range(rng.randint(3, 6)):
        w = rng.randint(1, 4)
        h = rng.randint(1, 3)
        col = rng.randint(2, max(2, cols // 2 - w))
        row = rng.randint(2, max(2, rows // 2 - h))
        _stamp(solid, cols, rows, col, row, w, h, True, True)

def _style_walls(rng, solid, cols, rows):
    for _ in range(rng.randint(2, 4)):
        length = rng.randint(3, 7)
        col = rng.randint(2, cols // 2 - 1)
        row = rng.randint(2, rows // 2 - 1)
        if rng.random() < 0.5:
            _stamp(solid, cols, rows, col, row, length, 1, True, rng.random() < 0.7)
        else:
            _stamp(solid, cols, rows, col, row, 1, min(length, rows // 2 - 2), True, True)

def _style_open(rng, solid, cols, rows):
    # A few corner bumpers only; a breather layout.
    for _ in range(rng.randint(1, 3)):
        col = rng.randint(3, cols // 2 - 3)
        row = rng.randint(3, rows // 2 - 2)
        _stamp(solid, cols, rows, col, row, 2, 1, True, True)

STYLES = (_style_pillars, _style_blocks, _style_walls, _style_open)

def _clear_zone(solid, cols, rows, radius):
    mid_c, mid_r = cols // 2, rows // 2
    for r in range(mid_r - radius, mid_r + radius):
        for c in range(mid_c - radius, mid_c + radius):
            if 0 < c < cols - 1 and 0 < r < rows - 1:
                solid[r * cols + c] = False

def _seal_unreachable(solid, cols, rows):
    """Turn floor pockets that cannot be reached from the centre into walls."""
    start = (rows // 2) * cols + cols // 2
    seen = [False] * len(solid)
    seen[start] = True
    stack = [start]
    while stack:
        idx = stack.pop()
        col, row = idx % cols, idx // cols
        for nc, nr in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)):
            if 0 <= nc < cols and 0 <= nr < rows:
                n = nr * cols + nc
                if not seen[n] and not solid[n]:
                    seen[n] = True
                    stack.append(n)
    for idx in range(len(solid)):
        if not solid[idx] and not seen[idx]:
            solid[idx] = True

def generate_arena(seed, cols=C.COLS, rows=C.ROWS):
    """Build a playable arena for a seed. The same seed always gives the same layout."""
    rng = random.Random(seed)
    inner = (cols - 2) * (rows - 2)
    for _ in range(16):
        solid = _blank(cols, rows)
        rng.choice(STYLES)(rng, solid, cols, rows)
        _clear_zone(solid, cols, rows, SPAWN_CLEARANCE)
        _seal_unreachable(solid, cols, rows)
        open_tiles = len(solid) - sum(solid)
        if MIN_OPEN <= open_tiles / inner <= MAX_OPEN:
            return Arena(cols, rows, solid, seed)
    return Arena(cols, rows, _blank(cols, rows), seed)
