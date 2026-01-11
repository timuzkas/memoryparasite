from dataclasses import dataclass
from typing import Callable

def linear(t): return t
def ease_in_quad(t): return t * t
def ease_out_quad(t): return t * (2 - t)
def ease_in_out_quad(t): return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t
def bounce_out(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1: return n1 * t * t
    elif t < 2 / d1: t -= 1.5 / d1; return n1 * t * t + 0.75
    elif t < 2.5 / d1: t -= 2.25 / d1; return n1 * t * t + 0.9375
    t -= 2.625 / d1; return n1 * t * t + 0.984375

class AnimationCurve:
    LINEAR, EASE_IN, EASE_OUT, EASE_IN_OUT, BOUNCE = linear, ease_in_quad, ease_out_quad, ease_in_out_quad, bounce_out

@dataclass
class Tween:
    name: str; start_val: float; end_val: float; duration: float; elapsed: float = 0.0
    curve: Callable = linear; on_complete: Callable = None
    @property
    def value(self):
        if self.duration == 0: return self.end_val
        return self.start_val + (self.end_val - self.start_val) * self.curve(min(1.0, max(0.0, self.elapsed / self.duration)))
    @property
    def is_finished(self): return self.elapsed >= self.duration

class Animator:
    def __init__(self): self.tweens = []
    def to(self, name, start, end, duration, curve=linear, on_complete=None):
        t = Tween(name, start, end, duration, 0.0, curve, on_complete); self.tweens.append(t); return t
    def update(self, dt):
        for t in self.tweens[:]:
            t.elapsed += dt
            if t.is_finished:
                if t.on_complete: t.on_complete()
                self.tweens.remove(t)
    def remove_tween(self, name): self.tweens = [t for t in self.tweens if t.name != name]

@dataclass
class SpriteAnimation:
    name: str; frames: list[int]; frame_duration: float = 0.1; loop: bool = True