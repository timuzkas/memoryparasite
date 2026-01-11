from dataclasses import dataclass
from enum import Enum, auto

class EventType(Enum):
    KEY_PRESS = auto(); KEY_RELEASE = auto(); MOUSE_PRESS = auto(); MOUSE_RELEASE = auto(); MOUSE_MOVE = auto(); SCROLL = auto(); RESIZE = auto()

@dataclass
class Event:
    type: EventType; key: int = 0; button: int = 0; x: float = 0.0; y: float = 0.0; dx: float = 0.0; dy: float = 0.0; width: int = 0; height: int = 0; mods: int = 0

class Component:
    def __init__(self, name="Component"):
        self.name, self.enabled, self.bounds = name, True, (0, 0, 0, 0)
    def on_init(self, ctx, canvas): pass
    def on_event(self, event): return False
    def on_update(self, dt): pass
    def on_render_gl(self, ctx): pass
    def on_render_ui(self, canvas): pass
    def on_destroy(self): pass
    def contains_point(self, x, y):
        bx, by, bw, bh = self.bounds
        return bx <= x <= bx + bw and by <= y <= by + bh