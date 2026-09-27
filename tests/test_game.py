import unittest

from splashback import config as C
from splashback.autopilot import Autopilot
from splashback.game import GAMEOVER, PAUSED, PERK, PLAYING, SCORES, SETTINGS, TITLE, Game
from splashback.storage import MemoryStorage
from splashback.world import Controls

DT = C.FIXED_DT

def new_game(lang="en", seed=11, storage=None):
    return Game(storage or MemoryStorage(), lang, seed=seed)

def play_until(game, predicate, seconds, pilot_seed=3):
    pilot = Autopilot(pilot_seed)
    for _ in range(int(seconds / DT)):
        if predicate():
            return True
        controls = pilot.control(game.world, DT) if game.state == PLAYING else Controls()
        game.update(DT, controls)
    return predicate()

class MenuTests(unittest.TestCase):
    def test_title_menu_and_navigation(self):
        g = new_game()
        self.assertEqual(g.state, TITLE)
        actions = [a for a, _ in g.menu_items()]
        self.assertEqual(actions, ["play", "settings", "scores", "quit"])
        g.command("up")
        self.assertEqual(g.menu_index, 3)
        g.command("down")
        self.assertEqual(g.menu_index, 0)
        g.command("confirm")
        self.assertEqual(g.state, PLAYING)

    def test_language_toggle_changes_every_label(self):
        g = new_game()
        english = [label for _, label in g.menu_items()]
        g.command("lang")
        self.assertEqual(g.lang, "tr")
        turkish = [label for _, label in g.menu_items()]
        self.assertNotEqual(english, turkish)
        self.assertEqual(g.storage.load_settings().lang, "tr")
        g.set_lang("xx")
        self.assertEqual(g.lang, "tr")

    def test_saved_language_used_when_none_given(self):
        st = MemoryStorage()
        new_game("tr", storage=st).set_lang("tr")
        self.assertEqual(Game(st).lang, "tr")

    def test_settings_screen(self):
        g = new_game()
        g.activate("settings")
        self.assertEqual(g.state, SETTINGS)
        g.activate("difficulty")
        self.assertEqual(g.settings.difficulty, "hard")
        g.activate("difficulty")
        self.assertEqual(g.settings.difficulty, "easy")
        g.activate("shake")
        self.assertFalse(g.storage.load_settings().shake)
        g.command("back")
        self.assertEqual(g.state, TITLE)

    def test_scores_screen_lists_rows(self):
        st = MemoryStorage()
        st.add_score(500, 4, "hard", today="2026-03-01")
        g = new_game("tr", storage=st)
        g.activate("scores")
        self.assertEqual(g.state, SCORES)
        self.assertIn("500 puan", g.score_rows()[0])
        self.assertIn("Zor", g.score_rows()[0])

    def test_demo_keeps_running_on_title(self):
        g = new_game()
        first = g.demo_world
        for _ in range(60 * 3):
            g.update(DT, Controls())
        self.assertIs(g.display_world, g.demo_world)
        self.assertGreater(first.arena.painted_count + first.arena.gloom_count, 0)

    def test_quit(self):
        g = new_game()
        g.activate("quit")
        self.assertTrue(g.quit_requested)

class RunTests(unittest.TestCase):
    def test_pause_and_resume(self):
        g = new_game()
        g.activate("play")
        g.command("back")
        self.assertEqual(g.state, PAUSED)
        t = g.world.time
        g.update(DT, Controls())
        self.assertEqual(g.world.time, t)
        g.activate("resume")
        self.assertEqual(g.state, PLAYING)

    def test_clearing_a_wave_offers_perks_and_saves(self):
        g = new_game()
        g.activate("play")
        self.assertEqual(g.storage.load_run()["wave"], 1)
        self.assertTrue(play_until(g, lambda: g.state == PERK, 120))
        cards = g.perk_cards()
        self.assertEqual(len(cards), 3)
        score_after_wave = g.score
        self.assertGreater(score_after_wave, 0)
        g.command("pick", 0)
        self.assertEqual((g.state, g.wave), (PLAYING, 2))
        self.assertEqual(sum(g.taken.values()), 1)
        saved = g.storage.load_run()
        self.assertEqual((saved["wave"], saved["score"]), (2, score_after_wave))

    def test_continue_restores_saved_run(self):
        st = MemoryStorage()
        g = new_game(storage=st)
        g.activate("play")
        play_until(g, lambda: g.state == PERK, 120)
        g.command("pick", 1)
        taken, score = dict(g.taken), g.score
        g.command("back")
        g.activate("to_title")
        self.assertIn("continue", [a for a, _ in g.menu_items()])

        fresh = Game(st, "en")
        self.assertIn("continue", [a for a, _ in fresh.menu_items()])
        fresh.activate("continue")
        self.assertEqual((fresh.state, fresh.wave, fresh.score), (PLAYING, 2, score))
        self.assertEqual(fresh.taken, taken)

    def test_death_records_score_and_clears_save(self):
        g = new_game()
        g.activate("play")
        g.score = 77
        p = g.world.player
        p.invuln = 0.0
        p.hp = 1
        g.world.hurt_player(p.x, p.y)
        self.assertTrue(play_until(g, lambda: g.state == GAMEOVER, 5))
        self.assertEqual(g.last_result["score"], 77)
        self.assertTrue(g.last_result["new_best"])
        self.assertEqual(g.storage.load_scores()[0]["score"], 77)
        self.assertIsNone(g.storage.load_run())
        g.activate("again")
        self.assertEqual((g.state, g.wave, g.score), (PLAYING, 1, 0))

    def test_same_seed_same_run(self):
        results = []
        for _ in range(2):
            g = new_game(seed=5)
            g.activate("play")
            play_until(g, lambda: False, 20)
            results.append((g.score, round(g.world.player.x, 6), g.world.arena.painted_count))
        self.assertEqual(results[0], results[1])

    def test_keys_after_game_over(self):
        g = new_game()
        g.activate("play")
        g.world.player.hp = 0
        g.world.player.alive = False
        play_until(g, lambda: g.state == GAMEOVER, 5)
        g.command("back")
        self.assertEqual(g.state, TITLE)

if __name__ == "__main__":
    unittest.main()
