"""Command-line entry point: picks the language, opens storage and starts the window."""

import argparse
import sys

from . import __version__
from .storage import FileStorage, MemoryStorage
from .strings import LANGS, detect_system_lang, normalize_lang, t

def _early_lang(argv):
    """Find --lang before argparse runs, so that --help is already translated."""
    for i, arg in enumerate(argv):
        if arg.startswith("--lang="):
            return normalize_lang(arg.split("=", 1)[1])
        if arg == "--lang" and i + 1 < len(argv):
            return normalize_lang(argv[i + 1])
    return None

def build_parser(lang):
    parser = argparse.ArgumentParser(prog="splashback", description=t(lang, "cli_description"))
    parser.add_argument("--lang", choices=LANGS, help=t(lang, "cli_lang"))
    parser.add_argument("--seed", type=int, help=t(lang, "cli_seed"))
    parser.add_argument("--reset", action="store_true", help=t(lang, "cli_reset"))
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser

def open_storage(lang):
    storage = FileStorage()
    if not storage.writable:
        print(t(lang, "cli_storage_warning", path=storage.root), file=sys.stderr)
        return MemoryStorage()
    return storage

def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    lang = _early_lang(argv) or detect_system_lang()
    args = build_parser(lang).parse_args(argv)

    storage = open_storage(lang)
    if args.reset:
        if isinstance(storage, FileStorage):
            storage.reset()
            print(t(lang, "cli_reset_done", path=storage.root))
        return 0

    # An explicit --lang wins, then the saved choice, then the system language.
    lang = args.lang or storage.load_settings().lang or lang

    try:
        import tkinter
    except ImportError:
        print(t(lang, "cli_no_tk"), file=sys.stderr)
        return 2

    from .app import App
    from .game import Game

    game = Game(storage, lang, seed=args.seed)
    try:
        app = App(game)
    except tkinter.TclError as error:
        print(t(lang, "cli_no_window", error=error), file=sys.stderr)
        return 2
    app.run()
    return 0
