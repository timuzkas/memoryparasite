import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        return self.__mul__(scalar)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def length_squared(self) -> float:
        return self.x**2 + self.y**2

    def normalized(self) -> "Vec2":
        ln = self.length()
        if ln == 0:
            return Vec2(0, 0)
        return Vec2(self.x / ln, self.y / ln)

    def copy(self) -> "Vec2":
        return Vec2(self.x, self.y)


@dataclass
class RigidBody:
    position: Vec2 = field(default_factory=Vec2)
    velocity: Vec2 = field(default_factory=Vec2)
    acceleration: Vec2 = field(default_factory=Vec2)
    mass: float = 1.0
    drag: float = 0.01
    restitution: float = 0.8  # Bounciness (0-1)
    is_static: bool = False

    def apply_force(self, force: Vec2):
        if self.is_static:
            return
        self.acceleration = self.acceleration + force * (1.0 / self.mass)

    def apply_impulse(self, impulse: Vec2):
        if self.is_static:
            return
        self.velocity = self.velocity + impulse * (1.0 / self.mass)

    def update(self, dt: float):
        if self.is_static:
            return

        # Apply drag
        self.velocity = self.velocity * (1.0 - self.drag)

        # Integrate
        self.velocity = self.velocity + self.acceleration * dt
        self.position = self.position + self.velocity * dt

        # Reset acceleration
        self.acceleration = Vec2(0, 0)


class PhysicsWorld:
    def __init__(self, gravity: Vec2 = None):
        self.gravity = gravity or Vec2(0, 0)
        self.bodies: List[RigidBody] = []

    def add_body(self, body: RigidBody):
        self.bodies.append(body)

    def remove_body(self, body: RigidBody):
        if body in self.bodies:
            self.bodies.remove(body)

    def update(self, dt: float):
        for body in self.bodies:
            if not body.is_static:
                body.apply_force(self.gravity * body.mass)
            body.update(dt)

    def constrain_to_bounds(
        self,
        body: RigidBody,
        radius: float,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ):
        """Keep a circular body within rectangular bounds."""
        if body.position.x - radius < min_x:
            body.position.x = min_x + radius
            body.velocity.x *= -body.restitution
        if body.position.x + radius > max_x:
            body.position.x = max_x - radius
            body.velocity.x *= -body.restitution
        if body.position.y - radius < min_y:
            body.position.y = min_y + radius
            body.velocity.y *= -body.restitution
        if body.position.y + radius > max_y:
            body.position.y = max_y - radius
            body.velocity.y *= -body.restitution
