"""The game's single source of state: which screen is showing, the current run and its score.

Input arrives as small named commands (``command``) and menu actions
(``activate``); time arrives through ``update``. A window only has to translate
keys and clicks into those calls and draw what it finds here.
"""

import random

from . import config as C
from .arena_gen import generate_arena
from .autopilot import Autopilot
from .entities import make_player
from .perks import apply_perk, offer_perks, rebuild_player
from .storage import RUN_VERSION
from .strings import DEFAULT_LANG, LANGS, other_lang, t
from .waves import WaveDirector, is_big_wave
from .world import World

TITLE, PLAYING, PAUSED, PERK, GAMEOVER, SETTINGS, SCORES = (
    "title", "playing", "paused", "perk", "gameover", "settings", "scores")
DEMO_STATES = (TITLE, SETTINGS, SCORES)

CLEAR_DELAY = 1.8
DEATH_DELAY = 1.3
BANNER_TIME = 2.2
MAX_FX = 400
DEMO_WARMUP_STEPS = 300

class Game:
    def __init__(self, storage, lang=None, seed=None):
        self.storage = storage
        self.settings = storage.load_settings()
        self.lang = lang if lang in LANGS else (self.settings.lang or DEFAULT_LANG)
        self.fixed_seed = seed
        self._seeds = random.Random(seed)
        self.state = TITLE
        self.menu_index = 0
        self.quit_requested = False
        self.clock = 0.0
        self.fx = []
        self.banner = None          # (list of (key, params), seconds left)
        self.saved_run = storage.load_run()
        self.last_result = None

        self.world = None
        self.director = None
        self.player = None
        self.wave = 0
        self.score = 0
        self.run_seed = 0
        self.run_difficulty = "normal"
        self.taken = {}
        self.perk_offer = []
        self._perk_rng = random.Random(0)
        self._clear_timer = 0.0
        self._end_timer = 0.0

        self._demo_wave = 2
        self._demo_end = 0.0
        self._new_demo()

    # --- small helpers ------------------------------------------------------------

    def text(self, key, **params):
        return t(self.lang, key, **params)

    @property
    def display_world(self):
        return self.demo_world if self.state in DEMO_STATES else self.world

    @property
    def best_score(self):
        scores = self.storage.load_scores()
        return scores[0]["score"] if scores else 0

    def _set_state(self, state):
        self.state = state
        self.menu_index = 0

    def _show_banner(self, *lines):
        self.banner = (list(lines), BANNER_TIME)

    def _push_fx(self, events):
        self.fx.extend(events)
        if len(self.fx) > MAX_FX:
            del self.fx[:len(self.fx) - MAX_FX]

    # --- menus --------------------------------------------------------------------

    def menu_items(self):
        """(action, label) pairs for the current screen, top to bottom."""
        s = self.state
        if s == TITLE:
            items = [("play", self.text("menu_play"))]
            if self.saved_run:
                items.append(("continue", self.text("menu_continue", wave=self.saved_run["wave"])))
            items += [("settings", self.text("menu_settings")),
                      ("scores", self.text("menu_scores")),
                      ("quit", self.text("menu_quit"))]
            return items
        if s == PAUSED:
            return [("resume", self.text("menu_resume")), ("to_title", self.text("menu_to_title"))]
        if s == GAMEOVER:
            return [("again", self.text("menu_again")), ("to_title", self.text("menu_to_title"))]
        if s == SETTINGS:
            onoff = self.text("on") if self.settings.shake else self.text("off")
            return [
                ("lang", self.text("setting_language", value=self.text("lang_name"))),
                ("difficulty", self.text("setting_difficulty",
                                         value=self.text("diff_" + self.settings.difficulty))),
                ("shake", self.text("setting_shake", value=onoff)),
                ("back", self.text("menu_back")),
            ]
        if s == SCORES:
            return [("back", self.text("menu_back"))]
        if s == PERK:
            return [("perk:%d" % i, self.text("perk_" + pid)) for i, pid in enumerate(self.perk_offer)]
        return []

    def perk_cards(self):
        """(action, title, description, level it would reach) for the perk screen."""
        return [("perk:%d" % i, self.text("perk_" + pid), self.text("perk_%s_desc" % pid),
                 self.taken.get(pid, 0) + 1)
                for i, pid in enumerate(self.perk_offer)]

    def score_rows(self):
        rows = []
        for rank, entry in enumerate(self.storage.load_scores(), start=1):
            rows.append(self.text("score_row", rank=rank, score=entry["score"], wave=entry["wave"],
                                  difficulty=self.text("diff_" + entry["difficulty"]),
                                  date=entry["date"] or "-"))
        return rows

    def hover(self, action):
        for i, (item_action, _) in enumerate(self.menu_items()):
            if item_action == action:
                self.menu_index = i
                return

    def command(self, name, arg=None):
        """Keyboard-level input: up, down, confirm, back, lang, pick."""
        items = self.menu_items()
        if name in ("up", "down") and items:
            step = -1 if name == "up" else 1
            self.menu_index = (self.menu_index + step) % len(items)
        elif name == "confirm":
            if items:
                self.activate(items[min(self.menu_index, len(items) - 1)][0])
        elif name == "back":
            if self.state == PLAYING:
                self._set_state(PAUSED)
            elif self.state == PAUSED:
                self.state = PLAYING
            elif self.state in (SETTINGS, SCORES, GAMEOVER):
                self._set_state(TITLE)
        elif name == "lang":
            self.set_lang(other_lang(self.lang))
        elif name == "pick" and self.state == PERK:
            self.activate("perk:%d" % int(arg))
        elif name == "pause_if_playing" and self.state == PLAYING:
            self._set_state(PAUSED)

    def activate(self, action):
        if action in ("play", "again"):
            self.start_new_run()
        elif action == "continue":
            self.continue_run()
        elif action == "settings":
            self._set_state(SETTINGS)
        elif action == "scores":
            self._set_state(SCORES)
        elif action == "quit":
            self.quit_requested = True
        elif action == "resume" and self.state == PAUSED:
            self.state = PLAYING
        elif action in ("to_title", "back"):
            self.saved_run = self.storage.load_run()
            self._set_state(TITLE)
        elif action == "lang":
            self.set_lang(other_lang(self.lang))
        elif action == "difficulty":
            order = C.DIFFICULTIES
            self.settings.difficulty = order[(order.index(self.settings.difficulty) + 1) % len(order)]
            self.storage.save_settings(self.settings)
        elif action == "shake":
            self.settings.shake = not self.settings.shake
            self.storage.save_settings(self.settings)
        elif action.startswith("perk:") and self.state == PERK:
            self.choose_perk(int(action[5:]))

    def set_lang(self, lang):
        if lang not in LANGS:
            return
        self.lang = lang
        self.settings.lang = lang
        self.storage.save_settings(self.settings)

    # --- runs -----------------------------------------------------------------------

    def start_new_run(self):
        self.run_seed = self.fixed_seed if self.fixed_seed is not None else self._seeds.randrange(1 << 30)
        self.run_difficulty = self.settings.difficulty
        self.score = 0
        self.taken = {}
        self.player = make_player(self.run_difficulty)
        self.last_result = None
        self._begin_wave(1)

    def continue_run(self):
        run = self.saved_run
        if not run:
            return False
        self.run_seed = run["seed"]
        self.run_difficulty = run["difficulty"]
        self.score = run["score"]
        self.taken = dict(run["perks"])
        self.player = make_player(self.run_difficulty)
        rebuild_player(self.player, self.taken)
        self.player.hp = min(self.player.max_hp, run["hp"])
        self.last_result = None
        self._begin_wave(run["wave"], save=False)
        return True

    def _begin_wave(self, wave, save=True):
        self.wave = wave
        arena = generate_arena(self.run_seed * 1009 + wave)
        rng = random.Random(self.run_seed * 7919 + wave)
        p = self.player
        p.invuln = 1.5
        p.bombs = p.max_bombs
        p.fire_timer = 0.0
        p.rapid_timer = p.triple_timer = 0.0
        self.world = World(arena, p, rng, self.run_difficulty, (wave - 1) % len(C.HUES), wave)
        self.director = WaveDirector(wave, self.run_difficulty, rng)
        self._perk_rng = random.Random(self.run_seed * 31 + wave)
        self._clear_timer = 0.0
        self._end_timer = 0.0
        lines = [("wave_start", {"wave": wave})]
        if is_big_wave(wave):
            lines.append(("big_wave", {}))
        self._show_banner(*lines)
        self._set_state(PLAYING)
        if save:
            self.storage.save_run({
                "version": RUN_VERSION, "seed": self.run_seed, "wave": wave,
                "score": self.score, "hp": p.hp, "difficulty": self.run_difficulty,
                "perks": dict(self.taken),
            })
        self.saved_run = self.storage.load_run()

    def choose_perk(self, index):
        if not 0 <= index < len(self.perk_offer):
            return False
        apply_perk(self.player, self.perk_offer[index], self.taken)
        self.perk_offer = []
        self._begin_wave(self.wave + 1)
        return True

    def _finish_wave(self):
        self.perk_offer = offer_perks(self._perk_rng, self.taken, self.player)
        if self.perk_offer:
            self._set_state(PERK)
        else:
            self._begin_wave(self.wave + 1)

    def _end_run(self):
        best_before = self.best_score
        rank = self.storage.add_score(self.score, self.wave, self.run_difficulty)
        self.storage.clear_run()
        self.saved_run = None
        self.last_result = {
            "score": self.score, "wave": self.wave, "rank": rank,
            "new_best": self.score > best_before and self.score > 0,
        }
        self._set_state(GAMEOVER)

    # --- time -----------------------------------------------------------------------

    def update(self, dt, controls):
        self.clock += dt
        if self.banner:
            lines, left = self.banner
            left -= dt
            self.banner = (lines, left) if left > 0 else None
        if self.state in DEMO_STATES:
            self._update_demo(dt)
        elif self.state == PLAYING:
            self._update_run(dt, controls)

    def _update_run(self, dt, controls):
        w = self.world
        w.step(dt, controls)
        self.director.update(dt, w)
        mult = C.DIFFICULTY[self.run_difficulty]["score"]
        for ev in w.events:
            if ev[0] == "kill":
                points = max(1, round(ev[4] * mult))
                self.score += points
                self.fx.append(("points", ev[1], ev[2], points))
        self._push_fx(w.events)
        w.events.clear()

        if not w.player.alive:
            self._end_timer += dt
            if self._end_timer >= DEATH_DELAY:
                self._end_run()
            return
        if self._clear_timer > 0.0:
            self._clear_timer -= dt
            if self._clear_timer <= 0.0:
                self._finish_wave()
        elif self.director.finished and w.enemy_count() == 0:
            pct = round(w.arena.coverage() * 100)
            bonus = pct * self.wave
            self.score += bonus
            self._clear_timer = CLEAR_DELAY
            self._show_banner(("wave_clear", {}), ("paint_bonus", {"points": bonus}))

    # --- title-screen demo ------------------------------------------------------------

    def _new_demo(self):
        seed = self._seeds.randrange(1 << 30)
        player = make_player("normal")
        player.max_hp = player.hp = 8
        rng = random.Random(seed)
        self.demo_world = World(generate_arena(seed), player, rng, "normal",
                                seed % len(C.HUES), self._demo_wave)
        self.demo_director = WaveDirector(self._demo_wave, "normal", rng)
        self.demo_pilot = Autopilot(seed)
        self._demo_wave = 2 + (self._demo_wave - 1) % 5
        self._demo_end = 0.0
        self._demo_age = 0.0
        # Fast-forward a few seconds so the first screen already shows a painted, busy arena.
        self.demo_director.timer = 0.1
        w, dt = self.demo_world, C.FIXED_DT
        for _ in range(DEMO_WARMUP_STEPS):
            w.step(dt, self.demo_pilot.control(w, dt))
            self.demo_director.update(dt, w)
            w.events.clear()

    def _update_demo(self, dt):
        w = self.demo_world
        w.step(dt, self.demo_pilot.control(w, dt))
        self.demo_director.update(dt, w)
        self._push_fx(w.events)
        w.events.clear()
        self._demo_age += dt
        over = (not w.player.alive or self._demo_age > 70.0
                or (self.demo_director.finished and w.enemy_count() == 0))
        if over:
            self._demo_end += dt
            if self._demo_end > 1.2:
                self._new_demo()
