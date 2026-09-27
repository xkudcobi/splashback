import random
import unittest

from splashback import config as C
from splashback.arena_gen import generate_arena
from splashback.enemies import SPECS
from splashback.entities import Player, make_player
from splashback.perks import PERKS, apply_perk, offer_perks, rebuild_player
from splashback.waves import WaveDirector, build_wave, is_big_wave, wave_budget
from splashback.world import Controls, World

class WavePlanTests(unittest.TestCase):
    def test_budget_grows_and_scales_with_difficulty(self):
        self.assertLess(wave_budget(1), wave_budget(5))
        self.assertLess(wave_budget(4, "easy"), wave_budget(4, "normal"))
        self.assertLess(wave_budget(4, "normal"), wave_budget(4, "hard"))
        self.assertGreaterEqual(wave_budget(1, "easy"), 3)

    def test_plan_spends_budget_on_unlocked_kinds(self):
        for wave in range(1, 12):
            plan = build_wave(wave, "normal", random.Random(wave))
            with self.subTest(wave=wave):
                self.assertTrue(plan)
                for kind in plan:
                    self.assertLessEqual(SPECS[kind].min_wave, wave)
                spent = sum(SPECS[k].cost for k in plan)
                self.assertLessEqual(spent, wave_budget(wave) + (12 if is_big_wave(wave) else 0))

    def test_first_wave_is_only_crawlers(self):
        self.assertEqual(set(build_wave(1, "normal", random.Random(3))), {"crawler"})

    def test_big_waves_bring_brutes(self):
        self.assertTrue(is_big_wave(5))
        self.assertFalse(is_big_wave(4))
        self.assertGreaterEqual(build_wave(5, "normal", random.Random(1)).count("brute"), 2)

    def test_plan_is_deterministic(self):
        self.assertEqual(build_wave(7, "hard", random.Random(9)), build_wave(7, "hard", random.Random(9)))

    def test_director_releases_everything_far_from_player(self):
        rng = random.Random(4)
        world = World(generate_arena(4), Player(), rng)
        director = WaveDirector(3, "normal", rng)
        total = director.total
        spawned = 0
        p = world.player
        for _ in range(60 * 60):
            before = len(world.enemies)
            director.update(C.FIXED_DT, world)
            for e in world.enemies[before:]:
                spawned += 1
                self.assertGreater(abs(e.x - p.x) + abs(e.y - p.y), 5 * C.TILE)
            for e in world.enemies:   # clear the arena so the director never stalls on max_alive
                e.alive = False
            world.step(C.FIXED_DT, Controls())
            if director.finished:
                break
        self.assertTrue(director.finished)
        self.assertEqual(spawned, total)

class PerkTests(unittest.TestCase):
    def test_offers_are_distinct_and_respect_stacks(self):
        p = make_player()
        taken = {pid: perk.max_stacks for pid, perk in PERKS.items() if pid not in ("swift", "rapid")}
        offer = offer_perks(random.Random(1), taken, p)
        self.assertEqual(sorted(offer), ["rapid", "swift"])
        offer = offer_perks(random.Random(1), {}, p)
        self.assertEqual(len(offer), 3)
        self.assertEqual(len(set(offer)), 3)

    def test_heal_only_offered_when_hurt(self):
        p = make_player()
        for seed in range(30):
            self.assertNotIn("heal", offer_perks(random.Random(seed), {}, p, count=20))
        p.hp -= 1
        self.assertIn("heal", offer_perks(random.Random(0), {}, p, count=20))

    def test_apply_changes_stats_and_caps(self):
        p = Player()
        taken = {}
        self.assertTrue(apply_perk(p, "spread", taken))
        self.assertTrue(apply_perk(p, "spread", taken))
        self.assertFalse(apply_perk(p, "spread", taken))
        self.assertEqual(p.extra_shots, 2)
        apply_perk(p, "bomber", taken)
        self.assertEqual((p.max_bombs, p.bombs), (C.PLAYER_BOMBS + 1, C.PLAYER_BOMBS + 1))
        with self.assertRaises(KeyError):
            apply_perk(p, "nope", taken)

    def test_rebuild_matches_step_by_step(self):
        a, b = Player(), Player()
        taken = {}
        for pid in ("swift", "swift", "wide", "heavy", "rapid"):
            apply_perk(a, pid, taken)
        rebuild_player(b, dict(taken, unknown=3))
        for field in ("speed", "splash", "damage", "fire_cooldown"):
            self.assertAlmostEqual(getattr(a, field), getattr(b, field))

if __name__ == "__main__":
    unittest.main()
