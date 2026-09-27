"""The Tk window: turns keys and mouse clicks into game input and runs the frame loop."""

import time
import tkinter as tk

from . import config as C
from .game import PLAYING, TITLE
from .render import Renderer, pick_fonts
from .world import Controls

MOVE_KEYS = {
    "left": (-1, 0), "a": (-1, 0), "right": (1, 0), "d": (1, 0),
    "up": (0, -1), "w": (0, -1), "down": (0, 1), "s": (0, 1),
}
MENU_KEYS = {"up": "up", "w": "up", "down": "down", "s": "down",
             "left": "up", "a": "up", "right": "down", "d": "down"}

class App:
    def __init__(self, game):
        self.game = game
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=C.WORLD_W, height=C.WORLD_H,
                                highlightthickness=0, bg="#23253a", cursor="crosshair")
        self.canvas.pack()
        self.renderer = Renderer(self.canvas, pick_fonts(self.root))
        self.controls = Controls()
        self.keys = set()
        self.mouse = (C.WORLD_W / 2, C.WORLD_H / 2)
        self.firing = False
        self.bomb_queued = False
        self._accumulator = 0.0
        self._last = time.perf_counter()
        self._title_lang = None

        root = self.root
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<KeyPress>", self._key_down)
        root.bind("<KeyRelease>", self._key_up)
        root.bind("<FocusOut>", self._focus_lost)
        self.canvas.bind("<Motion>", self._mouse_move)
        self.canvas.bind("<ButtonPress-1>", self._left_down)
        self.canvas.bind("<ButtonRelease-1>", self._left_up)
        self.canvas.bind("<ButtonPress-3>", self._right_down)
        self.canvas.bind("<ButtonPress-2>", self._right_down)   # macOS right click
        self.canvas.focus_set()

    # --- input ----------------------------------------------------------------------

    def _key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        game = self.game
        if key == "l":
            game.command("lang")
        elif key == "escape" or (key == "p" and game.state == PLAYING):
            game.command("back")
        elif key in ("return", "kp_enter"):
            game.command("confirm")
        elif key in ("1", "2", "3"):
            game.command("pick", int(key) - 1)
        elif game.state == PLAYING:
            if key == "space":
                self.bomb_queued = True
        elif key == "space":
            game.command("confirm")
        elif key in MENU_KEYS:
            game.command(MENU_KEYS[key])

    def _key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def _focus_lost(self, _event):
        self.keys.clear()
        self.firing = False
        self.game.command("pause_if_playing")

    def _mouse_move(self, event):
        self.mouse = (event.x, event.y)
        action = self.renderer.hit_test(event.x, event.y)
        if action and action != "lang":
            self.game.hover(action)

    def _left_down(self, event):
        self.mouse = (event.x, event.y)
        action = self.renderer.hit_test(event.x, event.y)
        if action:
            self.game.activate(action)
        elif self.game.state == PLAYING:
            self.firing = True
        elif self.game.state == TITLE:
            self.game.activate("play")

    def _left_up(self, _event):
        self.firing = False

    def _right_down(self, event):
        self.mouse = (event.x, event.y)
        if self.game.state == PLAYING:
            self.bomb_queued = True

    def _build_controls(self):
        c = self.controls
        mx = my = 0
        for key in self.keys:
            step = MOVE_KEYS.get(key)
            if step:
                mx += step[0]
                my += step[1]
        c.move_x, c.move_y = max(-1, min(1, mx)), max(-1, min(1, my))
        c.aim_x, c.aim_y = self.mouse
        c.fire = self.firing
        c.bomb = self.bomb_queued
        return c

    # --- loop ------------------------------------------------------------------------

    def run(self):
        self._last = time.perf_counter()
        self.root.after(1, self._tick)
        self.root.mainloop()

    def _tick(self):
        now = time.perf_counter()
        frame_dt = min(now - self._last, 0.1)
        self._last = now
        self._accumulator += frame_dt
        controls = self._build_controls()
        steps = 0
        while self._accumulator >= C.FIXED_DT and steps < C.MAX_STEPS_PER_FRAME:
            self.game.update(C.FIXED_DT, controls)
            if controls.bomb:
                controls.bomb = self.bomb_queued = False
            self._accumulator -= C.FIXED_DT
            steps += 1
        if steps == C.MAX_STEPS_PER_FRAME:
            self._accumulator = 0.0
        if self.game.quit_requested:
            self.close()
            return
        if self._title_lang != self.game.lang:
            self._title_lang = self.game.lang
            self.root.title(self.game.text("app_title") + " - " + self.game.text("tagline"))
        self.renderer.draw(self.game, frame_dt)
        spent = time.perf_counter() - now
        self.root.after(max(1, int((C.FIXED_DT - spent) * 1000)), self._tick)

    def close(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
