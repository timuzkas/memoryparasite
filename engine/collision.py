import math
from dataclasses import dataclass
from typing import Optional, Tuple

from engine.physics import RigidBody, Vec2


@dataclass
class CollisionInfo:
    hit: bool = False
    normal: Vec2 | None = None
    depth: float = 0.0
    point: Vec2 | None = None


def circle_vs_circle(
    pos_a: Vec2, radius_a: float, pos_b: Vec2, radius_b: float
) -> CollisionInfo:
    """Check collision between two circles."""
    diff = pos_b - pos_a
    dist = diff.length()
    min_dist = radius_a + radius_b

    if dist >= min_dist or dist == 0:
        return CollisionInfo(hit=False)

    normal = diff.normalized()
    depth = min_dist - dist
    point = pos_a + normal * radius_a

    return CollisionInfo(hit=True, normal=normal, depth=depth, point=point)


def circle_vs_rect(
    circle_pos: Vec2,
    radius: float,
    rect_x: float,
    rect_y: float,
    rect_w: float,
    rect_h: float,
) -> CollisionInfo:
    """Check collision between a circle and an axis-aligned rectangle."""
    # Find closest point on rectangle to circle center
    closest_x = max(rect_x, min(circle_pos.x, rect_x + rect_w))
    closest_y = max(rect_y, min(circle_pos.y, rect_y + rect_h))
    closest = Vec2(closest_x, closest_y)

    diff = circle_pos - closest
    dist = diff.length()

    if dist >= radius:
        return CollisionInfo(hit=False)

    if dist == 0:
        # Circle center is inside the rectangle. Push out to the nearest edge.
        # Check distances to edges
        # closest_x is circle_pos.x, closest_y is circle_pos.y
        dl = circle_pos.x - rect_x
        dr = (rect_x + rect_w) - circle_pos.x
        dt = circle_pos.y - rect_y
        db = (rect_y + rect_h) - circle_pos.y
        
        # Find minimum penetration
        min_p = min(dl, dr, dt, db)
        
        if min_p == dl:
            normal = Vec2(-1, 0)
            depth = radius + dl # Ensure we push out fully + radius? 
            # If center is inside, depth is distance to surface? No.
            # Depth in Resolve is overlap amount.
            # If we want to push center to surface + radius:
            # We want to push by `radius + min_p`? 
            # If min_p is 10 (10 units inside), and radius is 10.
            # If we push by 10, center is ON surface. Still intersecting?
            # Yes, if center is on surface, distance is 0.
            # We need to push so distance is Radius.
            depth = radius + min_p
        elif min_p == dr:
            normal = Vec2(1, 0)
            depth = radius + dr
        elif min_p == dt:
            normal = Vec2(0, -1)
            depth = radius + dt
        else:
            normal = Vec2(0, 1)
            depth = radius + db
            
        return CollisionInfo(hit=True, normal=normal, depth=depth, point=closest)

    normal = diff.normalized()
    depth = radius - dist

    return CollisionInfo(hit=True, normal=normal, depth=depth, point=closest)


def rect_vs_rect(
    ax: float,
    ay: float,
    aw: float,
    ah: float,
    bx: float,
    by: float,
    bw: float,
    bh: float,
) -> CollisionInfo:
    """Check collision between two axis-aligned rectangles."""
    overlap_x = min(ax + aw, bx + bw) - max(ax, bx)
    overlap_y = min(ay + ah, by + bh) - max(ay, by)

    if overlap_x <= 0 or overlap_y <= 0:
        return CollisionInfo(hit=False)

    if overlap_x < overlap_y:
        normal = Vec2(1 if ax < bx else -1, 0)
        depth = overlap_x
    else:
        normal = Vec2(0, 1 if ay < by else -1)
        depth = overlap_y

    return CollisionInfo(hit=True, normal=normal, depth=depth)


def resolve_rect_vs_static(
    body: RigidBody,
    width: float,
    height: float,
    static_rects: list,
    padding: float = 4.0,
    epsilon: float = 0.01,
) -> Tuple[bool, bool]:
    """
    Robust axis-locked resolution for a dynamic rect against static world geometry.
    Strictly separates Y and X passes to prevent sticking on seams.
    """
    grounded = False
    hit_ceiling = False

    # Ensure padding isn't larger than the box itself
    pad_x = min(padding, width * 0.4)
    pad_y = min(padding, height * 0.4)

    # Pass 1: Vertical Resolution (Y)
    for r in static_rects:
        rx, ry, rw, rh = (r.x, r.y, r.w, r.h) if hasattr(r, "x") else r
        px = body.position.x - width / 2
        py = body.position.y - height / 2

        # Horizontal overlap check with dynamic padding
        if px + pad_x < rx + rw and px + width - pad_x > rx:
            # Check vertical overlap
            if py < ry + rh and py + height > ry:
                # Calculate penetration depths
                overlap_top = (py + height) - ry
                overlap_bottom = (ry + rh) - py

                if overlap_top < overlap_bottom:  # Closer to top of platform
                    body.position.y = ry - height / 2 - epsilon
                    if body.velocity.y > 0:
                        body.velocity.y = 0
                        grounded = True
                else:  # Closer to bottom of platform
                    body.position.y = ry + rh + height / 2 + epsilon
                    if body.velocity.y < 0:
                        body.velocity.y = 0
                        hit_ceiling = True

    # Pass 2: Horizontal Resolution (X)
    for r in static_rects:
        rx, ry, rw, rh = (r.x, r.y, r.w, r.h) if hasattr(r, "x") else r
        px = body.position.x - width / 2
        py = body.position.y - height / 2

        # Vertical overlap check with dynamic padding
        if py + pad_y < ry + rh and py + height - pad_y > ry:
            # Check horizontal overlap
            if px < rx + rw and px + width > rx:
                # Calculate penetration depths
                overlap_left = (px + width) - rx
                overlap_right = (rx + rw) - px

                if overlap_left < overlap_right:  # Closer to left of platform
                    body.position.x = rx - width / 2 - epsilon
                    if body.velocity.x > 0:
                        body.velocity.x = 0
                else:  # Closer to right of platform
                    body.position.x = rx + rw + width / 2 + epsilon
                    if body.velocity.x < 0:
                        body.velocity.x = 0

    return grounded, hit_ceiling


def resolve_collision(body_a: RigidBody, body_b: RigidBody, info: CollisionInfo):
    """Resolve a collision between two rigid bodies."""
    if not info.hit:
        return

    # Separate bodies
    if body_a.is_static and info.normal:
        body_b.position = body_b.position + info.normal * info.depth
    elif body_b.is_static and info.normal:
        body_a.position = body_a.position - info.normal * info.depth
    else:
        half_depth = info.depth / 2
        if info.normal:
            body_a.position = body_a.position - info.normal * half_depth
            body_b.position = body_b.position + info.normal * half_depth

    # Calculate relative velocity
    rel_vel = body_b.velocity - body_a.velocity
    if info.normal:
        vel_along_normal = rel_vel.dot(info.normal)

        # Don't resolve if separating
        if vel_along_normal > 0:
            return

        # Restitution (bounciness)
        e = min(body_a.restitution, body_b.restitution)

        # Impulse scalar
        if body_a.is_static:
            inv_mass_a = 0
        else:
            inv_mass_a = 1.0 / body_a.mass
        if body_b.is_static:
            inv_mass_b = 0
        else:
            inv_mass_b = 1.0 / body_b.mass

        j = -(1 + e) * vel_along_normal / (inv_mass_a + inv_mass_b)

        # Apply impulse
        impulse = info.normal * j
        if not body_a.is_static:
            body_a.velocity = body_a.velocity - impulse * inv_mass_a
        if not body_b.is_static:
            body_b.velocity = body_b.velocity + impulse * inv_mass_b


class CollisionWorld:
    """Manages collision detection for a set of colliders."""

    def __init__(self):
        self.circles: list[Tuple[RigidBody, float]] = []  # (body, radius)
        self.rects: list[Tuple[RigidBody, float, float]] = []  # (body, width, height)

    def add_circle(self, body: RigidBody, radius: float):
        self.circles.append((body, radius))

    def add_rect(self, body: RigidBody, width: float, height: float):
        self.rects.append((body, width, height))

    def check_and_resolve(self):
        # Circle vs Circle
        for i, (body_a, rad_a) in enumerate(self.circles):
            for j, (body_b, rad_b) in enumerate(self.circles):
                if i >= j:
                    continue
                info = circle_vs_circle(body_a.position, rad_a, body_b.position, rad_b)
                resolve_collision(body_a, body_b, info)

        # Circle vs Rect
        for body_c, rad_c in self.circles:
            for body_r, w, h in self.rects:
                rx = body_r.position.x - w / 2
                ry = body_r.position.y - h / 2
                info = circle_vs_rect(body_c.position, rad_c, rx, ry, w, h)
                resolve_collision(body_c, body_r, info)

        # Rect vs Rect
        for i, (body_a, wa, ha) in enumerate(self.rects):
            for j, (body_b, wb, hb) in enumerate(self.rects):
                if i >= j:
                    continue
                ax = body_a.position.x - wa / 2
                ay = body_a.position.y - ha / 2
                bx = body_b.position.x - wb / 2
                by = body_b.position.y - hb / 2
                info = rect_vs_rect(ax, ay, wa, ha, bx, by, wb, hb)
                resolve_collision(body_a, body_b, info)
