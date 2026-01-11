from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple


class EventType(Enum):
    KEY_PRESS = auto()
    KEY_RELEASE = auto()
    MOUSE_PRESS = auto()
    MOUSE_RELEASE = auto()
    MOUSE_MOVE = auto()
    SCROLL = auto()
    RESIZE = auto()


@dataclass
class Event:
    type: EventType
    key: int = 0
    button: int = 0
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    width: int = 0
    height: int = 0
    mods: int = 0


class Component:
    def __init__(self, name="Component"):
        self.name = name
        self.enabled = True
        self.bounds = (0, 0, 0, 0)  # x, y, w, h for hit testing

    def on_init(self, ctx, canvas):
        """Called when the component is added to the engine."""
        pass

    def on_event(self, event: Event) -> bool:
        """Handle input events. Return True to consume the event."""
        return False

    def on_update(self, dt: float):
        """Logic/Simulation update."""
        pass

    def on_render_gl(self, ctx):
        """ModernGL 3D/Simulation rendering."""
        pass

    def on_render_ui(self, canvas):
        """Skia 2D/UI rendering."""
        pass

    def on_destroy(self):
        """Called when component is removed."""
        pass

    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is within component bounds."""
        bx, by, bw, bh = self.bounds
        return bx <= x <= bx + bw and by <= y <= by + bh
