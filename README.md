Türkçe: [README.tr.md](README.tr.md)

# Splashback

Splashback is a small top-down arena game: grey gloom creatures crawl in and drain the colour from the floor, and you run around throwing paint at them until the room is bright again.

```
python3 play.py
```

That's all you need. The window opens with the computer already playing a round in the background. Click anywhere or press Enter and you're in.

## How to play

| | |
|---|---|
| Move | WASD or the arrow keys |
| Aim | mouse |
| Throw paint | hold the left mouse button |
| Paint bomb | Space or right click |
| Pause | Esc |
| Switch language | L, or the `TR │ EN` button in the top-right corner |

- Every blob you throw leaves colour on the floor. You run faster on painted tiles, and the creatures slow down on them.
- The creatures leave grey gloom wherever they walk. It slows you down and speeds them up. Gloom has to be scrubbed off before your colour will show.
- Clear a wave and you get a paint bonus for how much of the floor is coloured. Then you pick one of three boosts: faster feet, wider splashes, an extra heart, and so on.
- Every fifth wave brings in the big ones.

## The creatures

- **Crawlers** walk straight at you and leave a grey trail.
- **Spitters** keep their distance and lob gloom globs.
- **Splitters** burst into two small, quick crawlers.
- **Brutes** shudder for a moment, then charge. Step aside.

## What gets saved

Your language, difficulty, screen-shake setting and top ten scores are saved between sessions. The game also saves at the start of every wave, so **Continue** on the title screen puts you back where you were. On Windows the data lives in `%APPDATA%\Splashback`, and on other systems in `~/.splashback`. Set `SPLASHBACK_HOME` to use a different folder.

## Language

The game follows your system language (Turkish or English). Change it at any time with the `TR │ EN` button or the L key, and it will remember your choice. From the terminal you can also start it in a given language with `python3 play.py --lang tr` or `--lang en`.

## Command line

```
python3 play.py                 # start the game
python3 play.py --lang tr       # start in Turkish
python3 play.py --seed 1234     # the same arenas every game
python3 play.py --reset         # forget settings, scores and the saved game
python3 -m splashback           # same as play.py
```

The only requirement is Python 3.8 or newer with tkinter, which ships with the python.org installers. There are no other dependencies.

## Under the hood

The simulation doesn't know about the window, and the window doesn't make any decisions:

- `world.py` runs one wave at a fixed 60 steps per second: movement, projectiles, collisions and pickups. It reports what happened as a list of events.
- `navigation.py` builds one Dijkstra flow field outward from the player's tile. It's rebuilt only when the player moves onto a different tile. Every creature then just steps to its tile's best neighbour, so pathfinding cost doesn't grow with the number of enemies. Line of sight is a grid traversal, and each creature rechecks it on a staggered timer.
- `physics.py` handles circle-versus-tile sliding and a spatial hash whose buckets are allocated once and cleared in place.
- `arena_gen.py` makes seeded, mirrored layouts and walls off any pocket that can't be reached from the centre.
- `game.py` is the single state machine (title, playing, paused, boosts, game over, settings, scores). `render.py` draws it on a Tk canvas using pools of reused canvas items, and only recolours floor tiles whose paint actually changed.
- `autopilot.py` plays the title-screen demo. The tests also use it to play whole waves.
- Every visible string lives in `strings.py`.

Run the tests with:

```
python3 -m unittest discover -s tests
```

## License

MIT
