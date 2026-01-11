import random
import skia
import math
from engine.effects import PostProcessSystem
from engine.physics import Vec2

class CorruptionManager:
    def __init__(self, engine, post_process: PostProcessSystem):
        self.engine = engine
        self.pp = post_process
        self.corruption_level = 0.0 # 0.0 to 1.0
        self.memory_percent = 1.0
        self.crash_timer = 0.0
        self.shatter_timer = 0.0
        self.is_shattered = False
        self.impact_shatter_timer = 0.0
        self.impact_pos = Vec2(0, 0)
        self.loss_iteration = 0
        self.boss_crack_level = 0.0 # 0.0 to 1.0
        
    def update(self, dt: float):
        self.pp.update(dt)
        if self.crash_timer > 0:
            self.crash_timer -= dt
        if self.shatter_timer > 0:
            self.shatter_timer -= dt
        if self.impact_shatter_timer > 0:
            self.impact_shatter_timer -= dt
        
        # Slowly decay boss cracks if they were a burst
        # But we'll mostly use it as a permanent HP-based value + burst
        
        if self.memory_percent < 0.5 and self.shatter_timer <= 0:
            chance = (0.5 - self.memory_percent) * 2.0 
            if random.random() < chance * dt * 3:
                 self.crash_timer = 0.05
        
    def on_headbang(self):
        self.pp.trigger_shake(20.0)
        self.pp.trigger_glitch(0.8) 
        self.crash_timer = 0.15 

    def trigger_glitch(self, intensity: float):
        self.pp.trigger_glitch(intensity)

    def trigger_impact_shatter(self, pos: Vec2):
        self.impact_shatter_timer = 0.3
        self.impact_pos = pos.copy()
        self.pp.trigger_shake(15.0)
        self.pp.trigger_glitch(0.5)
        
    def trigger_shatter(self, iteration: int):
        self.is_shattered = True
        self.shatter_timer = 3.5 
        self.loss_iteration = iteration
        self.pp.trigger_glitch(1.0)
        self.pp.trigger_shake(40.0)

    def set_corruption(self, memory_percent: float):
        self.memory_percent = memory_percent
        if memory_percent < 0.75:
            self.corruption_level = (0.75 - memory_percent) / 0.65
        else:
            self.corruption_level = 0.0
        self.corruption_level = max(0.0, min(1.0, self.corruption_level))
        intensity = self.corruption_level
        if memory_percent < 0.1: intensity = 1.0
        self.pp.glitch = intensity

    def render_vignette(self, canvas: skia.Canvas, width: int, height: int):
        if self.shatter_timer > 0 and self.shatter_timer < 2.0: return
        alpha = int(220 * self.corruption_level)
        grad = skia.GradientShader.MakeRadial(
            (width/2, height/2), width*0.9, [skia.ColorTRANSPARENT, skia.Color(0, 0, 0, alpha)], None, skia.TileMode.kClamp
        )
        canvas.drawPaint(skia.Paint(Shader=grad))

    def render_crash(self, canvas: skia.Canvas, width: int, height: int):
        if self.crash_timer <= 0: return
        paint = skia.Paint(Color=skia.ColorWHITE, Style=skia.Paint.kFill_Style)
        for _ in range(3 if self.memory_percent > 0.1 else 8):
            ry = random.uniform(0, height)
            rh = random.uniform(2, 40)
            canvas.drawRect(skia.Rect.MakeXYWH(0, ry, width, rh), paint)

    def render_shatter(self, canvas: skia.Canvas, width: int, height: int):
        if self.shatter_timer <= 0: return
        if self.shatter_timer >= 2.0:
            progress = (3.5 - self.shatter_timer) / 1.5
            paint = skia.Paint(Color=skia.Color(255, 255, 255, int(progress * 255)), Style=skia.Paint.kFill_Style)
            canvas.drawPaint(paint)
            paint_line = skia.Paint(Color=skia.ColorBLACK, StrokeWidth=2)
            random.seed(int(self.shatter_timer * 100))
            for _ in range(30):
                canvas.drawLine(random.uniform(0, width), random.uniform(0, height), random.uniform(0, width), random.uniform(0, height), paint_line)
            random.seed()
        else:
            canvas.clear(skia.ColorBLACK)
            self._render_glitch_text(canvas, "deja vu", width/2, height/2, self.loss_iteration, is_shatter=True)

    def render_void_text(self, canvas: skia.Canvas, text: str, width: int, height: int):
        """Clean but slightly unstable text for the void"""
        self._render_glitch_text(canvas, text, width/2, height/2, 0.5)

    def _render_glitch_text(self, canvas: skia.Canvas, text: str, cx: float, cy: float, intensity: float, is_shatter: bool = False):
        font_size = 42
        typeface = skia.Typeface.MakeFromFile("assets/font.ttf") or skia.Typeface.MakeDefault()
        font = skia.Font(typeface, font_size)
        
        paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
        
        # Obfuscation logic
        display_text = ""
        chars = "01X#!?@$<>[]"
        for c in text:
            if c == " ": 
                display_text += " "
                continue
            # Chance to swap characters increases with intensity/loss
            chance = 0.15 * intensity if is_shatter else 0.05
            if random.random() < chance:
                display_text += random.choice(chars)
            else:
                display_text += c

        # Horizontal slicing glitch
        num_slices = 3
        slice_h = font_size / num_slices
        
        for i in range(num_slices):
            canvas.save()
            # Rect for the slice
            clip_rect = skia.Rect.MakeXYWH(cx - 200, cy - font_size + (i * slice_h), 400, slice_h)
            canvas.clipRect(clip_rect)
            
            # Random offset per slice
            ox = random.uniform(-5, 5) * intensity if random.random() > 0.7 else 0
            oy = random.uniform(-1, 1) * intensity
            
            # RGB shadow for shatter
            if is_shatter and random.random() > 0.5:
                paint.setColor(skia.ColorRED)
                canvas.drawString(display_text, cx - 80 + ox + 2, cy + oy, font, paint)
                paint.setColor(skia.ColorCYAN)
                canvas.drawString(display_text, cx - 80 + ox - 2, cy + oy, font, paint)
                paint.setColor(skia.ColorWHITE)

            canvas.drawString(display_text, cx - 80 + ox, cy + oy, font, paint)
            canvas.restore()

    def render_impact_shatter(self, canvas: skia.Canvas):
        if self.impact_shatter_timer <= 0: return
        alpha = int((self.impact_shatter_timer / 0.3) * 200)
        paint = skia.Paint(Color=skia.Color(255, 255, 255, alpha), Style=skia.Paint.kStroke_Style, StrokeWidth=2, AntiAlias=True)
        random.seed(42)
        for _ in range(8):
            path = skia.Path()
            path.moveTo(self.impact_pos.x, self.impact_pos.y)
            curr = self.impact_pos
            for _ in range(4):
                curr = curr + Vec2(random.uniform(-100, 100), random.uniform(-100, 100))
                path.lineTo(curr.x, curr.y)
            canvas.drawPath(path, paint)
        random.seed()

    def render_cracks(self, canvas: skia.Canvas, width: int, height: int):
        if (self.corruption_level < 0.15 and self.boss_crack_level < 0.05) or (self.shatter_timer > 0 and self.shatter_timer < 2.0): return
        
        # Combine corruption cracks and boss cracks
        total_crack_intensity = max(self.corruption_level, self.boss_crack_level)
        num_cracks = int(30 * total_crack_intensity)
        
        paint = skia.Paint(
            Color=skia.Color(255, 255, 255, int(180 * total_crack_intensity)), 
            Style=skia.Paint.kStroke_Style, 
            StrokeWidth=1, 
            AntiAlias=True
        )
        
        random.seed(42) 
        for _ in range(num_cracks):
            # Start near edges
            side = random.randint(0, 3)
            if side == 0: # Top
                start = Vec2(random.uniform(0, width), random.uniform(0, 50))
            elif side == 1: # Bottom
                start = Vec2(random.uniform(0, width), random.uniform(height - 50, height))
            elif side == 2: # Left
                start = Vec2(random.uniform(0, 50), random.uniform(0, height))
            else: # Right
                start = Vec2(random.uniform(width - 50, width), random.uniform(0, height))
            
            # If not enough boss corruption, skip some edge cracks to only show them at high intensity
            if random.random() > total_crack_intensity * 1.5:
                # Fallback to original random position check for general corruption
                start = Vec2(random.uniform(0, width), random.uniform(0, height))
                if 180 < start.x < width - 180 and 180 < start.y < height - 180: continue

            path = skia.Path()
            path.moveTo(start.x, start.y)
            curr = start
            # Crack grows towards center
            center = Vec2(width/2, height/2)
            dir_to_center = (center - start).normalized()
            
            for i in range(8):
                # Jittery path towards center
                step = dir_to_center * 30 + Vec2(random.uniform(-20, 20), random.uniform(-20, 20))
                curr = curr + step
                path.lineTo(curr.x, curr.y)
            canvas.drawPath(path, paint)
        random.seed()