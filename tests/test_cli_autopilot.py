import io
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from splashback import cli
from splashback import config as C
from splashback.arena_gen import generate_arena
from splashback.autopilot import Autopilot
from splashback.entities import make_player
from splashback.waves import WaveDirector
from splashback.world import World

class AutopilotTests(unittest.TestCase):
    def run_wave(self, seed):
        rng = random.Random(seed)
        world = World(generate_arena(seed), make_player(), rng, "normal", 0, 2)
        director = WaveDirector(2, "normal", rng)
        pilot = Autopilot(seed)
        for _ in range(60 * 60):
            world.step(C.FIXED_DT, pilot.control(world, C.FIXED_DT))
            director.update(C.FIXED_DT, world)
            world.events.clear()
            if director.finished and world.enemy_count() == 0:
                break
        return world, director

    def test_clears_an_early_wave_and_paints(self):
        world, director = self.run_wave(8)
        self.assertTrue(director.finished)
        self.assertEqual(world.enemy_count(), 0)
        self.assertGreater(world.arena.coverage(), 0.05)

    def test_is_deterministic(self):
        a, _ = self.run_wave(21)
        b, _ = self.run_wave(21)
        self.assertEqual((a.player.x, a.player.y, a.arena.paint), (b.player.x, b.player.y, b.arena.paint))

    def test_never_leaves_the_arena(self):
        world, _ = self.run_wave(3)
        self.assertFalse(world.arena.is_solid_point(world.player.x, world.player.y))

class CliTests(unittest.TestCase):
    def test_early_lang_lookup(self):
        self.assertEqual(cli._early_lang(["--lang", "tr"]), "tr")
        self.assertEqual(cli._early_lang(["--lang=en"]), "en")
        self.assertIsNone(cli._early_lang(["--lang"]))
        self.assertIsNone(cli._early_lang([]))

    def test_help_is_translated(self):
        for lang, word in (("tr", "arayüz dili"), ("en", "interface language")):
            out = io.StringIO()
            with redirect_stdout(out), self.assertRaises(SystemExit):
                cli.main(["--lang", lang, "--help"])
            self.assertIn(word, out.getvalue())

    def test_reset_clears_saved_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "data")
            os.makedirs(root)
            with open(os.path.join(root, "scores.json"), "w") as fh:
                fh.write("[]")
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"SPLASHBACK_HOME": root}), redirect_stdout(out):
                self.assertEqual(cli.main(["--reset", "--lang", "en"]), 0)
            self.assertFalse(os.path.exists(os.path.join(root, "scores.json")))
            self.assertIn("Saved data removed", out.getvalue())

if __name__ == "__main__":
    unittest.main()
