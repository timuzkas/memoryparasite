import math, skia
from dataclasses import dataclass
from engine.physics import Vec2

@dataclass
class Rect: x: float; y: float; w: float; h: float

class Sprite:
    def __init__(self, image, src_rect=None):
        self.image, self.src_rect = image, src_rect
        self.anchor, self.scale = Vec2(0.5, 0.5), Vec2(1.0, 1.0)
        self.rotation, self.flip_x, self.flip_y = 0.0, False, False
        self.color, self.alpha = skia.ColorWHITE, 1.0

    def render(self, canvas, pos):
        if not self.image: return
        w = self.src_rect.w if self.src_rect else self.image.width()
        h = self.src_rect.h if self.src_rect else self.image.height()
        canvas.save()
        canvas.translate(pos.x, pos.y); canvas.rotate(math.degrees(self.rotation))
        canvas.scale(-self.scale.x if self.flip_x else self.scale.x, -self.scale.y if self.flip_y else self.scale.y)
        dx, dy = -w * self.anchor.x, -h * self.anchor.y
        pa = skia.Paint(AntiAlias=True); pa.setAlphaf(self.alpha)
        if self.color != skia.ColorWHITE: pa.setColorFilter(skia.ColorFilters.Blend(self.color, skia.BlendMode.kModulate))
        if self.src_rect:
            src = skia.Rect(self.src_rect.x, self.src_rect.y, self.src_rect.x + self.src_rect.w, self.src_rect.y + self.src_rect.h)
            canvas.drawImageRect(self.image, src, skia.Rect(dx, dy, dx + w, dy + h), pa)
        else: canvas.drawImage(self.image, dx, dy, skia.SamplingOptions(), pa)
        canvas.restore()

class PositionedSprite(Sprite):
    def __init__(self, image, pos=Vec2(0, 0), src_rect=None):
        super().__init__(image, src_rect); self.position = pos
    def render(self, canvas, pos=None): super().render(canvas, pos if pos else self.position)

class AnimatedSprite(Sprite):
    def __init__(self, image, frame_w, frame_h, frame_dur=0.1):
        super().__init__(image); self.frame_width, self.frame_height, self.frame_duration = frame_w, frame_h, frame_dur
        self.cols, self.rows = image.width() // frame_w, image.height() // frame_h
        self.total_frames = self.cols * self.rows; self.current_frame, self.timer, self.playing, self.loop = 0, 0.0, True, True
        self.animations, self.current_anim = {}, None; self._update_src_rect()

    def add_animation(self, name, frames): self.animations[name] = frames
    def play(self, name, loop=True):
        if name not in self.animations or (self.current_anim == name and self.playing): return
        self.current_anim, self.loop, self.current_frame, self.playing, self.timer = name, loop, 0, True, 0.0
        self._update_src_rect()

    def update(self, dt):
        if not self.playing: return
        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer = 0.0
            if self.current_anim:
                f = self.animations[self.current_anim]
                self.current_frame += 1
                if self.current_frame >= len(f):
                    if self.loop: self.current_frame = 0
                    else: self.current_frame = len(f) - 1; self.playing = False
                idx = f[self.current_frame]
            else: self.current_frame = (self.current_frame + 1) % self.total_frames; idx = self.current_frame
            self._update_src_rect_by_idx(idx)

    def _update_src_rect(self): self._update_src_rect_by_idx(self.animations[self.current_anim][self.current_frame] if self.current_anim else self.current_frame)
    def _update_src_rect_by_idx(self, idx):
        c, r = idx % self.cols, idx // self.cols
        self.src_rect = Rect(c * self.frame_width, r * self.frame_height, self.frame_width, self.frame_height)