"""Drawing the game on a Tk canvas.

Canvas items are expensive to create and cheap to move, so nothing here is
created per frame: floor tiles are made once per arena and only recoloured when
their paint changes, and moving things come from pools of items that are
repositioned, recoloured only on change, and hidden when unused.
"""

import math
import random
import tkinter.font as tkfont

from . import config as C
from .game import GAMEOVER, PAUSED, PERK, PLAYING, SCORES, SETTINGS, TITLE

W, H = C.WORLD_W, C.WORLD_H
INK = "#2b2d3a"
PANEL = "#23253a"
PAPER = "#fdfaf3"
MUTED = "#8d8fa3"
WALL_TOP = "#4a4f73"
WALL_FACE = "#353955"
GROUT = "#d6cebd"
FLOOR = (234, 228, 214)
GLOOM = (92, 94, 110)
HEART = "#ff5470"
PAINT_BLEND = (0.0, 0.38, 0.62, 0.82, 1.0)
GLOOM_BLEND = (0.0, 0.4, 0.7, 1.0)
ENEMY_COLORS = {
    "crawler": "#5d6072", "mini": "#72758a", "spitter": "#6b5f86",
    "splitter": "#4f6e74", "brute": "#3d3e4c",
}
PICKUP_STYLE = {
    "heart": ("#ff5470", "♥"), "bomb": ("#2b2d3a", "B"),
    "rapid": ("#1fa5ff", "»"), "triple": ("#ffae00", "x3"),
}
MAX_PARTICLES = 260
MAX_POPUPS = 14
MAX_RINGS = 6

def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)

def _mix(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))

def _darker(rgb, k=0.55):
    return _hex(tuple(v * k for v in rgb))

def pick_fonts(root):
    families = set(tkfont.families(root))
    body = next((f for f in ("Segoe UI", "Helvetica Neue", "Ubuntu", "DejaVu Sans", "Arial")
                 if f in families), "TkDefaultFont")
    heavy = next((f for f in ("Segoe UI Black", "Arial Black", "Impact") if f in families), body)
    return {
        "title": (heavy, 52, "bold"),
        "banner": (heavy, 34, "bold"),
        "big": (body, 22, "bold"),
        "mid": (body, 15, "bold"),
        "body": (body, 12),
        "small": (body, 10),
        "hud": (body, 12, "bold"),
        "heart": (body, 15, "bold"),
    }

class ShapePool:
    """Reusable canvas items of one kind (oval, line, rectangle or text)."""

    def __init__(self, canvas, kind, below, **options):
        self.canvas = canvas
        self.kind = kind
        self.below = below
        self.options = options
        self.items = []
        self.fills = []
        self.outlines = []
        self.visible = []
        self.used = 0

    def begin(self):
        self.used = 0

    def _next(self):
        i = self.used
        self.used += 1
        if i == len(self.items):
            c = self.canvas
            if self.kind == "oval":
                item = c.create_oval(0, 0, 0, 0, **self.options)
            elif self.kind == "line":
                item = c.create_line(0, 0, 0, 0, **self.options)
            elif self.kind == "rect":
                item = c.create_rectangle(0, 0, 0, 0, **self.options)
            else:
                item = c.create_text(0, 0, **self.options)
            c.tag_lower(item, self.below)
            self.items.append(item)
            self.fills.append(None)
            self.outlines.append(None)
            self.visible.append(True)
        elif not self.visible[i]:
            self.canvas.itemconfigure(self.items[i], state="normal")
            self.visible[i] = True
        return i

    def shape(self, x0, y0, x1, y1, fill, outline=None):
        i = self._next()
        item = self.items[i]
        self.canvas.coords(item, x0, y0, x1, y1)
        if self.fills[i] != fill:
            self.canvas.itemconfigure(item, fill=fill)
            self.fills[i] = fill
        if outline is not None and self.outlines[i] != outline:
            self.canvas.itemconfigure(item, outline=outline)
            self.outlines[i] = outline
        return item

    def circle(self, x, y, r, fill, outline=None):
        return self.shape(x - r, y - r, x + r, y + r, fill, outline)

    def text(self, x, y, text, fill):
        i = self._next()
        item = self.items[i]
        self.canvas.coords(item, x, y)
        if self.outlines[i] != text:
            self.canvas.itemconfigure(item, text=text)
            self.outlines[i] = text
        if self.fills[i] != fill:
            self.canvas.itemconfigure(item, fill=fill)
            self.fills[i] = fill
        return item

    def finish(self):
        for i in range(self.used, len(self.items)):
            if self.visible[i]:
                self.canvas.itemconfigure(self.items[i], state="hidden")
                self.visible[i] = False

class Particles:
    """Cosmetic droplets kept in flat, preallocated arrays."""

    def __init__(self, capacity=MAX_PARTICLES):
        self.capacity = capacity
        self.x = [0.0] * capacity
        self.y = [0.0] * capacity
        self.vx = [0.0] * capacity
        self.vy = [0.0] * capacity
        self.life = [0.0] * capacity
        self.max_life = [1.0] * capacity
        self.size = [2.0] * capacity
        self.color = ["#000000"] * capacity
        self.cursor = 0

    def emit(self, x, y, count, speed, color, size, life, rng):
        for _ in range(count):
            i = self.cursor
            self.cursor = (i + 1) % self.capacity
            angle = rng.random() * math.tau
            s = speed * (0.35 + rng.random() * 0.65)
            self.x[i], self.y[i] = x, y
            self.vx[i], self.vy[i] = math.cos(angle) * s, math.sin(angle) * s
            self.life[i] = self.max_life[i] = life * (0.6 + rng.random() * 0.4)
            self.size[i] = size * (0.6 + rng.random() * 0.6)
            self.color[i] = color

    def update(self, dt):
        drag = max(0.0, 1.0 - 5.0 * dt)
        life = self.life
        for i in range(self.capacity):
            if life[i] > 0.0:
                life[i] -= dt
                self.x[i] += self.vx[i] * dt
                self.y[i] += self.vy[i] * dt
                self.vx[i] *= drag
                self.vy[i] *= drag

    def clear(self):
        for i in range(self.capacity):
            self.life[i] = 0.0

class Renderer:
    def __init__(self, canvas, fonts):
        self.c = canvas
        self.fonts = fonts
        self.rng = random.Random(7)
        self.buttons = []
        self._arena = None
        self._floor_items = {}
        self._floor_colors = {}
        self._color_cache = {}
        self._shake = 0.0
        self._offset = (0.0, 0.0)
        self._overlay_sig = None
        self._pulse_item = None
        self._pulse_step = -1
        self._hud_cache = {}
        self.particles = Particles()
        self.popups = []      # [x, y, text, color, life]
        self.rings = []       # [x, y, radius, life, color]

        c = canvas
        markers = {}
        for name in ("pickups", "enemies", "player", "shots", "particles", "hud", "ui"):
            markers[name] = c.create_line(0, 0, 0, 0, state="hidden")
        self.pickup_bodies = ShapePool(c, "oval", markers["pickups"], width=3)
        self.pickup_marks = ShapePool(c, "text", markers["pickups"], font=fonts["hud"])
        self.spawn_rings = ShapePool(c, "oval", markers["enemies"], width=2, fill="", dash=(4, 3))
        self.enemy_bodies = ShapePool(c, "oval", markers["enemies"], width=2, outline=INK)
        self.enemy_eyes = ShapePool(c, "oval", markers["enemies"], outline="")
        self.player_parts = ShapePool(c, "oval", markers["player"], width=3)
        self.player_nozzle = ShapePool(c, "line", markers["player"], width=7, capstyle="round")
        self.shots = ShapePool(c, "oval", markers["shots"], width=2)
        self.particle_dots = ShapePool(c, "oval", markers["particles"], outline="")
        self.blast_rings = ShapePool(c, "oval", markers["particles"], width=4, fill="")
        self.popup_texts = ShapePool(c, "text", markers["particles"], font=fonts["mid"])
        self.pools = (self.pickup_bodies, self.pickup_marks, self.spawn_rings, self.enemy_bodies,
                      self.enemy_eyes, self.player_parts, self.player_nozzle, self.shots,
                      self.particle_dots, self.blast_rings, self.popup_texts)
        self._ui_marker = markers["ui"]
        self._build_hud(markers["hud"])
        self._build_lang_toggle()

    # --- colours ---------------------------------------------------------------------

    def tile_color(self, value, hue):
        key = (value, hue)
        color = self._color_cache.get(key)
        if color is None:
            if value > 0:
                rgb = _mix(FLOOR, C.HUES[hue % len(C.HUES)], PAINT_BLEND[min(value, C.PAINT_MAX)])
            elif value < 0:
                rgb = _mix(FLOOR, GLOOM, GLOOM_BLEND[min(-value, C.GLOOM_MAX)])
            else:
                rgb = FLOOR
            color = self._color_cache[key] = _hex(rgb)
        return color

    # --- arena -------------------------------------------------------------------------

    def _build_arena(self, arena):
        c = self.c
        c.delete("static")
        self._floor_items.clear()
        self._floor_colors.clear()
        ts = C.TILE
        ox, oy = self._offset
        c.create_rectangle(0, 0, W, H, fill=GROUT, outline="", tags=("static",))
        for idx in range(arena.cols * arena.rows):
            col, row = arena.cell(idx)
            x, y = col * ts + ox, row * ts + oy
            if arena.solid[idx]:
                c.create_rectangle(x, y, x + ts, y + ts, fill=WALL_TOP, outline="", tags=("static",))
                if not arena.is_solid_cell(col, row + 1):
                    c.create_rectangle(x, y + ts - 9, x + ts, y + ts, fill=WALL_FACE,
                                       outline="", tags=("static",))
            else:
                color = self.tile_color(arena.paint[idx], arena.hue[idx])
                self._floor_items[idx] = c.create_rectangle(
                    x + 1, y + 1, x + ts - 1, y + ts - 1, fill=color, outline="", tags=("static",))
                self._floor_colors[idx] = color
        c.tag_lower("static")
        arena.dirty.clear()
        self._arena = arena
        self.particles.clear()
        self.popups.clear()
        self.rings.clear()

    def _sync_floor(self, arena):
        if not arena.dirty:
            return
        items, colors = self._floor_items, self._floor_colors
        for idx in arena.dirty:
            item = items.get(idx)
            if item is None:
                continue
            color = self.tile_color(arena.paint[idx], arena.hue[idx])
            if colors[idx] != color:
                self.c.itemconfigure(item, fill=color)
                colors[idx] = color
        arena.dirty.clear()

    # --- effects ------------------------------------------------------------------------

    def _consume_fx(self, game, world):
        hue = C.HUES[world.hue % len(C.HUES)]
        paint, dark = _hex(hue), _darker(hue, 0.7)
        p = self.particles
        rng = self.rng
        shake_on = game.settings.shake
        for ev in game.fx:
            kind = ev[0]
            if kind == "splat":
                p.emit(ev[1], ev[2], 4, 120.0, paint, 3.0, 0.35, rng)
            elif kind == "gloom":
                p.emit(ev[1], ev[2], 4, 90.0, "#6d6f80", 3.0, 0.4, rng)
            elif kind == "hit":
                p.emit(ev[1], ev[2], 3, 140.0, "#ffffff", 2.0, 0.2, rng)
            elif kind == "kill":
                big = ev[3] == "brute"
                p.emit(ev[1], ev[2], 18 if big else 10, 220.0, paint, 4.0, 0.55, rng)
                p.emit(ev[1], ev[2], 6, 160.0, dark, 3.0, 0.45, rng)
                if big and shake_on:
                    self._shake = max(self._shake, 6.0)
            elif kind == "points":
                self._popup(ev[1], ev[2] - 14, "+%d" % ev[3], INK)
            elif kind == "hurt":
                p.emit(ev[1], ev[2], 14, 200.0, HEART, 3.5, 0.5, rng)
                if shake_on:
                    self._shake = max(self._shake, 8.0)
            elif kind == "dead":
                p.emit(ev[1], ev[2], 40, 260.0, "#6d6f80", 4.5, 0.9, rng)
            elif kind == "bomb":
                p.emit(ev[1], ev[2], 36, 320.0, paint, 5.0, 0.6, rng)
                if len(self.rings) < MAX_RINGS:
                    self.rings.append([ev[1], ev[2], 10.0, 0.35, paint])
                if shake_on:
                    self._shake = max(self._shake, 9.0)
            elif kind == "pickup":
                color = PICKUP_STYLE[ev[3]][0]
                self._popup(ev[1], ev[2] - 16, game.text("pickup_" + ev[3]), color)
                p.emit(ev[1], ev[2], 10, 150.0, color, 3.0, 0.4, rng)
            elif kind == "thud" and shake_on:
                self._shake = max(self._shake, 4.0)
        game.fx.clear()

    def _popup(self, x, y, text, color):
        if len(self.popups) >= MAX_POPUPS:
            self.popups.pop(0)
        self.popups.append([x, y, text, color, 0.9])

    # --- frame -------------------------------------------------------------------------

    def draw(self, game, frame_dt):
        world = game.display_world
        if world.arena is not self._arena:
            self._build_arena(world.arena)
        self._sync_floor(world.arena)
        self._consume_fx(game, world)
        self.particles.update(frame_dt)

        self._shake = max(0.0, self._shake - frame_dt * 30.0)
        if self._shake > 0.0 and game.state == PLAYING:
            ox = self.rng.uniform(-self._shake, self._shake)
            oy = self.rng.uniform(-self._shake, self._shake)
        else:
            ox = oy = 0.0
        if (ox, oy) != self._offset:
            self.c.move("static", ox - self._offset[0], oy - self._offset[1])
            self._offset = (ox, oy)

        for pool in self.pools:
            pool.begin()
        self._draw_world(game, world, ox, oy, frame_dt)
        for pool in self.pools:
            pool.finish()
        self._draw_hud(game)
        self._draw_overlay(game)
        self._draw_lang_toggle(game.lang)

    def _draw_world(self, game, world, ox, oy, frame_dt):
        t = game.clock
        hue = C.HUES[world.hue % len(C.HUES)]
        paint_hex, paint_dark = _hex(hue), _darker(hue)

        for pk in world.pickups:
            if pk.life < 3.0 and int(pk.life * 8) % 2:
                continue
            color, mark = PICKUP_STYLE[pk.kind]
            bob = math.sin(t * 5.0 + pk.x) * 2.0
            self.pickup_bodies.circle(pk.x + ox, pk.y + oy + bob, 11, PAPER, color)
            self.pickup_marks.text(pk.x + ox, pk.y + oy + bob, mark, color)

        for e in world.enemies:
            if not e.alive:
                continue
            x, y = e.x + ox, e.y + oy
            r = e.radius
            if e.spawn_timer > 0.0:
                ring = r + e.spawn_timer * 34.0
                self.spawn_rings.circle(x, y, ring, "", "#5d6072")
                self.enemy_bodies.circle(x, y, r * max(0.15, 1.0 - e.spawn_timer), "#9a9cae")
                continue
            if e.state == "windup":
                x += math.sin(t * 60.0) * 2.5
            squash = math.sin(t * 9.0 + e.x * 0.05) * 1.3
            body = "#ffffff" if e.hit_flash > 0.0 else ENEMY_COLORS[e.kind]
            self.enemy_bodies.shape(x - r - squash, y - r + squash, x + r + squash, y + r - squash, body)
            lx, ly = e.look_x, e.look_y
            px, py = -ly, lx
            eye = max(2.0, r * 0.3)
            pupil = max(1.2, r * 0.15)
            for side in (-1.0, 1.0):
                ex = x + lx * r * 0.35 + px * r * 0.38 * side
                ey = y + ly * r * 0.35 + py * r * 0.38 * side - 1.0
                self.enemy_eyes.circle(ex, ey, eye, "#ffffff")
                self.enemy_eyes.circle(ex + lx * eye * 0.45, ey + ly * eye * 0.45, pupil, INK)

        p = world.player
        if p.alive and not (p.invuln > 0.0 and int(p.invuln * 12) % 2):
            x, y = p.x + ox, p.y + oy
            r = p.radius
            if p.rapid_timer > 0.0 or p.triple_timer > 0.0:
                glow = r + 6 + math.sin(t * 12.0) * 2.0
                self.player_parts.circle(x, y, glow, "", paint_hex)
            self.player_nozzle.shape(x, y, x + p.face_x * (r + 8), y + p.face_y * (r + 8), INK)
            self.player_parts.circle(x, y, r, paint_hex, INK)
            self.player_parts.circle(x - r * 0.35, y - r * 0.4, r * 0.28, "#ffffff", "")

        for pr in world.projectiles:
            x, y = pr.x + ox, pr.y + oy
            if pr.kind == "paint":
                self.shots.circle(x, y, pr.radius, paint_hex, paint_dark)
            elif pr.kind == "glob":
                self.shots.circle(x, y, pr.radius, "#4a4c5c", "#2e303c")
            else:
                wobble = 8 + math.sin(t * 20.0) * 1.5
                self.shots.circle(x, y, wobble, paint_hex, INK)

        parts = self.particles
        for i in range(parts.capacity):
            life = parts.life[i]
            if life > 0.0:
                s = parts.size[i] * (life / parts.max_life[i])
                self.particle_dots.circle(parts.x[i] + ox, parts.y[i] + oy, s, parts.color[i])

        for ring in self.rings:
            ring[3] -= frame_dt
            ring[2] += frame_dt * 260.0
            if ring[3] > 0.0:
                self.blast_rings.circle(ring[0] + ox, ring[1] + oy, ring[2], "", ring[4])
        if self.rings and self.rings[0][3] <= 0.0:
            self.rings[:] = [r for r in self.rings if r[3] > 0.0]

        for pop in self.popups:
            pop[4] -= frame_dt
            pop[1] -= frame_dt * 30.0
            if pop[4] > 0.0:
                self.popup_texts.text(pop[0] + ox, pop[1] + oy, pop[2], pop[3])
        if self.popups and self.popups[0][4] <= 0.0:
            self.popups[:] = [p for p in self.popups if p[4] > 0.0]

    # --- heads-up display -------------------------------------------------------------------

    def _build_hud(self, below):
        c, f = self.c, self.fonts
        items = {
            "bar": c.create_rectangle(0, 0, W, 32, fill=PANEL, outline=""),
            "hearts": c.create_text(14, 16, anchor="w", font=f["heart"], fill=HEART),
            "hearts_empty": c.create_text(14, 16, anchor="w", font=f["heart"], fill="#555870"),
            "bombs": c.create_text(165, 16, anchor="w", font=f["hud"], fill=PAPER),
            "wave": c.create_text(265, 16, anchor="w", font=f["hud"], fill=PAPER),
            "score": c.create_text(365, 16, anchor="w", font=f["hud"], fill="#ffd166"),
            "left": c.create_text(495, 16, anchor="w", font=f["hud"], fill=MUTED),
            "paint_bg": c.create_rectangle(752, 11, 852, 21, fill="#3a3d58", outline=""),
            "paint_fill": c.create_rectangle(752, 11, 752, 21, fill=PAPER, outline=""),
            "paint_text": c.create_text(652, 16, anchor="w", font=f["small"], fill=PAPER),
        }
        for item in items.values():
            c.tag_lower(item, below)
        self.hud = items
        self._hud_visible = True
        self.heart_w = tkfont.Font(font=f["heart"]).measure("♥")

    def _hud_set(self, name, **options):
        if self._hud_cache.get(name) != options:
            self.c.itemconfigure(self.hud[name], **options)
            self._hud_cache[name] = options

    def _draw_hud(self, game):
        show = game.state in (PLAYING, PAUSED, PERK, GAMEOVER) and game.world is not None
        if show != self._hud_visible:
            state = "normal" if show else "hidden"
            for name, item in self.hud.items():
                if name != "bar":
                    self.c.itemconfigure(item, state=state)
            self._hud_visible = show
        if not show:
            return
        w, p = game.world, game.world.player
        self._hud_set("hearts", text="♥" * p.hp)
        self._hud_set("hearts_empty", text="♥" * (p.max_hp - p.hp))
        c = self.c
        target = (14 + self.heart_w * p.hp, 16)
        if self._hud_cache.get("hearts_pos") != target:
            c.coords(self.hud["hearts_empty"], *target)
            self._hud_cache["hearts_pos"] = target
        self._hud_set("bombs", text=game.text("hud_bombs", bombs=p.bombs))
        self._hud_set("wave", text=game.text("hud_wave", wave=game.wave))
        self._hud_set("score", text=game.text("hud_score", score=game.score))
        left = game.director.remaining + w.enemy_count()
        self._hud_set("left", text=game.text("hud_left", count=left))
        pct = round(w.arena.coverage() * 100)
        self._hud_set("paint_text", text=game.text("hud_painted", pct=pct))
        hue = _hex(C.HUES[w.hue % len(C.HUES)])
        self._hud_set("paint_fill", fill=hue)
        width = (752, 11, 752 + pct, 21)
        if self._hud_cache.get("paint_w") != width:
            c.coords(self.hud["paint_fill"], *width)
            self._hud_cache["paint_w"] = width

    # --- language switch -----------------------------------------------------------------

    def _build_lang_toggle(self):
        c, f = self.c, self.fonts
        self.lang_box = (868, 3, 952, 29)
        self.lang_bg = c.create_rectangle(*self.lang_box, fill="#3a3d58", outline=MUTED, width=1)
        self.lang_tr = c.create_text(890, 16, text="TR", font=f["hud"])
        self.lang_bar = c.create_text(910, 16, text="|", font=f["hud"], fill=MUTED)
        self.lang_en = c.create_text(930, 16, text="EN", font=f["hud"])
        self._lang_drawn = None

    def _draw_lang_toggle(self, lang):
        if lang == self._lang_drawn:
            return
        self.c.itemconfigure(self.lang_tr, fill="#ffd166" if lang == "tr" else MUTED)
        self.c.itemconfigure(self.lang_en, fill="#ffd166" if lang == "en" else MUTED)
        self._lang_drawn = lang

    # --- menus and banners ----------------------------------------------------------------

    def hit_test(self, x, y):
        x0, y0, x1, y1 = self.lang_box
        if x0 <= x <= x1 and y0 <= y <= y1:
            return "lang"
        for bx0, by0, bx1, by1, action in self.buttons:
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                return action
        return None

    def _overlay_signature(self, game):
        banner = None
        if game.banner and game.state == PLAYING:
            banner = tuple(game.text(key, **params) for key, params in game.banner[0])
        extra = None
        if game.state == GAMEOVER:
            extra = tuple(sorted((game.last_result or {}).items()))
        elif game.state == SCORES:
            extra = tuple(game.score_rows())
        elif game.state == PERK:
            extra = tuple(game.perk_cards())
        return (game.state, game.lang, tuple(game.menu_items()), game.menu_index, banner, extra,
                game.display_world.hue)

    def _draw_overlay(self, game):
        sig = self._overlay_signature(game)
        if sig != self._overlay_sig:
            self._overlay_sig = sig
            self.c.delete("ui")
            self.buttons = []
            self._pulse_item = None
            self._pulse_step = -1
            builder = {
                TITLE: self._ui_title, PAUSED: self._ui_paused, GAMEOVER: self._ui_gameover,
                SETTINGS: self._ui_settings, SCORES: self._ui_scores, PERK: self._ui_perk,
                PLAYING: self._ui_playing,
            }[game.state]
            builder(game)
        if self._pulse_item is not None:
            step = int(game.clock * 6) % 12
            if step != self._pulse_step:
                self._pulse_step = step
                k = abs(6 - step) / 6.0
                self.c.itemconfigure(self._pulse_item, fill=_hex(_mix((255, 209, 102), (253, 250, 243), k)))

    def _ui(self, method, *args, **options):
        item = getattr(self.c, method)(*args, tags=("ui",), **options)
        self.c.tag_lower(item, self._ui_marker)
        return item

    def _panel(self, x0, y0, x1, y1):
        self._ui("create_rectangle", x0 + 6, y0 + 6, x1 + 6, y1 + 6, fill=INK, outline="")
        self._ui("create_rectangle", x0, y0, x1, y1, fill=PANEL, outline="#3a3d58", width=2)

    def _shadow_text(self, x, y, text, font, fill, **options):
        self._ui("create_text", x + 3, y + 3, text=text, font=font, fill=INK, **options)
        return self._ui("create_text", x, y, text=text, font=font, fill=fill, **options)

    def _hue(self, game):
        return C.HUES[game.display_world.hue % len(C.HUES)]

    def _menu(self, game, top, width=320, height=38, gap=46, font="mid"):
        hue = _hex(self._hue(game))
        x0 = (W - width) / 2
        for i, (action, label) in enumerate(game.menu_items()):
            y0 = top + i * gap
            selected = i == game.menu_index
            self._ui("create_rectangle", x0, y0, x0 + width, y0 + height,
                     fill=hue if selected else PAPER, outline=INK, width=2)
            self._ui("create_text", W / 2, y0 + height / 2, text=label, font=self.fonts[font],
                     fill="#ffffff" if selected else INK)
            self.buttons.append((x0, y0, x0 + width, y0 + height, action))

    def _controls_bar(self, game):
        self._ui("create_rectangle", 0, H - 50, W, H, fill=PANEL, outline="")
        self._ui("create_text", W / 2, H - 34, text=game.text("controls_1"),
                 font=self.fonts["body"], fill=PAPER)
        self._ui("create_text", W / 2, H - 14, text=game.text("controls_2"),
                 font=self.fonts["body"], fill=MUTED)

    def _ui_title(self, game):
        f = self.fonts
        self._panel(200, 46, 760, 490)
        title = game.text("app_title").upper()
        font = tkfont.Font(font=f["title"])
        widths = [font.measure(ch) for ch in title]
        x = (W - sum(widths)) / 2
        for i, ch in enumerate(title):
            color = _hex(C.HUES[i % len(C.HUES)])
            self._shadow_text(x + widths[i] / 2, 100, ch, f["title"], color)
            x += widths[i]
        self._ui("create_text", W / 2, 160, text=game.text("tagline"), font=f["big"], fill=PAPER)
        self._ui("create_text", W / 2, 200, text=game.text("intro"), font=f["body"], fill="#d9d9e6",
                 width=500, justify="center")
        self._pulse_item = self._ui("create_text", W / 2, 244, text=game.text("press_to_play"),
                                    font=f["mid"], fill="#ffd166")
        self._menu(game, 278, height=36, gap=44)
        self._ui("create_text", 14, 16, text=game.text("demo_label"), anchor="w",
                 font=f["small"], fill=MUTED)
        self._controls_bar(game)

    def _ui_playing(self, game):
        if not game.banner:
            return
        lines = [game.text(key, **params) for key, params in game.banner[0]]
        hue = _hex(self._hue(game))
        self._shadow_text(W / 2, 200, lines[0], self.fonts["banner"], PAPER)
        for i, line in enumerate(lines[1:]):
            self._shadow_text(W / 2, 250 + i * 36, line, self.fonts["big"], hue)

    def _ui_paused(self, game):
        self._panel(280, 150, 680, 400)
        self._shadow_text(W / 2, 205, game.text("paused"), self.fonts["banner"], PAPER)
        self._menu(game, 260)
        self._controls_bar(game)

    def _ui_gameover(self, game):
        f = self.fonts
        result = game.last_result or {"score": game.score, "wave": game.wave, "new_best": False}
        self._panel(230, 110, 730, 470)
        self._shadow_text(W / 2, 165, game.text("game_over"), f["banner"], PAPER)
        self._ui("create_text", W / 2, 222, text=game.text("final_score", score=result["score"]),
                 font=f["big"], fill="#ffd166")
        self._ui("create_text", W / 2, 258, text=game.text("reached_wave", wave=result["wave"]),
                 font=f["mid"], fill=PAPER)
        if result.get("new_best"):
            self._pulse_item = self._ui("create_text", W / 2, 292, text=game.text("new_best"),
                                        font=f["mid"], fill="#ffd166")
        self._menu(game, 330)

    def _ui_settings(self, game):
        self._panel(200, 90, 760, 520)
        self._shadow_text(W / 2, 145, game.text("settings_title"), self.fonts["banner"], PAPER)
        self._menu(game, 200, width=440, gap=54)
        self._ui("create_text", W / 2, 440, text=game.text("settings_hint"), font=self.fonts["body"],
                 fill=MUTED, width=480, justify="center")

    def _ui_scores(self, game):
        f = self.fonts
        self._panel(160, 60, 800, 580)
        self._shadow_text(W / 2, 110, game.text("scores_title"), f["banner"], PAPER)
        rows = game.score_rows()
        if not rows:
            self._ui("create_text", W / 2, 280, text=game.text("scores_empty"), font=f["mid"], fill=PAPER)
        for i, row in enumerate(rows):
            color = "#ffd166" if i == 0 else PAPER
            self._ui("create_text", 220, 165 + i * 30, text=row, anchor="w", font=f["body"], fill=color)
        self._menu(game, 505)

    def _ui_perk(self, game):
        f = self.fonts
        hue = _hex(self._hue(game))
        self._panel(100, 80, 860, 460)
        self._shadow_text(W / 2, 130, game.text("perk_title"), f["banner"], PAPER)
        self._ui("create_text", W / 2, 175, text=game.text("perk_hint"), font=f["body"], fill=PAPER)
        cards = game.perk_cards()
        card_w, card_h, gap = 250, 200, 30
        x = (W - (card_w * len(cards) + gap * (len(cards) - 1))) / 2
        for i, (action, title, desc, level) in enumerate(cards):
            selected = i == game.menu_index
            y0 = 215 - (8 if selected else 0)
            self._ui("create_rectangle", x + 6, y0 + 6, x + card_w + 6, y0 + card_h + 6, fill=INK, outline="")
            self._ui("create_rectangle", x, y0, x + card_w, y0 + card_h,
                     fill=PAPER, outline=hue if selected else INK, width=4 if selected else 2)
            self._ui("create_oval", x + 14, y0 + 14, x + 50, y0 + 50, fill=hue, outline=INK, width=2)
            self._ui("create_text", x + 32, y0 + 32, text=str(i + 1), font=f["mid"], fill="#ffffff")
            self._ui("create_text", x + card_w / 2, y0 + 82, text=title, font=f["big"], fill=INK,
                     width=card_w - 20, justify="center")
            self._ui("create_text", x + card_w / 2, y0 + 130, text=desc, font=f["body"], fill=INK,
                     width=card_w - 30, justify="center")
            self._ui("create_text", x + card_w / 2, y0 + card_h - 20,
                     text=game.text("perk_level", level=level), font=f["small"], fill=MUTED)
            self.buttons.append((x, y0, x + card_w, y0 + card_h, action))
            x += card_w + gap
