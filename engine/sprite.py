import math
from dataclasses import dataclass

import skia

from engine.physics import Vec2


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float


class Sprite:
    def __init__(self, image: skia.Image, src_rect: Rect | None = None):
        self.image = image
        self.src_rect = src_rect
        self.anchor = Vec2(0.5, 0.5)  # Normalized anchor point (0.5, 0.5 is center)
        self.scale = Vec2(1.0, 1.0)
        self.rotation = 0.0  # Radians
        self.flip_x = False
        self.flip_y = False
        self.color = skia.ColorWHITE  # Tint
        self.alpha = 1.0

    def render(self, canvas: skia.Canvas, pos: Vec2):
        if not self.image:
            return

        w = self.src_rect.w if self.src_rect else self.image.width()
        h = self.src_rect.h if self.src_rect else self.image.height()

        canvas.save()
        canvas.translate(pos.x, pos.y)
        canvas.rotate(math.degrees(self.rotation))

        sx = -self.scale.x if self.flip_x else self.scale.x
        sy = -self.scale.y if self.flip_y else self.scale.y
        canvas.scale(sx, sy)

        # Calculate offset based on anchor
        dx = -w * self.anchor.x
        dy = -h * self.anchor.y

        # Paint for tint/alpha
        paint = skia.Paint(AntiAlias=True)
        paint.setAlphaf(self.alpha)
        # Note: Skia's simple drawImage doesn't easily support full tinting without shaders or filters,
        # but we can do alpha. For color tinting, we'd need a ColorFilter.
        if self.color != skia.ColorWHITE:
            paint.setColorFilter(
                skia.ColorFilters.Blend(self.color, skia.BlendMode.kModulate)
            )

        if self.src_rect:
            src = skia.Rect(
                self.src_rect.x,
                self.src_rect.y,
                self.src_rect.x + self.src_rect.w,
                self.src_rect.y + self.src_rect.h,
            )
            dst = skia.Rect(dx, dy, dx + w, dy + h)
            canvas.drawImageRect(self.image, src, dst, paint)
        else:
            canvas.drawImage(self.image, dx, dy, skia.SamplingOptions(), paint)

        canvas.restore()


class PositionedSprite(Sprite):
    def __init__(
        self,
        image: skia.Image,
        position: Vec2 = Vec2(0, 0),
        src_rect: Rect | None = None,
    ):
        super().__init__(image, src_rect)
        self.position = position

    def render(self, canvas: skia.Canvas, pos: Vec2 | None = None):
        render_pos = pos if pos is not None else self.position
        super().render(canvas, render_pos)


class AnimatedSprite(Sprite):
    def __init__(
        self,
        image: skia.Image,
        frame_width: int,
        frame_height: int,
        frame_duration: float = 0.1,
    ):
        super().__init__(image)
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.frame_duration = frame_duration

        self.cols = image.width() // frame_width
        self.rows = image.height() // frame_height
        self.total_frames = self.cols * self.rows

        self.current_frame = 0
        self.timer = 0.0
        self.playing = True
        self.loop = True

        self.animations = {}  # name -> (start_frame, end_frame)
        self.current_anim = None

        self._update_src_rect()

    def add_animation(self, name: str, frames: list):
        """Frames can be a range or list of indices"""
        self.animations[name] = frames

    def play(self, name: str, loop: bool = True):
        if name not in self.animations:
            return
        if self.current_anim == name and self.playing:
            return

        self.current_anim = name
        self.loop = loop
        self.current_frame = 0  # Index relative to animation list
        self.playing = True
        self.timer = 0.0
        self._update_src_rect()

    def update(self, dt: float):
        if not self.playing:
            return

        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer = 0.0

            if self.current_anim:
                frames = self.animations[self.current_anim]
                self.current_frame += 1
                if self.current_frame >= len(frames):
                    if self.loop:
                        self.current_frame = 0
                    else:
                        self.current_frame = len(frames) - 1
                        self.playing = False
                frame_idx = frames[self.current_frame]
            else:
                # Default linear
                self.current_frame = (self.current_frame + 1) % self.total_frames
                frame_idx = self.current_frame

            self._update_src_rect_by_index(frame_idx)

    def _update_src_rect(self):
        if self.current_anim:
            idx = self.animations[self.current_anim][self.current_frame]
        else:
            idx = self.current_frame
        self._update_src_rect_by_index(idx)

    def _update_src_rect_by_index(self, idx: int):
        c = idx % self.cols
        r = idx // self.cols
        self.src_rect = Rect(
            c * self.frame_width,
            r * self.frame_height,
            self.frame_width,
            self.frame_height,
        )
