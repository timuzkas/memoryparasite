import math
from dataclasses import dataclass, field
from typing import List

@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0
    def __add__(self, o): return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o): return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s): return Vec2(self.x * s, self.y * s)
    def __rmul__(self, s): return self.__mul__(s)
    def dot(self, o): return self.x * o.x + self.y * o.y
    def length(self): return math.sqrt(self.x**2 + self.y**2)
    def length_squared(self): return self.x**2 + self.y**2
    def normalized(self):
        ln = self.length()
        return Vec2(self.x / ln, self.y / ln) if ln > 0 else Vec2(0, 0)
    def copy(self): return Vec2(self.x, self.y)

@dataclass
class RigidBody:
    position: Vec2 = field(default_factory=Vec2)
    velocity: Vec2 = field(default_factory=Vec2)
    acceleration: Vec2 = field(default_factory=Vec2)
    mass: float = 1.0
    drag: float = 0.01
    restitution: float = 0.8
    is_static: bool = False

    def apply_force(self, force):
        if not self.is_static: self.acceleration = self.acceleration + force * (1.0 / self.mass)

    def update(self, dt):
        if self.is_static: return
        self.velocity = self.velocity * (1.0 - self.drag)
        self.velocity = self.velocity + self.acceleration * dt
        self.position = self.position + self.velocity * dt
        self.acceleration = Vec2(0, 0)

class PhysicsWorld:
    def __init__(self, gravity=None):
        self.gravity = gravity or Vec2(0, 0)
        self.bodies = []

    def add_body(self, b): self.bodies.append(b)
    def remove_body(self, b):
        if b in self.bodies: self.bodies.remove(b)

    def update(self, dt):
        for b in self.bodies:
            if not b.is_static: b.apply_force(self.gravity * b.mass)
            b.update(dt)