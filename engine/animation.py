import math
from dataclasses import dataclass
from typing import Callable, Any

# Interpolation Curves
def linear(t: float) -> float:
    return t

def ease_in_quad(t: float) -> float:
    return t * t

def ease_out_quad(t: float) -> float:
    return t * (2 - t)

def ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

def ease_in_cubic(t: float) -> float:
    return t * t * t

def ease_out_cubic(t: float) -> float:
    return (--t) * t * t + 1

def bounce_out(t: float) -> float:
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375

class AnimationCurve:
    LINEAR = linear
    EASE_IN = ease_in_quad
    EASE_OUT = ease_out_quad
    EASE_IN_OUT = ease_in_out_quad
    BOUNCE = bounce_out

@dataclass
class Tween:
    name: str
    start_val: float
    end_val: float
    duration: float
    elapsed: float = 0.0
    curve: Callable[[float], float] = linear
    on_complete: Callable[[], None] | None = None
    
    @property
    def value(self) -> float:
        if self.duration == 0:
            return self.end_val
        t = min(1.0, max(0.0, self.elapsed / self.duration))
        v = self.curve(t)
        return self.start_val + (self.end_val - self.start_val) * v

    @property
    def is_finished(self) -> bool:
        return self.elapsed >= self.duration

class Animator:
    def __init__(self):
        self.tweens = []

    def to(self, name: str, start: float, end: float, duration: float, curve=linear, on_complete=None) -> Tween:
        t = Tween(name, start, end, duration, 0.0, curve, on_complete)
        self.tweens.append(t)
        return t

    def update(self, dt: float):
        for t in self.tweens[:]:
            t.elapsed += dt
            if t.is_finished:
                if t.on_complete:
                    t.on_complete()
                self.tweens.remove(t)

    def get_tween(self, name: str) -> Tween | None:
        for t in self.tweens:
            if t.name == name:
                return t
        return None

    def remove_tween(self, name: str):
        for t in self.tweens[:]:
            if t.name == name:
                self.tweens.remove(t)

# Sprite Animation Definition (for spritesheets)
@dataclass
class SpriteAnimation:
    name: str
    frames: list[int] # Indices
    frame_duration: float = 0.1
    loop: bool = True
