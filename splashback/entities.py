"""Plain data holders for everything that moves. Behaviour lives in world, enemies and weapons."""

from . import config as C

class Player:
    __slots__ = (
        "x", "y", "radius", "hp", "max_hp", "speed", "fire_cooldown", "fire_timer",
        "shot_speed", "shot_range", "damage", "splash", "paint_amount", "extra_shots",
        "bombs", "max_bombs", "invuln", "face_x", "face_y", "rapid_timer",
        "triple_timer", "alive", "moving",
    )

    def __init__(self, max_hp=C.PLAYER_HP):
        max_hp = max(1, int(max_hp))
        self.x = 0.0
        self.y = 0.0
        self.radius = C.PLAYER_RADIUS
        self.max_hp = max_hp
        self.hp = max_hp
        self.speed = C.PLAYER_SPEED
        self.fire_cooldown = C.PLAYER_FIRE_COOLDOWN
        self.fire_timer = 0.0
        self.shot_speed = C.PLAYER_SHOT_SPEED
        self.shot_range = C.PLAYER_SHOT_RANGE
        self.damage = 1.0
        self.splash = C.PLAYER_SPLASH
        self.paint_amount = 2
        self.extra_shots = 0
        self.max_bombs = C.PLAYER_BOMBS
        self.bombs = C.PLAYER_BOMBS
        self.invuln = 0.0
        self.face_x = 1.0
        self.face_y = 0.0
        self.rapid_timer = 0.0
        self.triple_timer = 0.0
        self.alive = True
        self.moving = False

def make_player(difficulty="normal"):
    bonus = C.DIFFICULTY.get(difficulty, C.DIFFICULTY["normal"])["bonus_hp"]
    return Player(C.PLAYER_HP + bonus)

class Enemy:
    __slots__ = (
        "kind", "spec", "x", "y", "radius", "hp", "max_hp", "speed", "state", "timer",
        "cooldown", "dir_x", "dir_y", "spawn_timer", "last_tile", "hit_flash", "alive",
        "sees_player", "sight_timer", "wobble", "look_x", "look_y",
    )

    def __init__(self, spec, x, y, hp_mult=1.0, speed_mult=1.0, spawn_time=0.8):
        self.kind = spec.kind
        self.spec = spec
        self.x = x
        self.y = y
        self.radius = spec.radius
        self.max_hp = spec.hp * hp_mult
        self.hp = self.max_hp
        self.speed = spec.speed * speed_mult
        self.state = "walk"
        self.timer = 0.0
        self.cooldown = 1.0
        self.dir_x = 0.0
        self.dir_y = 0.0
        self.spawn_timer = spawn_time
        self.last_tile = -1
        self.hit_flash = 0.0
        self.alive = True
        self.sees_player = False
        self.sight_timer = 0.0
        self.wobble = 1.0
        self.look_x = 1.0
        self.look_y = 0.0

    @property
    def active(self):
        return self.alive and self.spawn_timer <= 0.0

class Projectile:
    """kind is 'paint' (the player's), 'glob' (gloom spit) or 'bomb'."""

    __slots__ = ("kind", "x", "y", "vx", "vy", "radius", "damage", "life", "splash",
                 "amount", "hue", "alive", "last_tile")

    def __init__(self, kind, x, y, vx, vy, radius, damage, life, splash, amount, hue=0):
        self.kind = kind
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.damage = damage
        self.life = life
        self.splash = splash
        self.amount = amount
        self.hue = hue
        self.alive = True
        self.last_tile = -1

class Pickup:
    """kind is 'heart', 'bomb', 'rapid' or 'triple'."""

    __slots__ = ("kind", "x", "y", "life", "alive")

    def __init__(self, kind, x, y, life=C.PICKUP_LIFE):
        self.kind = kind
        self.x = x
        self.y = y
        self.life = life
        self.alive = True
