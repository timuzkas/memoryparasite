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

def circle_vs_circle(pos_a, radius_a, pos_b, radius_b):
    diff = pos_b - pos_a
    dist = diff.length()
    min_dist = radius_a + radius_b
    if dist >= min_dist or dist == 0: return CollisionInfo(hit=False)
    normal = diff.normalized()
    return CollisionInfo(hit=True, normal=normal, depth=min_dist - dist, point=pos_a + normal * radius_a)

def circle_vs_rect(circle_pos, radius, rect_x, rect_y, rect_w, rect_h):
    closest_x = max(rect_x, min(circle_pos.x, rect_x + rect_w))
    closest_y = max(rect_y, min(circle_pos.y, rect_y + rect_h))
    closest = Vec2(closest_x, closest_y)
    diff = circle_pos - closest
    dist = diff.length()
    if dist >= radius: return CollisionInfo(hit=False)
    if dist == 0:
        dl, dr = circle_pos.x - rect_x, (rect_x + rect_w) - circle_pos.x
        dt, db = circle_pos.y - rect_y, (rect_y + rect_h) - circle_pos.y
        min_p = min(dl, dr, dt, db)
        if min_p == dl: normal = Vec2(-1, 0)
        elif min_p == dr: normal = Vec2(1, 0)
        elif min_p == dt: normal = Vec2(0, -1)
        else: normal = Vec2(0, 1)
        return CollisionInfo(hit=True, normal=normal, depth=radius + min_p, point=closest)
    return CollisionInfo(hit=True, normal=diff.normalized(), depth=radius - dist, point=closest)

def rect_vs_rect(ax, ay, aw, ah, bx, by, bw, bh):
    overlap_x = min(ax + aw, bx + bw) - max(ax, bx)
    overlap_y = min(ay + ah, by + bh) - max(ay, by)
    if overlap_x <= 0 or overlap_y <= 0: return CollisionInfo(hit=False)
    if overlap_x < overlap_y: return CollisionInfo(hit=True, normal=Vec2(1 if ax < bx else -1, 0), depth=overlap_x)
    return CollisionInfo(hit=True, normal=Vec2(0, 1 if ay < by else -1), depth=overlap_y)

def resolve_rect_vs_static(body, width, height, static_rects, padding=4.0, epsilon=0.01):
    grounded, hit_ceiling = False, False
    pad_x, pad_y = min(padding, width * 0.4), min(padding, height * 0.4)
    for r in static_rects:
        rx, ry, rw, rh = (r.x, r.y, r.w, r.h) if hasattr(r, "x") else r
        px, py = body.position.x - width / 2, body.position.y - height / 2
        if px + pad_x < rx + rw and px + width - pad_x > rx:
            if py < ry + rh and py + height > ry:
                if (py + height) - ry < (ry + rh) - py:
                    body.position.y = ry - height / 2 - epsilon
                    if body.velocity.y > 0: body.velocity.y = 0; grounded = True
                else:
                    body.position.y = ry + rh + height / 2 + epsilon
                    if body.velocity.y < 0: body.velocity.y = 0; hit_ceiling = True
    for r in static_rects:
        rx, ry, rw, rh = (r.x, r.y, r.w, r.h) if hasattr(r, "x") else r
        px, py = body.position.x - width / 2, body.position.y - height / 2
        if py + pad_y < ry + rh and py + height - pad_y > ry:
            if px < rx + rw and px + width > rx:
                if (px + width) - rx < (rx + rw) - px:
                    body.position.x = rx - width / 2 - epsilon
                    if body.velocity.x > 0: body.velocity.x = 0
                else:
                    body.position.x = rx + rw + width / 2 + epsilon
                    if body.velocity.x < 0: body.velocity.x = 0
    return grounded, hit_ceiling

def resolve_collision(body_a, body_b, info):
    if not info.hit: return
    if body_a.is_static: body_b.position = body_b.position + info.normal * info.depth
    elif body_b.is_static: body_a.position = body_a.position - info.normal * info.depth
    else:
        body_a.position = body_a.position - info.normal * (info.depth / 2)
        body_b.position = body_b.position + info.normal * (info.depth / 2)
    rel_vel = body_b.velocity - body_a.velocity
    vel_along_normal = rel_vel.dot(info.normal)
    if vel_along_normal > 0: return
    e = min(body_a.restitution, body_b.restitution)
    inv_mass_a = 0 if body_a.is_static else 1.0 / body_a.mass
    inv_mass_b = 0 if body_b.is_static else 1.0 / body_b.mass
    j = -(1 + e) * vel_along_normal / (inv_mass_a + inv_mass_b)
    impulse = info.normal * j
    if not body_a.is_static: body_a.velocity = body_a.velocity - impulse * inv_mass_a
    if not body_b.is_static: body_b.velocity = body_b.velocity + impulse * inv_mass_b

class CollisionWorld:
    def __init__(self):
        self.circles = []; self.rects = []
    def add_circle(self, b, r): self.circles.append((b, r))
    def add_rect(self, b, w, h): self.rects.append((b, w, h))
    def check_and_resolve(self):
        for i, (ba, ra) in enumerate(self.circles):
            for j, (bb, rb) in enumerate(self.circles):
                if i < j: resolve_collision(ba, bb, circle_vs_circle(ba.position, ra, bb.position, rb))
        for bc, rc in self.circles:
            for br, w, h in self.rects: resolve_collision(bc, br, circle_vs_rect(bc.position, rc, br.position.x-w/2, br.position.y-h/2, w, h))
        for i, (ba, wa, ha) in enumerate(self.rects):
            for j, (bb, wb, hb) in enumerate(self.rects):
                if i < j: resolve_collision(ba, bb, rect_vs_rect(ba.position.x-wa/2, ba.position.y-ha/2, wa, ha, bb.position.x-wb/2, bb.position.y-hb/2, wb, hb))