import random
import math
import skia
from dataclasses import dataclass
from engine.physics import Vec2

@dataclass
class Particle:
    pos: Vec2
    vel: Vec2
    life: float
    max_life: float
    col: int
    sz: float
    gravity: float = 500.0

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, pos: Vec2, count: int, color: int, speed_range: tuple = (50, 200), life_range: tuple = (0.3, 0.8), size_range: tuple = (2, 6), gravity: float = 500.0):
        for _ in range(count):
            a = random.uniform(0, math.pi * 2)
            s = random.uniform(*speed_range)
            v = Vec2(math.cos(a) * s, math.sin(a) * s)
            self.particles.append(
                Particle(
                    pos=pos.copy(),
                    vel=v,
                    life=random.uniform(*life_range),
                    max_life=0.8, # Using the upper bound as max_life reference
                    col=color,
                    sz=random.uniform(*size_range),
                    gravity=gravity
                )
            )
            # Fix max_life to be the actual life started with
            self.particles[-1].max_life = self.particles[-1].life

    def append_manual(self, pos: Vec2, vel: Vec2, life: float, color: int, size: float = 3.0, gravity: float = 500.0):
        self.particles.append(
            Particle(
                pos=pos.copy(),
                vel=vel,
                life=life,
                max_life=life,
                col=color,
                sz=size,
                gravity=gravity
            )
        )

    def update(self, dt: float):
        for pt in self.particles[:]:
            pt.life -= dt
            pt.pos = pt.pos + pt.vel * dt
            pt.vel.y += pt.gravity * dt
            if pt.life <= 0:
                self.particles.remove(pt)

    def render(self, canvas: skia.Canvas):
        for pt in self.particles:
            a = pt.life / pt.max_life
            col = skia.Color4f.FromColor(pt.col)
            col.fA = a
            pa = skia.Paint(Color4f=col, Style=skia.Paint.kFill_Style, AntiAlias=True)
            canvas.drawCircle(pt.pos.x, pt.pos.y, pt.sz, pa)