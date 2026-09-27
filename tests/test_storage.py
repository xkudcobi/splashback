import json
import os
import tempfile
import unittest

from splashback.storage import (MAX_SCORES, FileStorage, MemoryStorage, Settings, clean_run,
                                insert_score)

GOOD_RUN = {"version": 1, "seed": 5, "wave": 3, "score": 120, "hp": 4,
            "difficulty": "hard", "perks": {"swift": 2}}

class SettingsTests(unittest.TestCase):
    def test_bad_values_fall_back(self):
        s = Settings.from_dict({"lang": "de", "difficulty": "insane", "shake": "yes"})
        self.assertEqual((s.lang, s.difficulty, s.shake), (None, "normal", True))
        s = Settings.from_dict({"lang": "tr", "difficulty": "hard", "shake": False})
        self.assertEqual((s.lang, s.difficulty, s.shake), ("tr", "hard", False))
        self.assertEqual(Settings.from_dict(["not", "a", "dict"]), Settings())

class ScoreTests(unittest.TestCase):
    def test_insert_keeps_order_and_limit(self):
        scores = []
        self.assertEqual(insert_score(scores, 50, 2, "normal", "d"), 1)
        self.assertEqual(insert_score(scores, 80, 3, "normal", "d"), 1)
        self.assertEqual(insert_score(scores, 60, 3, "normal", "d"), 2)
        self.assertEqual([s["score"] for s in scores], [80, 60, 50])
        for i in range(20):
            insert_score(scores, 1000 + i, 1, "easy", "d")
        self.assertEqual(len(scores), MAX_SCORES)
        self.assertIsNone(insert_score(scores, 1, 1, "easy", "d"))

    def test_ties_rank_below_existing(self):
        scores = []
        insert_score(scores, 10, 1, "normal", "first")
        self.assertEqual(insert_score(scores, 10, 1, "normal", "second"), 2)

class RunTests(unittest.TestCase):
    def test_clean_run(self):
        self.assertEqual(clean_run(GOOD_RUN)["perks"], {"swift": 2})
        for broken in (None, [], dict(GOOD_RUN, version=9), dict(GOOD_RUN, wave=0),
                       dict(GOOD_RUN, hp="x"), dict(GOOD_RUN, difficulty="??")):
            self.assertIsNone(clean_run(broken))

    def test_memory_storage_round_trip(self):
        st = MemoryStorage()
        st.save_run(GOOD_RUN)
        self.assertEqual(st.load_run()["wave"], 3)
        st.clear_run()
        self.assertIsNone(st.load_run())
        st.save_run({"junk": True})
        self.assertIsNone(st.load_run())

class FileStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "save")

    def tearDown(self):
        self.tmp.cleanup()

    def test_persists_between_instances(self):
        st = FileStorage(self.root)
        st.save_settings(Settings(lang="tr", difficulty="easy", shake=False))
        st.add_score(300, 4, "easy", today="2026-01-02")
        st.save_run(GOOD_RUN)
        again = FileStorage(self.root)
        self.assertEqual(again.load_settings(), Settings("tr", "easy", False))
        self.assertEqual(again.load_scores()[0],
                         {"score": 300, "wave": 4, "difficulty": "easy", "date": "2026-01-02"})
        self.assertEqual(again.load_run()["seed"], 5)
        again.clear_run()
        self.assertIsNone(FileStorage(self.root).load_run())

    def test_corrupt_files_are_ignored(self):
        os.makedirs(self.root)
        with open(os.path.join(self.root, "settings.json"), "w") as fh:
            fh.write("{not json")
        with open(os.path.join(self.root, "scores.json"), "w") as fh:
            json.dump([{"score": "lots"}, {"score": 5, "wave": 1}, "x"], fh)
        st = FileStorage(self.root)
        self.assertEqual(st.load_settings(), Settings())
        self.assertEqual([s["score"] for s in st.load_scores()], [5])

    def test_reset_removes_everything(self):
        st = FileStorage(self.root)
        st.add_score(10, 1, "normal")
        st.reset()
        self.assertFalse(os.path.exists(os.path.join(self.root, "scores.json")))
        self.assertEqual(st.load_scores(), [])

    def test_unwritable_location_is_reported(self):
        blocker = os.path.join(self.tmp.name, "file")
        with open(blocker, "w") as fh:
            fh.write("x")
        st = FileStorage(os.path.join(blocker, "inside"))
        st.save_settings(Settings())
        self.assertFalse(st.writable)

if __name__ == "__main__":
    unittest.main()
