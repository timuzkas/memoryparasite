import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import glfw
import skia

from engine.assets import AssetManager
from engine.physics import PhysicsWorld, RigidBody, Vec2
from engine.sprite import Sprite


class PlayerState(Enum):
    IDLE = auto()
    RUNNING = auto()
    JUMPING = auto()
    DASHING = auto()


@dataclass
class PlayerConfig:
    r: float = 16.0
    spd: float = 300.0
    jump: float = 700.0
    max_mem: float = 100.0

    col_width: float = 7.0
    col_height: float = 9.5
    visual_offset: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    
    dash_spd: float = 800.0
    dash_duration: float = 0.2
    dash_cooldown: float = 0.8


class MemoryPlayer:
    debug_mode = False
    _f1_pressed = False

    def __init__(self, phys: PhysicsWorld, start_pos: Vec2):
        self.body = RigidBody(position=start_pos, mass=1.0, drag=0.0, restitution=0.0)
        phys.add_body(self.body)

        self.cfg = PlayerConfig()
        self.scale = Vec2(6.0, 6.0)
        self.state = PlayerState.IDLE
        self.grounded = False
        self.facing_r = True
        self.keys = set()
        self.memory = self.cfg.max_mem
        self.loss_iteration = 0
        self.fruits = 0
        self.alpha = 1.0
        self.weight_enabled = False
        
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.is_dashing = False

        # Glitch effects from Boss
        self.glitch_size_factor = 1.0
        self.glitch_flip_y = False
        self.glitch_color_override = None
        self.glitch_effect_timer = 0.0

        self.width = self.cfg.col_width
        self.height = self.cfg.col_height
        self.cfg.col_height = self.cfg.col_height * self.scale.y
        self.cfg.col_width = self.cfg.col_width * self.scale.x

        spritesheet = AssetManager.get().load_spritesheet(
            "assets/player.png", frame_w=16, frame_h=16, offset=1, key="player"
        )
        self.spritesheet = spritesheet

        self.animation_frame = 0
        self.anim_timer = 0.0
        self.audio = AssetManager.get()
        self.audio.load_sound("assets/step.wav", "step")

    @classmethod
    def toggle_debug(cls):
        cls.debug_mode = not cls.debug_mode
        print(f"[DEBUG] Collision visualization: {'ON' if cls.debug_mode else 'OFF'}")

    def handle_input(self, keys: set):
        if glfw.KEY_F1 in keys and not MemoryPlayer._f1_pressed:
            MemoryPlayer.toggle_debug()
            MemoryPlayer._f1_pressed = True
        if glfw.KEY_F1 not in keys:
            MemoryPlayer._f1_pressed = False

        if (glfw.KEY_LEFT_SHIFT in keys or glfw.KEY_RIGHT_SHIFT in keys) and self.dash_cooldown <= 0:
            self.is_dashing = True
            self.dash_timer = self.cfg.dash_duration
            self.dash_cooldown = self.cfg.dash_cooldown
        self.keys = keys

    def update_velocity(self, dt: float, world_corruption: float = 0.0):
        self.width = self.cfg.col_width
        self.height = self.cfg.col_height

        if self.dash_cooldown > 0: self.dash_cooldown -= dt

        if self.is_dashing:
            self.dash_timer -= dt
            self.body.velocity.x = (self.cfg.dash_spd if self.facing_r else -self.cfg.dash_spd)
            self.body.velocity.y = 0 
            if self.dash_timer <= 0: self.is_dashing = False
            return

        mem_factor = 1.0 - (self.memory / self.cfg.max_mem)
        mem_percent = self.memory / self.cfg.max_mem
        actual_spd = self.cfg.spd * (1.0 + mem_factor * 0.5)

        move_dir = 0
        if glfw.KEY_A in self.keys or glfw.KEY_LEFT in self.keys: move_dir -= 1
        if glfw.KEY_D in self.keys or glfw.KEY_RIGHT in self.keys: move_dir += 1

        if world_corruption > 0.1:
            if random.random() < world_corruption * 0.05:
                move_dir *= -1

        if move_dir != 0:
            self.body.velocity.x = move_dir * actual_spd
            self.facing_r = move_dir > 0
        else:
            self.body.velocity.x *= 0.8
            if abs(self.body.velocity.x) < 5: self.body.velocity.x = 0

        if (glfw.KEY_W in self.keys or glfw.KEY_SPACE in self.keys) and self.grounded:
            jump_force = self.cfg.jump
            if self.weight_enabled:
                if mem_percent > 0.8: jump_force *= 0.7 # Heavy jump
                elif mem_percent < 0.3: jump_force *= 1.3 # Light jump
            self.body.velocity.y = -jump_force
            self.grounded = False

        gravity = 980
        if self.weight_enabled and mem_percent < 0.3: gravity *= 0.5 # Floaty fall
        
        self.body.velocity.y += gravity * dt
        if self.body.velocity.y > 800: self.body.velocity.y = 800

    def update_animation(self, dt: float):
        self.anim_timer += dt
        
        # Memory Weight Visuals
        mem_percent = self.memory / self.cfg.max_mem
        if self.weight_enabled:
            if mem_percent > 0.8: # HEAVY
                self.scale = Vec2(7.0, 7.0)
                self.alpha = 1.0
            elif mem_percent < 0.3: # LIGHT
                self.scale = Vec2(5.0, 5.0)
                self.alpha = 0.6
            else: # NORMAL
                self.scale = Vec2(6.0, 6.0)
                self.alpha = 1.0
        else:
            self.scale = Vec2(6.0, 6.0)
            self.alpha = 1.0

        new_frame = self.animation_frame
        if self.is_dashing:
            self.state = PlayerState.DASHING
            new_frame = 1 
        elif not self.grounded:
            self.state = PlayerState.JUMPING
            new_frame = 3
        elif abs(self.body.velocity.x) > 10:
            self.state = PlayerState.RUNNING
            new_frame = 1 if (int(self.anim_timer * 10) % 2 == 0) else 0
        else:
            self.state = PlayerState.IDLE
            new_frame = 2
        if self.state == PlayerState.RUNNING and new_frame != self.animation_frame:
            self.audio.play_sound("step", volume=0.3)
        self.animation_frame = new_frame

    def update_state(self, dt: float, level_manager, particles, mem_percent: float, world_corruption: float = 0.0, fragments_collected: int = 0) -> dict:
        events = {"impact": 0.0, "head_bang": False}
        self.grounded, hit_ceiling = level_manager.resolve_level_collision(
            self.body, self.width, self.height, mem_percent, world_corruption, fragments_collected
        )
        if hit_ceiling: events["head_bang"] = True
        self.update_animation(dt)
        self.memory -= 1.0 * dt

        if self.glitch_effect_timer > 0:
            self.glitch_effect_timer -= dt
            if self.glitch_effect_timer <= 0:
                self.glitch_size_factor = 1.0
                self.glitch_flip_y = False
                self.glitch_color_override = None

        return events

    def render(self, canvas: skia.Canvas):
        self.render_at(canvas, self.body.position, flip=not self.facing_r)

    def render_at(self, canvas: skia.Canvas, pos: Vec2, flip: bool = False):
        if self.spritesheet is not None:
            frame_image = self.spritesheet.get_frame(self.animation_frame)
            if frame_image is not None:
                sprite = Sprite(frame_image)
                sprite.scale = Vec2(self.scale.x * self.glitch_size_factor, self.scale.y * self.glitch_size_factor)
                sprite.alpha = self.alpha
                
                if self.glitch_color_override:
                    sprite.color = self.glitch_color_override
                elif self.loss_iteration > 0:
                    r = max(0, 255 - self.loss_iteration * 20)
                    sprite.color = skia.Color(255, r, r) 
                    sprite.alpha = min(self.alpha, max(0.4, 1.0 - self.loss_iteration * 0.05))
                
                if self.is_dashing:
                    sprite.color = skia.Color(100, 200, 255)
                    sprite.alpha = 0.7
                
                canvas.save()
                canvas.translate(pos.x + self.cfg.visual_offset.x, pos.y + self.cfg.visual_offset.y)
                if flip: canvas.scale(-1, 1)
                if self.glitch_flip_y: canvas.scale(1, -1)
                sprite.render(canvas, Vec2(0, 0))
                canvas.restore()
        else: self._render_fallback(canvas, pos)
        if MemoryPlayer.debug_mode: self._render_debug_overlay(canvas, pos)

    def _render_fallback(self, canvas: skia.Canvas, pos: Vec2):
        canvas.drawRect(skia.Rect.MakeXYWH(pos.x - self.width / 2, pos.y - self.height / 2, self.width, self.height), skia.Paint(Color=skia.ColorRED))

    def _render_debug_overlay(self, canvas: skia.Canvas, pos: Vec2):
        canvas.drawRect(skia.Rect.MakeXYWH(pos.x - self.width / 2, pos.y - self.height / 2, self.width, self.height), skia.Paint(Color=skia.ColorGREEN, Style=skia.Paint.kStroke_Style, StrokeWidth=2))
        canvas.drawCircle(pos.x, pos.y, 4, skia.Paint(Color=skia.ColorRED))
        vel = self.body.velocity
        if abs(vel.x) > 1 or abs(vel.y) > 1:
            canvas.drawLine(pos.x, pos.y, pos.x + vel.x * 0.1, pos.y + vel.y * 0.1, skia.Paint(Color=skia.ColorYELLOW, StrokeWidth=2))
        font, text_paint = skia.Font(None, 12), skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
        info = [f"Grounded: {self.grounded}", f"State: {self.state.name}", f"Pos: ({pos.x:.0f}, {pos.y:.0f})"]
        for i, line in enumerate(info): canvas.drawString(line, pos.x + self.width / 2 + 5, pos.y - 20 + i * 14, font, text_paint)

    def apply_loss_tweak(self, iteration: int):
        self.loss_iteration = iteration
        self.cfg.spd *= 0.98 
        self.cfg.jump *= 1.02
        self.scale.x *= random.uniform(0.98, 1.02)
        self.scale.y *= random.uniform(0.98, 1.02)
