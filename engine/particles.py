import random, math, skia
from dataclasses import dataclass
from engine.physics import Vec2

@dataclass
class Particle:
    pos: Vec2; vel: Vec2; life: float; max_life: float; col: int; sz: float; gravity: float = 500.0

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.paint = skia.Paint(Style=skia.Paint.kFill_Style, AntiAlias=True)
    def emit(self, pos, count, color, speed_range=(50, 200), life_range=(0.3, 0.8), size_range=(2, 6), gravity=500.0):
        for _ in range(count):
            s = random.uniform(*speed_range); a = random.uniform(0, math.pi * 2); l = random.uniform(*life_range)
            self.particles.append(Particle(pos.copy(), Vec2(math.cos(a)*s, math.sin(a)*s), l, l, color, random.uniform(*size_range), gravity))
    def update(self, dt):
        for pt in self.particles[:]:
            pt.life -= dt; pt.pos = pt.pos + pt.vel * dt; pt.vel.y += pt.gravity * dt
            if pt.life <= 0: self.particles.remove(pt)
    def render(self, canvas):
        for pt in self.particles:
            col = skia.Color4f.FromColor(pt.col); col.fA = pt.life / pt.max_life
            self.paint.setColor4f(col)
            canvas.drawCircle(pt.pos.x, pt.pos.y, pt.sz, self.paint)
