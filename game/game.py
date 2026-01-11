import math
import random
import glfw
import skia
from engine.collision import CollisionWorld
from engine.component import Component, EventType
from engine.effects import PostProcessSystem
from engine.particles import ParticleSystem
from engine.physics import PhysicsWorld, Vec2
from engine.sound import SoundManager
from game.effects import CorruptionManager
from game.enemies import EnemyManager
from game.intro import IntroManager
from game.items import ItemManager
from game.level import Door, LevelManager, Platform
from game.player import MemoryPlayer
from game.ui import UIManager

class GameState:
    INTRO = 0
    PLAYING = 1
    SHATTERING = 2
    TRANSITIONING = 3
    VOID = 4
    BOSS_DEATH = 5
    CREDITS = 6
    ART_SCENE = 7

class MemoryParasiteGame(Component):
    DEBUG_PROD = True

    def __init__(self):
        super().__init__("MemoryParasite")
        self.w, self.h = 1280, 720
        self.state = GameState.INTRO
        self.prev_state = GameState.PLAYING
        self.loss_iteration = 0
        self.world_corruption = 0.0
        self.is_in_glitched_world = False
        self.threshold_50_triggered = False

        self.particles = ParticleSystem()
        self.phys = PhysicsWorld(gravity=Vec2(0, 0))
        self.coll = CollisionWorld()
        self.items = ItemManager()
        self.level = LevelManager(self.w, self.h, self.phys, self.coll, self.items)
        self.player = MemoryPlayer(self.phys, Vec2(100, self.h - 140))
        self.enemies = EnemyManager(self.phys, self.coll)
        self.audio = SoundManager.get()
        self.ui = UIManager(self.w, self.h)
        self.intro = IntroManager(self.w, self.h, self.audio)

        self.post_process = None
        self.corruption = None
        self.keys = set()
        self.t = 0.0
        self.transition_t = 0.0
        self.target_level = ""
        self.void_door = None
        self.void_platforms = []
        self.glitch_loop_handle = None

        self.audio.load("assets/hitHurt.wav", "hitWall")
        self.audio.load("assets/explode.wav", "explode")
        self.audio.load("assets/glitchloop.wav", "glitchloop")
        self.audio.load("assets/shatter.wav", "shatter")
        self.audio.load("assets/pickupCoin.wav", "pickup")
        self.audio.load("assets/shock.wav", "shock")
        self.audio.load("assets/noise.wav", "noise")
        self.audio.load("assets/pickupFragment.wav", "pickupFragment")
        self.audio.load("assets/glitch1.wav", "glitch1")
        self.audio.load("assets/glitch2.wav", "glitch2")
        self.audio.load("assets/glitch3.wav", "glitch3")
        self.audio.load("assets/glitchloop.wav", "glitchloop_ambiance")
        self.audio.load("assets/bossAmbiance.wav", "boss_ambiance")
        self.audio.load("assets/bossdeath.wav", "boss_death_sound")
        self.audio.load("assets/glitchriser.wav", "glitch_riser")

        self.shockwaves = []
        self.sparks = []
        self.noise_handle = None
        self.ambiance_handle = None
        self.boss_ambiance_handle = None
        self.ending_glitch_handles = []
        self.riser_handle = None
        self.fragments_collected = 0
        self.rising_purge_y = 720.0
        self.last_spark_hit_timer = 0.0
        self.last_spark_hit_pos = Vec2(0, 0)
        self.visual_noise_timer = 0.0
        self.boss_death_timer = 0.0
        self.exit_door = None

    def on_init(self, ctx, canvas):
        self.ctx, self.canvas = ctx, canvas
        self.window = glfw.get_current_context()

    def _load_level(self, level_name: str):
        self.level.load_from_xml(level_name)
        self.fragments_collected = 0
        self.rising_purge_y = 720.0
        self.player.body.position = Vec2(100, self.h - 100)
        self.player.body.velocity = Vec2(0, 0)
        self.player.memory = self.player.cfg.max_mem
        self.enemies.reset_for_death()
        if self.level.boss_spawn_pos:
            self.enemies.spawn_boss(self.level.boss_spawn_pos)
        
        if level_name == "level10":
            if not self.ambiance_handle:
                self.ambiance_handle = self.audio.play("glitchloop_ambiance", volume=0.3, loop=True)
            if not self.boss_ambiance_handle:
                self.boss_ambiance_handle = self.audio.play("boss_ambiance", volume=0.5, loop=True)
        else:
            if self.ambiance_handle: self.ambiance_handle.stop(); self.ambiance_handle = None
            if self.boss_ambiance_handle: self.boss_ambiance_handle.stop(); self.boss_ambiance_handle = None

    def on_event(self, ev):
        if ev.type == EventType.KEY_PRESS:
            if ev.key == glfw.KEY_F9:
                if self.state != GameState.ART_SCENE:
                    self.prev_state = self.state
                    self.state = GameState.ART_SCENE
                else:
                    self.state = self.prev_state
                return True

            if ev.key == glfw.KEY_F4 and self.state == GameState.INTRO:
                self._load_level("level1")
                self.state = GameState.PLAYING
                return True

        if self.DEBUG_PROD and ev.type == EventType.KEY_PRESS and ev.key == glfw.KEY_F3:
            levels = ["level1", "level2", "level3", "level4", "level5", "level6", "level7", "level8", "level9", "level10", "level11"]
            try: curr_idx = levels.index(self.level.current_level_name)
            except: curr_idx = -1
            self._load_level(levels[(curr_idx + 1) % len(levels)])
            self.state = GameState.PLAYING
            return True

        if ev.type == EventType.KEY_PRESS:
            if ev.key == glfw.KEY_1 and self.player.fruits > 0:
                self.player.fruits -= 1
                self.audio.play("shock", volume=1.0)
                self.player.memory = min(self.player.cfg.max_mem, self.player.memory + self.player.cfg.max_mem * 0.7)
                self.shockwaves.append({"pos": self.player.body.position.copy(), "r": 0.0, "max_r": 1200.0})
                self.level.revive_all_platforms()
                self.enemies.kill_all(self.particles)
                return True

            if self.state in [GameState.SHATTERING, GameState.TRANSITIONING]: return False
            self.keys.add(ev.key)
        elif ev.type == EventType.KEY_RELEASE:
            self.keys.discard(ev.key)
        return False

    def _reset_with_loss(self):
        self.loss_iteration += 1
        self.is_in_glitched_world = True
        self.threshold_50_triggered = False
        self.player.memory = self.player.cfg.max_mem * 0.75
        self.player.body.position = Vec2(100, self.h - 100)
        self.player.body.velocity = Vec2(0, 0)
        self.player.apply_loss_tweak(self.loss_iteration)
        if self.glitch_loop_handle: self.glitch_loop_handle.stop()
        self.glitch_loop_handle = self.audio.play("glitchloop", volume=0.4, loop=True)

        new_platforms = []
        for p in self.level.platforms:
            if not p.is_permanent:
                p.is_lost = True
                p.x += random.uniform(-40, 40)
                p.y += random.uniform(-30, 30)
                p.orig_x, p.orig_y = p.x, p.y
            new_platforms.append(p)
        for _ in range(2 + self.loss_iteration):
            new_platforms.append(Platform(random.uniform(100, self.w-300), random.uniform(200, self.h-100), random.uniform(80, 250), 20, is_lost=True))
        self.level.platforms = new_platforms
        self.enemies.reset_for_death(keep_boss=True)
        self.state = GameState.PLAYING

    def _trigger_relay(self, r):
        if r.active: return
        r.active = True
        self.audio.play("pickup", volume=1.0)
        self.particles.emit(Vec2(r.x, r.y), 20, skia.Color(0, 255, 255))
        if all(rel.active for rel in self.level.relays):
            self.enemies.kill_all(self.particles)
            self.player.memory = self.player.cfg.max_mem
            for d in self.level.doors:
                if d.is_locked:
                    d.is_locked = False
                    self.audio.play("shatter", volume=1.0)
                    self.particles.emit(Vec2(d.x + d.w/2, d.y + d.h/2), 40, skia.Color(0, 255, 255))

    def on_update(self, dt):
        self.t += dt
        if not self.corruption and self.post_process:
            self.corruption = CorruptionManager(None, self.post_process)

        if self.state == GameState.ART_SCENE: return

        if self.state == GameState.INTRO:
            if self.intro.update(dt, self.keys, self.particles) == "FINISHED":
                self._load_level("level1")
                self.state = GameState.PLAYING
            return

        if self.state == GameState.SHATTERING:
            if self.corruption:
                self.corruption.update(dt)
                if self.corruption.shatter_timer <= 0: self._reset_with_loss()
            return

        if self.state == GameState.TRANSITIONING:
            self.transition_t += dt
            if self.transition_t >= 1.0:
                if self.target_level == "RECONSTRUCTING":
                    self.state = GameState.PLAYING
                    self.transition_t = 0
                else:
                    self.state = GameState.VOID
                    self.player.body.position = Vec2(100, self.h - 100)
                    self.player.body.velocity = Vec2(0, 0)
                    self.void_door = Door(self.w - 200, self.h - 150, target_level=self.target_level)
                    self.void_platforms = [Platform(0, self.h - 50, self.w, 50)]
            return

        if self.state == GameState.VOID:
            self.player.handle_input(self.keys)
            self.player.update_velocity(dt, self.world_corruption)
            self.phys.update(dt)
            self.player.grounded, _ = self.level.resolve_rect_vs_static(self.player.body, self.player.width, self.player.height, self.void_platforms)
            self.player.update_animation(dt)
            self.void_door.glow_t += dt
            dx, dy = self.void_door.x + self.void_door.w/2, self.void_door.y + self.void_door.h/2
            if (self.player.body.position - Vec2(dx, dy)).length() < 60:
                self._load_level(self.target_level)
                self.player.keys.clear(); self.keys.clear()
                self.state = GameState.TRANSITIONING; self.target_level = "RECONSTRUCTING"; self.transition_t = 0
                if self.is_in_glitched_world:
                    self.world_corruption += 0.15; self.is_in_glitched_world = False; self.player.memory = self.player.cfg.max_mem
                    if self.glitch_loop_handle: self.glitch_loop_handle.stop(); self.glitch_loop_handle = None
            return

        if self.state == GameState.BOSS_DEATH:
            self.boss_death_timer += dt
            vol = min(1.0, self.boss_death_timer / 5.0)
            if self.boss_death_timer < 5.0:
                if random.random() < 0.1: self.ending_glitch_handles.append(self.audio.play(random.choice(["glitch1", "glitch2", "glitch3"]), volume=vol * 0.8))
                if not self.riser_handle: self.riser_handle = self.audio.play("glitch_riser", volume=0.5)
                elif self.riser_handle: self.riser_handle.set_volume(vol * 0.7)
                self.player.body.position += Vec2(random.uniform(-5, 5), random.uniform(-5, 5)) * vol
                if self.corruption: self.corruption.trigger_glitch(vol)
            else:
                self.player.glitch_size_factor = 1.0; self.player.glitch_flip_y = False; self.player.glitch_color_override = None; self.player.glitch_effect_timer = 0.0
                self._load_level("level11")
                self.player.body.position = Vec2(50, self.h - 100); self.state = GameState.PLAYING
                if self.riser_handle: self.riser_handle.stop()
                for h in self.ending_glitch_handles: h.stop()
            return

        self.player.handle_input(self.keys)
        self.player.update_velocity(dt, self.world_corruption)
        self.phys.update(dt)
        mem_percent = self.player.memory / self.player.cfg.max_mem
        self.level.update(dt, mem_percent, self.particles, self.fragments_collected, player_x=self.player.body.position.x)

        lvl_num = 0
        try: lvl_num = int(self.level.current_level_name.replace("level", ""))
        except: pass
        self.player.weight_enabled = lvl_num >= 6

        collected_types = self.items.update(dt, self.player.body.position, self.particles)
        for typ in collected_types:
            if typ == "fruit": self.audio.play("pickup", volume=0.8); self.player.fruits += 1
            elif typ == "fragment":
                self.fragments_collected += 1; self.audio.play("pickupFragment", volume=1.0)
                for d in self.level.doors:
                    if d.is_locked:
                        d.reconstruction_percent = self.fragments_collected / 3.0
                        if self.fragments_collected >= 3:
                            d.is_locked = False; self.audio.play("shatter", volume=1.0)
                            self.particles.emit(Vec2(d.x + d.w/2, d.y + d.h/2), 40, skia.Color(150, 200, 255), speed_range=(100, 400))

        events = self.player.update_state(dt, self.level, self.particles, mem_percent, self.world_corruption, self.fragments_collected)
        if mem_percent < 0.3 and abs(self.player.body.velocity.length()) > 50 and random.random() < 0.3:
            self.particles.emit(self.player.body.position, 1, skia.Color(150, 200, 255, 100), speed_range=(10, 30), life_range=(0.3, 0.6))

        if self.level.check_standing_on_corrupted(self.player.body, self.player.width, self.player.height, mem_percent, self.fragments_collected):
            self.player.memory -= (5.0 + self.world_corruption * 20.0) * dt
            if self.corruption: self.corruption.crash_timer = 0.05

        if events.get("head_bang"):
            if self.corruption:
                self.corruption.on_headbang(); self.player.memory -= 10.0; self.audio.play("hitWall", volume=0.6, low_pass=1.0 - mem_percent)
            self.particles.emit(self.player.body.position, 10, skia.ColorWHITE)

        for d in self.level.doors:
            if (self.player.body.position - Vec2(d.x + d.w/2, d.y + d.h/2)).length() < 60:
                if d.is_locked:
                    if self.corruption: self.corruption.crash_timer = 0.05
                    continue
                if d.target_level == "EXIT":
                    if self.window: glfw.set_window_should_close(self.window, True)
                    return
                self.state = GameState.TRANSITIONING; self.target_level = d.target_level; self.transition_t = 0
                self.keys.clear(); self.player.keys.clear(); self.player.body.velocity = Vec2(0, 0)
                break

        enemy_res = self.enemies.update(dt, self.player, self.level, self.particles, self.audio)
        is_lvl10 = self.level.current_level_name == "level10"
        for dmg, pos in enemy_res['events']:
            self.player.memory -= dmg * 0.4 if is_lvl10 else dmg
            if self.corruption: self.corruption.trigger_impact_shatter(pos)
            self.audio.play("hitWall", volume=1.0, low_pass=1.0 - (self.player.memory / 100))
        
        if enemy_res.get('boss_hit'):
            if self.corruption:
                self.corruption.pp.trigger_shake(25.0)
                if self.enemies.boss: self.corruption.boss_crack_level = max(self.corruption.boss_crack_level, 1.0 - self.enemies.boss.hp / self.enemies.boss.max_hp)
                else:
                    self.corruption.boss_crack_level = 1.0; self.state = GameState.BOSS_DEATH; self.boss_death_timer = 0.0; self.audio.play("boss_death_sound", volume=1.0)
                    self.level.platforms.clear(); self.level.doors.clear(); self.level.cables.clear(); self.level.relays.clear(); self.sparks.clear(); self.enemies.enemies.clear()
                    self.player.body.position = Vec2(self.w/2, self.h-150); self.player.body.velocity = Vec2(0, 0)
                self.corruption.boss_crack_level = min(1.0, self.corruption.boss_crack_level + 0.1)
            self.audio.play(random.choice(["glitch1", "glitch2", "glitch3"]), volume=0.8)

        if is_lvl10 and not self.enemies.boss:
            if self.ambiance_handle: self.ambiance_handle.stop(); self.ambiance_handle = None
            if self.boss_ambiance_handle: self.boss_ambiance_handle.stop(); self.boss_ambiance_handle = None

        if enemy_res.get('noise_hit'):
            self.visual_noise_timer = 0.2
            if self.corruption: self.corruption.trigger_glitch(0.1)
        if self.visual_noise_timer > 0: self.visual_noise_timer -= dt

        ghost_threshold = 0.8 if self.level.current_level_name == "level8" else 0.5
        if mem_percent < ghost_threshold and not self.threshold_50_triggered:
            self.threshold_50_triggered = True
            if self.level.current_level_name in ["level2", "level8"] or random.random() < 0.7:
                spawn_pts = self.level.lose_random_platforms(random.randint(1, 2))
                if spawn_pts: self.audio.play("shatter", volume=0.8)
                for pt in spawn_pts: self.enemies.spawn_lost_ghost(pt); self.particles.emit(pt, 30, skia.Color(100, 100, 100, 150), speed_range=(50, 200))

        if self.player.memory <= 0:
            self.state = GameState.SHATTERING
            if self.corruption: self.corruption.trigger_shatter(self.loss_iteration)
            self.particles.emit(self.player.body.position, 50, skia.ColorWHITE, speed_range=(200, 500)); self.audio.play("explode", volume=1.0); self.keys.clear()

        if self.corruption: self.corruption.set_corruption(mem_percent); self.corruption.update(dt)

        if mem_percent < 0.2:
            noise_vol = (0.2 - mem_percent) / 0.2 * 0.5
            if not self.noise_handle: self.noise_handle = self.audio.play("noise", volume=noise_vol, loop=True)
            else: self.noise_handle.set_volume(noise_vol)
        elif self.noise_handle: self.noise_handle.stop()

        if self.level.current_level_name == "level8":
            if not all(r.active for r in self.level.relays): self.rising_purge_y -= 8.0 * dt
            if self.player.body.position.y > self.rising_purge_y:
                self.player.memory -= 25.0 * dt
                if self.corruption: self.corruption.crash_timer = 0.05
                if random.random() < 0.2: self.particles.emit(self.player.body.position, 2, skia.Color(255, 0, 255))

        if self.last_spark_hit_timer > 0: self.last_spark_hit_timer -= dt

        for r in self.level.relays:
            if not r.active:
                if r.type == "ghost":
                    for e in self.enemies.enemies:
                        if (e.body.position - Vec2(r.x, r.y)).length() < 150: self._trigger_relay(r); break
                if r.active: continue
                if (self.player.body.position - Vec2(r.x, r.y)).length() < 50:
                    if (r.type == "weight" and mem_percent > 0.8) or (r.type == "spark" and self.last_spark_hit_timer > 0): self._trigger_relay(r)

        for c in self.level.cables:
            if c.timer <= 0:
                c.timer = random.uniform(1.5, 3.5)
                angle = math.atan2(self.player.body.position.y - c.length, self.player.body.position.x - c.x) + random.uniform(-0.5, 0.5) if random.random() < 0.5 else random.uniform(0, math.pi)
                self.sparks.append({"pos": Vec2(c.x, c.length), "vel": Vec2(math.cos(angle) * random.uniform(250, 450), math.sin(angle) * random.uniform(250, 450))})

        for s in self.sparks[:]:
            s["pos"] += s["vel"] * dt; s["vel"].y += 500 * dt
            if random.random() < 0.2: self.particles.emit(s["pos"], 1, skia.Color(255, 100, 0), speed_range=(10, 30))
            if (s["pos"] - self.player.body.position).length() < 30:
                self.player.memory -= 30.0; self.last_spark_hit_timer = 0.5
                if self.corruption: self.corruption.crash_timer = 0.2; self.corruption.trigger_glitch(0.5)
                self.particles.emit(s["pos"], 20, skia.Color(255, 150, 0), speed_range=(100, 300)); self.audio.play("hitWall", volume=0.8); self.sparks.remove(s); continue
            hit_p = False
            for p in self.level.platforms:
                if p.x < s["pos"].x < p.x + p.w and p.y < s["pos"].y < p.y + p.h:
                    p.temp_corrupt_t = 0.7; self.particles.emit(s["pos"], 15, skia.Color(255, 100, 0), speed_range=(50, 150)); hit_p = True
                    for r in self.level.relays:
                        if r.type == "spark" and not r.active and (s["pos"] - Vec2(r.x, r.y)).length() < 100: self._trigger_relay(r)
                    break
            if hit_p or s["pos"].y > self.h or s["pos"].x < 0 or s["pos"].x > self.w:
                if s in self.sparks: self.sparks.remove(s)

        for c in self.level.cables:
            if (self.player.body.position - Vec2(c.x, c.length)).length() < 45:
                self.player.memory -= 40.0 * dt
                if random.random() < dt * 12:
                    self.player.memory -= 8.0; self.player.body.velocity = (self.player.body.position - Vec2(c.x, c.length)).normalized() * 800
                    self.audio.play("hitWall", volume=1.0)
                    if self.corruption: self.corruption.crash_timer = 0.15
                    self.particles.emit(Vec2(c.x, c.length), 15, skia.Color(255, 50, 0))

        for sw in self.shockwaves[:]:
            old_r = sw["r"]; sw["r"] += 1500 * dt
            if sw["r"] > sw["max_r"]: self.shockwaves.remove(sw)
            else:
                for e in self.enemies.enemies:
                    if old_r < (e.body.position - sw["pos"]).length() <= sw["r"]: self.particles.emit(e.body.position, 10, skia.Color(100, 200, 255), speed_range=(20, 100), size_range=(2, 5))
                for p in self.level.platforms:
                    if old_r < (Vec2(p.x + p.w/2, p.y + p.h/2) - sw["pos"]).length() <= sw["r"] and (p.is_lost or p.memory_req is not None):
                        self.particles.emit(Vec2(p.x + p.w/2, p.y + p.h/2), 15, skia.Color(150, 200, 255), speed_range=(10, 80))

        self.particles.update(dt)
        if self.player.body.position.y > self.h + 100: self.player.body.position = Vec2(100, self.h - 100); self.player.body.velocity = Vec2(0, 0)

    def _render_art_scene(self, canvas):
        canvas.clear(skia.Color(10, 10, 10))
        font = skia.Font(self.level.typeface, 120); paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
        random.seed(int(self.t * 10))
        for i, line in enumerate(["MEMORY", "PARASITE"]):
            for _ in range(3):
                ox, oy = random.uniform(-5, 5), random.uniform(-2, 2)
                paint.setColor(skia.ColorRED if random.random() > 0.7 else skia.ColorCYAN if random.random() > 0.7 else skia.ColorWHITE)
                canvas.drawString(line, 100 + ox, 250 + i * 150 + oy, font, paint)
        random.seed(); canvas.save(); canvas.translate(self.w * 0.75, self.h / 2); canvas.scale(2.0, 2.0); self.player.render_at(canvas, Vec2(0, 0)); canvas.restore()

    def on_render_ui(self, canvas):
        if self.state == GameState.ART_SCENE: self._render_art_scene(canvas); return
        if self.state == GameState.BOSS_DEATH: canvas.clear(skia.ColorBLACK); self.player.render(canvas); return
        
        canvas.clear(skia.Color(10, 10, 10))
        if self.state == GameState.INTRO: self.intro.render(canvas, self.player); return
        if self.state == GameState.SHATTERING and self.corruption: self.corruption.render_shatter(canvas, self.w, self.h); return
        if self.state == GameState.TRANSITIONING:
            canvas.clear(skia.ColorBLACK); progress = min(1.0, self.transition_t)
            if self.target_level == "RECONSTRUCTING":
                canvas.save(); canvas.clipRect(skia.Rect.MakeXYWH(0, 0, self.w, progress * self.h))
                self.level.render(canvas, self.t, 1.0, self.particles, self.world_corruption, self.is_in_glitched_world, True, self.fragments_collected)
                self.player.render(canvas); canvas.restore(); canvas.drawRect(skia.Rect.MakeXYWH(0, progress * self.h, self.w, 4), skia.Paint(Color=skia.ColorWHITE))
            else:
                h_s, w_s = max(0.001, 1.0 - progress * 1.5), 1.0 if progress < 0.5 else max(0.001, 1.0 - (progress - 0.5) * 2.0)
                canvas.drawRect(skia.Rect.MakeXYWH(self.w/2 - (self.w*w_s)/2, self.h/2 - (self.h*h_s)/2, self.w*w_s, self.h*h_s), skia.Paint(Color=skia.ColorWHITE))
            return
        if self.state == GameState.VOID:
            canvas.clear(skia.ColorBLACK)
            if self.corruption: self.corruption.render_void_text(canvas, f"level {self.level.current_level_name.replace('level', '')}", self.w, self.h)
            d, gs = self.void_door, 5 + math.sin(self.void_door.glow_t * 5) * 3
            canvas.drawRect(skia.Rect.MakeXYWH(d.x-gs, d.y-gs, d.w+gs*2, d.h+gs*2), skia.Paint(Color=skia.Color(0, 255, 255, 100), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, gs)))
            canvas.drawRect(skia.Rect.MakeXYWH(d.x, d.y, d.w, d.h), skia.Paint(Color=skia.Color(0, 50, 50, 200))); canvas.drawRect(skia.Rect.MakeXYWH(d.x+10, d.y+10, d.w-20, d.h-20), skia.Paint(Color=skia.Color(0, 200, 200, 255))); self.player.render(canvas); return

        canvas.save()
        self.level.render(canvas, self.t, self.player.memory/self.player.cfg.max_mem, self.particles, self.world_corruption, self.is_in_glitched_world, self.is_in_glitched_world, self.fragments_collected)
        self.enemies.render(canvas, self.particles); self.player.render(canvas); self.particles.render(canvas)
        for d in self.level.doors:
            if d.target_level == "EXIT":
                exit_font = skia.Font(self.level.typeface, 24); canvas.drawString("Exit", d.x + d.w/2 - exit_font.measureText("Exit")/2, d.y - 20, exit_font, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
        if self.level.current_level_name == "level8":
            canvas.drawRect(skia.Rect.MakeXYWH(0, self.rising_purge_y, self.w, self.h - self.rising_purge_y + 100), skia.Paint(Color=skia.Color(255, 0, 255, 100), Style=skia.Paint.kFill_Style))
            canvas.drawLine(0, self.rising_purge_y, self.w, self.rising_purge_y, skia.Paint(Color=skia.Color(255, 255, 255, 150), StrokeWidth=2))
            for _ in range(5): canvas.drawLine(0, self.rising_purge_y + random.uniform(0, 50), self.w, self.rising_purge_y + random.uniform(0, 50), skia.Paint(Color=skia.Color(255, 0, 255, 50), StrokeWidth=1))
        
        sp = skia.Paint(Color=skia.Color(255, 200, 0), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
        for s in self.sparks:
            sp.setColor(skia.Color(255, 50, 0) if random.random() < 0.3 else skia.Color(255, 200, 0))
            canvas.drawCircle(s["pos"].x, s["pos"].y, 6, sp); canvas.drawCircle(s["pos"].x, s["pos"].y, 3, skia.Paint(Color=skia.ColorWHITE))
        for sw in self.shockwaves:
            alpha = int(255 * (1.0 - sw["r"] / sw["max_r"]))
            canvas.drawCircle(sw["pos"].x, sw["pos"].y, sw["r"], skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=15, Color=skia.Color(255, 200, 100, alpha), AntiAlias=True, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)))
            canvas.drawCircle(sw["pos"].x, sw["pos"].y, sw["r"], skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color=skia.Color(255, 200, 100, alpha), AntiAlias=True))

        self.ui.render(canvas, self.player.memory, self.player.cfg.max_mem, self.player.fruits)
        if self.corruption: self.corruption.render_vignette(canvas, self.w, self.h); self.corruption.render_cracks(canvas, self.w, self.h); self.corruption.render_crash(canvas, self.w, self.h); self.corruption.render_impact_shatter(canvas); self.corruption.render_shatter(canvas, self.w, self.h)
        if self.visual_noise_timer > 0:
            noise_pa = skia.Paint(Color=skia.Color(255, 255, 255, 100))
            for _ in range(20): canvas.drawRect(skia.Rect.MakeXYWH(random.uniform(0, self.w), random.uniform(0, self.h), random.uniform(50, 200), random.uniform(2, 10)), noise_pa)
        canvas.restore()