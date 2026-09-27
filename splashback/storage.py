"""Settings, best scores and the unfinished game, kept as small JSON files.

Everything read from disk is validated; a broken or hand-edited file falls back
to defaults instead of stopping the game.
"""

import datetime
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass

from . import config as C
from .strings import LANGS

MAX_SCORES = 10
RUN_VERSION = 1

@dataclass
class Settings:
    lang: str = None
    difficulty: str = "normal"
    shake: bool = True

    @classmethod
    def from_dict(cls, data):
        s = cls()
        if not isinstance(data, dict):
            return s
        if data.get("lang") in LANGS:
            s.lang = data["lang"]
        if data.get("difficulty") in C.DIFFICULTIES:
            s.difficulty = data["difficulty"]
        if isinstance(data.get("shake"), bool):
            s.shake = data["shake"]
        return s

def _clean_score(entry):
    if not isinstance(entry, dict):
        return None
    try:
        score = int(entry["score"])
        wave = int(entry["wave"])
    except (KeyError, TypeError, ValueError):
        return None
    if score < 0 or wave < 1:
        return None
    difficulty = entry.get("difficulty")
    if difficulty not in C.DIFFICULTIES:
        difficulty = "normal"
    date = entry.get("date") if isinstance(entry.get("date"), str) else ""
    return {"score": score, "wave": wave, "difficulty": difficulty, "date": date[:10]}

def clean_run(data):
    """Return a validated saved-game dict, or None when it is unusable."""
    if not isinstance(data, dict) or data.get("version") != RUN_VERSION:
        return None
    try:
        run = {
            "version": RUN_VERSION,
            "seed": int(data["seed"]),
            "wave": int(data["wave"]),
            "score": int(data["score"]),
            "hp": int(data["hp"]),
            "difficulty": data.get("difficulty", "normal"),
            "perks": {str(k): int(v) for k, v in dict(data.get("perks", {})).items()},
        }
    except (KeyError, TypeError, ValueError):
        return None
    if run["wave"] < 1 or run["hp"] < 1 or run["score"] < 0:
        return None
    if run["difficulty"] not in C.DIFFICULTIES:
        return None
    return run

def insert_score(scores, score, wave, difficulty, date):
    """Insert into a sorted list, trim it, and return the 1-based rank (or None)."""
    entry = {"score": int(score), "wave": int(wave), "difficulty": difficulty, "date": date}
    rank = len(scores)
    for i, other in enumerate(scores):
        if score > other["score"]:
            rank = i
            break
    if rank >= MAX_SCORES:
        return None
    scores.insert(rank, entry)
    del scores[MAX_SCORES:]
    return rank + 1

class MemoryStorage:
    """Keeps everything in memory. Used by tests and when the disk is not writable."""

    def __init__(self):
        self._settings = Settings()
        self._scores = []
        self._run = None

    def load_settings(self):
        return Settings(**asdict(self._settings))

    def save_settings(self, settings):
        self._settings = Settings(**asdict(settings))

    def load_scores(self):
        return [dict(s) for s in self._scores]

    def add_score(self, score, wave, difficulty, today=None):
        today = today or datetime.date.today().isoformat()
        return insert_score(self._scores, score, wave, difficulty, today)

    def load_run(self):
        return dict(self._run) if self._run else None

    def save_run(self, run):
        self._run = clean_run(run)

    def clear_run(self):
        self._run = None

class FileStorage(MemoryStorage):
    """Same interface, persisted under one folder."""

    def __init__(self, root=None):
        super().__init__()
        self.root = root or default_root()
        self.writable = True
        self._settings = Settings.from_dict(self._read("settings.json"))
        raw_scores = self._read("scores.json")
        scores = [_clean_score(s) for s in raw_scores] if isinstance(raw_scores, list) else []
        self._scores = sorted((s for s in scores if s), key=lambda s: -s["score"])[:MAX_SCORES]
        self._run = clean_run(self._read("run.json"))

    def _path(self, name):
        return os.path.join(self.root, name)

    def _read(self, name):
        try:
            with open(self._path(name), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _write(self, name, data):
        # Write to a temp file and swap it in, so a crash never leaves half a file.
        try:
            os.makedirs(self.root, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".tmp-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self._path(name))
        except OSError:
            self.writable = False

    def save_settings(self, settings):
        super().save_settings(settings)
        self._write("settings.json", asdict(self._settings))

    def add_score(self, score, wave, difficulty, today=None):
        rank = super().add_score(score, wave, difficulty, today)
        if rank is not None:
            self._write("scores.json", self._scores)
        return rank

    def save_run(self, run):
        super().save_run(run)
        if self._run:
            self._write("run.json", self._run)

    def clear_run(self):
        super().clear_run()
        try:
            os.remove(self._path("run.json"))
        except OSError:
            pass

    def reset(self):
        shutil.rmtree(self.root, ignore_errors=True)
        self.__init__(self.root)

def default_root():
    override = os.environ.get("SPLASHBACK_HOME")
    if override:
        return override
    base = os.environ.get("APPDATA") if os.name == "nt" else None
    if base:
        return os.path.join(base, "Splashback")
    return os.path.join(os.path.expanduser("~"), ".splashback")
