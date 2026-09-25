"""Tuning constants shared by the simulation and the window."""

TILE = 32
COLS = 30
ROWS = 20
WORLD_W = COLS * TILE
WORLD_H = ROWS * TILE

FIXED_DT = 1.0 / 60.0
MAX_STEPS_PER_FRAME = 5

# Tile paint runs from -GLOOM_MAX (fully grey) to PAINT_MAX (fully coloured).
PAINT_MAX = 4
GLOOM_MAX = 3

PLAYER_RADIUS = 11
PLAYER_SPEED = 172.0
PLAYER_HP = 5
PLAYER_FIRE_COOLDOWN = 0.16
PLAYER_SHOT_SPEED = 440.0
PLAYER_SHOT_RANGE = 360.0
PLAYER_SPLASH = 30.0
PLAYER_BOMBS = 2
INVULN_TIME = 1.1

BOMB_SPEED = 380.0
BOMB_MAX_THROW = 260.0
BOMB_RADIUS = 84.0
BOMB_DAMAGE = 6.0

GLOB_SPEED = 210.0
GLOB_RADIUS = 6

SPEED_ON_PAINT = 1.25
SPEED_ON_GLOOM = 0.72
ENEMY_SPEED_ON_PAINT = 0.72
ENEMY_SPEED_ON_GLOOM = 1.2

PICKUP_LIFE = 10.0
PICKUP_CHANCE = 0.13
POWERUP_TIME = 8.0

DIFFICULTIES = ("easy", "normal", "hard")
DIFFICULTY = {
    "easy": {"hp": 0.75, "count": 0.75, "speed": 0.88, "bonus_hp": 2, "score": 0.8, "fire": 1.25},
    "normal": {"hp": 1.0, "count": 1.0, "speed": 1.0, "bonus_hp": 0, "score": 1.0, "fire": 1.0},
    "hard": {"hp": 1.3, "count": 1.3, "speed": 1.12, "bonus_hp": -1, "score": 1.5, "fire": 0.8},
}

# Paint colours, one per wave in rotation.
HUES = (
    (255, 84, 122),
    (32, 190, 176),
    (255, 186, 36),
    (132, 94, 255),
    (255, 128, 48),
    (64, 156, 255),
)
