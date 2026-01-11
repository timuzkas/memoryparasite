import random
import math
import skia
from dataclasses import dataclass, field
from typing import List, Optional
from engine.physics import RigidBody, Vec2, PhysicsWorld
from engine.collision import CollisionWorld, circle_vs_circle
from game.boss import Boss

@dataclass
class Enemy:
    body: RigidBody
    r: float = 20.0
    typ: str = "cloud"
    hp: int = 1
    dmg: float = 20.0 # High memory damage
    spawn_pos: Vec2 = field(default_factory=Vec2)
    anim_t: float = 0.0
    speed: float = 150.0
    is_dissolving: bool = False
    dissolve_t: float = 0.0

class EnemyManager:
    def __init__(self, phys: PhysicsWorld, coll: CollisionWorld):
        self.enemies: List[Enemy] = []
        self.boss: Optional[Boss] = None
        self.phys = phys
        self.coll = coll
        self.spawn_timer = 0.0
        self.cloud_paint = skia.Paint(Color=skia.Color(150, 150, 150, 150), Style=skia.Paint.kFill_Style, AntiAlias=True)
        self.cloud_core_paint = skia.Paint(Color=skia.Color(80, 80, 100, 200), Style=skia.Paint.kFill_Style, AntiAlias=True)

    def spawn_lost_ghost(self, pos: Vec2):
        eb = RigidBody(position=pos.copy(), mass=0.5, drag=0.05, restitution=0.5)
        self.phys.add_body(eb)
        e = Enemy(body=eb, spawn_pos=pos.copy())
        self.enemies.append(e)

    def spawn_boss(self, pos: Vec2):
        self.boss = Boss(self.phys, pos)

    def reset_for_death(self, keep_boss: bool = False):
        for e in self.enemies:
            self.phys.remove_body(e.body)
        self.enemies.clear()
        if self.boss and not keep_boss:
            self.phys.remove_body(self.boss.body)
            self.boss = None

    def kill_all(self, particles):
        for e in self.enemies:
            if not e.is_dissolving:
                e.is_dissolving = True
                particles.emit(e.body.position, 15, skia.Color(100, 200, 255), speed_range=(50, 150))
        if self.boss:
            self.boss.freeze(2.0)

    def update(self, dt: float, player, level_manager, particles, audio) -> dict:
        # returns {'events': list of (damage, pos), 'noise_hit': bool, 'boss_hit': bool}
        res = {'events': [], 'noise_hit': False, 'boss_hit': False}
        
        if self.boss:
            hit = self.boss.update(dt, player, particles, audio)
            if hit > 0:
                res['boss_hit'] = True
            
            if self.boss.is_dead:
                self.phys.remove_body(self.boss.body)
                self.boss = None
            else:
                # Check if any noise ray is active and hitting player
                for ray in self.boss.noise_rays:
                    if self.boss._dist_point_to_segment(player.body.position, ray['start'], ray['end']) < player.cfg.r + 10:
                        res['noise_hit'] = True
                
                # Check if arrows hit platforms
                visible_platforms = level_manager.get_visible_platforms(player.memory / player.cfg.max_mem)
                for atk in self.boss.attacks[:]:
                    for p in visible_platforms:
                        if p.x < atk['pos'].x < p.x + p.w and p.y < atk['pos'].y < p.y + p.h:
                            # Already penetrated this platform? (prevent double trigger)
                            if atk.get('penetrating_p') == id(p):
                                continue
                                
                            if not atk.get('penetrated', False):
                                # First time hitting a platform
                                atk['penetrated'] = True
                                atk['penetrating_p'] = id(p) # Remember this platform
                                atk['vel'] *= 0.5 # Lose speed
                                # Emit some "impact but pass-thru" particles
                                particles.emit(atk['pos'], 5, skia.Color(150, 255, 150), speed_range=(20, 100))
                                break 
                            else:
                                # Already penetrated one, so crash into the second one
                                self.boss.explode_attack(atk, particles, audio)
                                break
                        else:
                            # If we were penetrating a platform and now we are not, clear the reference
                            if atk.get('penetrating_p') == id(p):
                                atk['penetrating_p'] = None

        player_pos = player.body.position
        player_radius = player.width / 2
        is_player_lethal = player.is_dashing
        
        for e in self.enemies[:]:
            if e.is_dissolving:
                e.dissolve_t += dt
                if e.dissolve_t > 0.5:
                    self.phys.remove_body(e.body)
                    self.enemies.remove(e)
                continue

            e.anim_t += dt * 4
            
            # Chase player
            to_player = player_pos - e.body.position
            dist = to_player.length()
            if dist > 0:
                dir = to_player.normalized()
                # Floatiness noise
                noise = Vec2(math.sin(e.anim_t), math.cos(e.anim_t)) * 50
                e.body.apply_force((dir * e.speed + noise) * 5.0)

            # Cap velocity
            if e.body.velocity.length() > 250:
                e.body.velocity = e.body.velocity.normalized() * 250

            # Collision with Player
            inf = circle_vs_circle(e.body.position, e.r, player_pos, player_radius)
            if inf.hit:
                if is_player_lethal: # Player is dashing
                    e.is_dissolving = True
                    particles.emit(e.body.position, 20, skia.Color(200, 200, 255, 150), speed_range=(50, 300))
                else:
                    res['events'].append((e.dmg, e.body.position))
                    # Knockback player a bit
                    kb = (player_pos - e.body.position).normalized() * 300
                
        return res

    def render(self, canvas: skia.Canvas, particles):
        if self.boss:
            self.boss.render(canvas, particles)
        for e in self.enemies:
            pos = e.body.position
            alpha = int(255 * (1.0 - e.dissolve_t * 2.0)) if e.is_dissolving else 255
            
            self.cloud_paint.setAlpha(int(150 * (alpha/255.0)))
            self.cloud_core_paint.setAlpha(int(200 * (alpha/255.0)))

            # Draw "Cloud"
            for i in range(4):
                offset_ang = e.anim_t + (i * 1.5)
                ox = math.cos(offset_ang) * 10
                oy = math.sin(offset_ang) * 10
                scale = 1.0 + math.sin(e.anim_t * 2 + i) * 0.3
                canvas.drawCircle(pos.x + ox, pos.y + oy, e.r * scale, self.cloud_paint)
            
            canvas.drawCircle(pos.x, pos.y, e.r * 0.7, self.cloud_core_paint)
