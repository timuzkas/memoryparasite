import random, math, skia
from dataclasses import dataclass, field
from typing import List, Optional
from engine.physics import RigidBody, Vec2, PhysicsWorld
from engine.collision import circle_vs_circle
from game.boss import Boss

@dataclass
class Enemy:
    body: RigidBody; r: float = 20.0; typ: str = "cloud"; hp: int = 1; dmg: float = 20.0
    spawn_pos: Vec2 = field(default_factory=Vec2); anim_t: float = 0.0; speed: float = 150.0
    is_dissolving: bool = False; dissolve_t: float = 0.0

class EnemyManager:
    def __init__(self, phys, coll):
        self.enemies, self.boss, self.phys, self.coll = [], None, phys, coll
        self.cloud_p = skia.Paint(Color=skia.Color(150, 150, 150, 150), AntiAlias=True)
        self.core_p = skia.Paint(Color=skia.Color(80, 80, 100, 200), AntiAlias=True)

    def spawn_lost_ghost(self, pos):
        eb = RigidBody(position=pos.copy(), mass=0.5, drag=0.05, restitution=0.5); self.phys.add_body(eb)
        self.enemies.append(Enemy(body=eb, spawn_pos=pos.copy()))

    def spawn_boss(self, pos): self.boss = Boss(self.phys, pos)

    def reset_for_death(self, keep_boss=False):
        for e in self.enemies: self.phys.remove_body(e.body)
        self.enemies.clear()
        if self.boss and not keep_boss: self.phys.remove_body(self.boss.body); self.boss = None

    def kill_all(self, part):
        for e in self.enemies:
            if not e.is_dissolving: e.is_dissolving = True; part.emit(e.body.position, 15, skia.Color(100, 200, 255), (50, 150))
        if self.boss: self.boss.freeze(2.0)

    def update(self, dt, player, level_manager, particles, audio):
        res = {'events': [], 'noise_hit': False, 'boss_hit': False}
        if self.boss:
            if self.boss.update(dt, player, particles, audio) > 0: res['boss_hit'] = True
            if self.boss.is_dead: self.phys.remove_body(self.boss.body); self.boss = None
            else:
                for ray in self.boss.noise_rays:
                    if self.boss._dist_point_to_segment(player.body.position, ray['start'], ray['end']) < player.cfg.r + 15: res['noise_hit'] = True
                vis = level_manager.get_visible_platforms(player.memory / player.cfg.max_mem)
                for atk in self.boss.attacks[:]:
                    for p in vis:
                        if p.x < atk['pos'].x < p.x + p.w and p.y < atk['pos'].y < p.y + p.h:
                            if atk.get('pen_p') == id(p): continue
                            if not atk.get('pen', False): atk['pen'] = True; atk['pen_p'] = id(p); atk['vel'] *= 0.5; particles.emit(atk['pos'], 5, skia.Color(150, 255, 150), (20, 100)); break
                            else: self.boss.explode_attack(atk, particles, audio); break
                        elif atk.get('pen_p') == id(p): atk['pen_p'] = None

        p_pos, p_r, lethal = player.body.position, player.width/2, player.is_dashing
        for e in self.enemies[:]:
            if e.is_dissolving:
                e.dissolve_t += dt
                if e.dissolve_t > 0.5: self.phys.remove_body(e.body); self.enemies.remove(e)
                continue
            e.anim_t += dt * 4; dir = (p_pos - e.body.position).normalized()
            e.body.apply_force((dir * e.speed + Vec2(math.sin(e.anim_t), math.cos(e.anim_t)) * 50) * 5.0)
            if e.body.velocity.length() > 250: e.body.velocity = e.body.velocity.normalized() * 250
            if circle_vs_circle(e.body.position, e.r, p_pos, p_r).hit:
                if lethal: e.is_dissolving = True; particles.emit(e.body.position, 20, skia.Color(200, 200, 255, 150), (50, 300))
                else: res['events'].append((e.dmg, e.body.position))
        return res

    def render(self, canvas, part):
        if self.boss: self.boss.render(canvas, part)
        for e in self.enemies:
            pos, alpha = e.body.position, int(255 * (1.0 - e.dissolve_t * 2.0)) if e.is_dissolving else 255
            self.cloud_p.setAlpha(int(150 * (alpha/255.0))); self.core_p.setAlpha(int(200 * (alpha/255.0)))
            for i in range(4):
                ang = e.anim_t + (i * 1.5)
                canvas.drawCircle(pos.x + math.cos(ang)*10, pos.y + math.sin(ang)*10, e.r * (1.0 + math.sin(e.anim_t*2+i)*0.3), self.cloud_p)
            canvas.drawCircle(pos.x, pos.y, e.r * 0.7, self.core_p)