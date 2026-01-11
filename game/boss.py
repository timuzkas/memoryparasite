import random
import math
import skia
from engine.physics import RigidBody, Vec2, PhysicsWorld
from engine.collision import circle_vs_circle, rect_vs_rect

class Boss:
    def __init__(self, phys: PhysicsWorld, pos: Vec2):
        self.max_hp = 300 # Increased from 100
        self.hp = 300
        self.rage = 0.0 # 0.0 to 1.0
        self.rage_boost = 0.1 # Base rage boost
        self.freeze_timer = 0.0
        
        self.r = 60.0 # 3x bigger than player (approx)
        self.body = RigidBody(position=pos, mass=10.0, drag=0.1, restitution=0.5)
        phys.add_body(self.body)
        
        self.anim_t = 0.0
        self.attacks = [] # List of active projectils/effects
        self.attack_timer = 2.0
        
        self.is_dead = False
        self.noise_rays = [] # List of {'start': Vec2, 'end': Vec2, 'timer': float, 'max_t': float}

    def update(self, dt: float, player, particles, audio):
        if self.is_dead:
            return 0

        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            return 0

        self.anim_t += dt
        
        hp_rage = (1.0 - (self.hp / self.max_hp)) * 1.2 # More aggressive rage
        self.rage = max(0.0, min(1.0, hp_rage + self.rage_boost))
        
        # Slowly decrease rage boost over time
        if self.rage_boost > 0.1:
            self.rage_boost -= 0.03 * dt
        
        # Floating movement
        target_pos = Vec2(640 + math.sin(self.anim_t * 0.5) * 400, 200 + math.cos(self.anim_t * 0.8) * 100)
        to_target = target_pos - self.body.position
        self.body.apply_force(to_target * 5.0)
        
        # Attack logic
        self.attack_timer -= dt * (1.0 + self.rage)
        if self.attack_timer <= 0:
            self._trigger_attack(player, audio)
            # Attacks become much more frequent at high rage
            self.attack_timer = random.uniform(1.0, 2.5) / (1.0 + self.rage * 1.5)

        # Update attacks (Arrows)
        for atk in self.attacks[:]:
            atk['pos'] += atk['vel'] * dt
            atk['t'] += dt
            
            # Trail logic
            if random.random() < 0.4:
                atk['trail'].append({
                    'pos': atk['pos'].copy(),
                    'char': random.choice(["0", "1", "x", "f", "a", "7", "!", "&"]),
                    'life': 0.6
                })
            
            for t in atk['trail'][:]:
                t['life'] -= dt
                if t['life'] <= 0:
                    atk['trail'].remove(t)

            # Collision with player
            if (atk['pos'] - player.body.position).length() < 30:
                self._apply_glitch(player, particles, audio)
                self.explode_attack(atk, particles, audio)
                continue
            # Remove off-screen
            if atk['pos'].x < -100 or atk['pos'].x > 1380 or atk['pos'].y < -100 or atk['pos'].y > 820:
                self.attacks.remove(atk)
                continue

        # Update Noise Rays
        for ray in self.noise_rays[:]:
            ray['timer'] -= dt
            # Check collision with player
            if ray['timer'] > 0:
                # Simple line-segment vs circle collision or distance check
                dist = self._dist_point_to_segment(player.body.position, ray['start'], ray['end'])
                if dist < player.cfg.r + 15: # Wider collision
                    # Apply noise to screen (handled in game.py by checking boss state)
                    player.memory -= 8.0 * dt # More damage
            else:
                self.noise_rays.remove(ray)

        # Dash damage from player
        hit_this_frame = 0
        if player.is_dashing:
            if (self.body.position - player.body.position).length() < self.r + 25:
                self.hp -= 15 # More damage per dash but more HP
                self.rage_boost += 0.12 # Get angrier when hit
                hit_this_frame = 1
                
                particles.emit(self.body.position, 30, skia.Color(255, 0, 0), speed_range=(100, 400))
                # Push back a bit
                kb = (self.body.position - player.body.position).normalized() * 600
                self.body.velocity += kb
                if self.hp <= 0:
                    self.is_dead = True
                    particles.emit(self.body.position, 100, skia.ColorWHITE, speed_range=(200, 600))
        
        return hit_this_frame

    def _trigger_attack(self, player, audio):
        rnd = random.random()
        # Increased initial speed
        atk_speed = 600 + self.rage * 600 
        
        if rnd < 0.5:
            # Bit Arrow
            dir = (player.body.position - self.body.position).normalized()
            self.attacks.append({
                'pos': self.body.position.copy(),
                'vel': dir * atk_speed,
                't': 0.0,
                'trail': [],
                'penetrated': False # Can pass thru 1 obstacle
            })
            audio.play("hitWall", volume=0.5)
        elif rnd < 0.8:
            # Noise Ray
            end_pos = player.body.position + Vec2(random.uniform(-150, 150), random.uniform(-150, 150))
            self.noise_rays.append({
                'start': self.body.position.copy(),
                'end': end_pos,
                'timer': 0.8 + self.rage,
                'max_t': 0.8 + self.rage
            })
            audio.play("noise", volume=0.4)
        else:
            # NEW: Cluster Shot - fire 5 arrows in a fan
            base_dir = (player.body.position - self.body.position).normalized()
            base_angle = math.atan2(base_dir.y, base_dir.x)
            for i in range(-2, 3):
                angle = base_angle + (i * 0.3)
                vel = Vec2(math.cos(angle), math.sin(angle)) * (atk_speed * 0.8)
                self.attacks.append({
                    'pos': self.body.position.copy(),
                    'vel': vel,
                    't': 0.0,
                    'trail': [],
                    'penetrated': False
                })
            audio.play("shock", volume=0.6)

    def _apply_glitch(self, player, particles, audio):
        effect = random.choice(["size", "flip", "color", "teleport"])
        player.glitch_effect_timer = 2.5 + self.rage * 2.5
        
        if effect == "size":
            player.glitch_size_factor = random.choice([0.4, 2.5])
        elif effect == "flip":
            player.glitch_flip_y = True
        elif effect == "color":
            player.glitch_color_override = skia.Color(random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        elif effect == "teleport":
            player.body.position += Vec2(random.uniform(-300, 300), random.uniform(-300, 300))
            particles.emit(player.body.position, 25, skia.Color(255, 0, 255))
        
        audio.play("shock", volume=0.7)
        particles.emit(player.body.position, 20, skia.Color(0, 255, 0))

    def explode_attack(self, atk, particles, audio):
        # Matrix green bits and smoke
        particles.emit(atk['pos'], 25, skia.Color(50, 255, 50), speed_range=(50, 300), life_range=(0.6, 1.2))
        particles.emit(atk['pos'], 15, skia.Color(150, 150, 150, 120), speed_range=(20, 80), life_range=(1.0, 2.5))
        audio.play("hitWall", volume=0.4)
        if atk in self.attacks:
            self.attacks.remove(atk)

    def _dist_point_to_segment(self, p, a, b):
        l2 = (a - b).length_squared()
        if l2 == 0: return (p - a).length()
        t = max(0, min(1, (p - a).dot(b - a) / l2))
        projection = a + (b - a) * t
        return (p - projection).length()

    def freeze(self, duration: float):
        self.freeze_timer = duration
        self.rage_boost -= 0.4 # Significantly decrease rage boost
        if self.rage_boost < -0.5: self.rage_boost = -0.5

    def render(self, canvas: skia.Canvas, particles):
        if self.is_dead:
            return
            
        pos = self.body.position
        # Broken cloud appearance
        paint = skia.Paint(AntiAlias=True)
        
        if self.freeze_timer > 0:
            paint.setColor(skia.Color(150, 200, 255, 180))
        else:
            r = int(100 + self.rage * 155)
            g = int(100 - self.rage * 50)
            b = int(200 - self.rage * 100)
            paint.setColor(skia.Color(r, g, b, 180))

        # Main circles - more chaotic with rage
        num_circles = 6 + int(self.rage * 4)
        for i in range(num_circles):
            off = Vec2(math.sin(self.anim_t + i) * (30 + self.rage * 20), 
                       math.cos(self.anim_t * 0.7 + i) * (20 + self.rage * 15))
            canvas.drawCircle(pos.x + off.x, pos.y + off.y, self.r * (0.8 + math.sin(self.anim_t * 2 + i) * 0.2), paint)
            
        # Glitchy bits
        if not self.freeze_timer > 0:
            bit_paint = skia.Paint(Color=skia.ColorWHITE)
            for _ in range(int(8 + self.rage * 20)):
                bx = pos.x + random.uniform(-self.r * 1.5, self.r * 1.5)
                by = pos.y + random.uniform(-self.r * 1.5, self.r * 1.5)
                bw = random.uniform(5, 20)
                canvas.drawRect(skia.Rect.MakeXYWH(bx, by, bw, bw), bit_paint)

        # Render attacks (Arrows)
        atk_paint = skia.Paint(Color=skia.Color(0, 255, 0), StrokeWidth=3, Style=skia.Paint.kStroke_Style)
        glow_paint = skia.Paint(
            Color=skia.Color(50, 255, 50, 150),
            StrokeWidth=10,
            Style=skia.Paint.kStroke_Style,
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4)
        )
        trail_font = skia.Font(skia.Typeface.MakeDefault(), 16)
        trail_paint = skia.Paint(Color=skia.Color(0, 255, 0, 180), AntiAlias=True)

        for atk in self.attacks:
            # Draw trail text
            for t in atk['trail']:
                trail_paint.setAlpha(int(255 * (t['life'] / 0.6)))
                canvas.drawString(t['char'], t['pos'].x, t['pos'].y, trail_font, trail_paint)
            
            # Arrow with glow
            canvas.drawLine(atk['pos'].x, atk['pos'].y, atk['pos'].x - atk['vel'].x * 0.06, atk['pos'].y - atk['vel'].y * 0.06, glow_paint)
            canvas.drawLine(atk['pos'].x, atk['pos'].y, atk['pos'].x - atk['vel'].x * 0.06, atk['pos'].y - atk['vel'].y * 0.06, atk_paint)

        # Render Noise Rays
        for ray in self.noise_rays:
            alpha_val = ray['timer'] / ray['max_t']
            alpha = int(200 * alpha_val)
            
            # Vibrant pulse/flicker
            ray_color = skia.Color(100, 255, 100, alpha) if random.random() > 0.2 else skia.ColorWHITE
            
            ray_paint = skia.Paint(
                Color=ray_color,
                StrokeWidth=12 + math.sin(self.anim_t * 20) * 4,
                MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6)
            )
            canvas.drawLine(ray['start'].x, ray['start'].y, ray['end'].x, ray['end'].y, ray_paint)
            
            # Inner ray - use a fresh paint to avoid filter carryover
            inner_ray_paint = skia.Paint(
                Color=skia.Color(200, 255, 200, alpha),
                StrokeWidth=3,
                AntiAlias=True
            )
            canvas.drawLine(ray['start'].x, ray['start'].y, ray['end'].x, ray['end'].y, inner_ray_paint)
            
            # Particle effects at ends
            if random.random() < 0.3:
                particles.emit(ray['end'], 1, skia.Color(100, 255, 100), speed_range=(10, 50))