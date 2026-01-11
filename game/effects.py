import random, skia, math
from engine.effects import PostProcessSystem
from engine.physics import Vec2

class CorruptionManager:
    def __init__(self, engine, post_process: PostProcessSystem):
        self.engine, self.pp = engine, post_process
        self.corruption_level, self.memory_percent = 0.0, 1.0
        self.crash_timer, self.shatter_timer, self.impact_shatter_timer = 0.0, 0.0, 0.0
        self.is_shattered, self.impact_pos, self.loss_iteration, self.boss_crack_level = False, Vec2(0, 0), 0, 0.0
        
    def update(self, dt):
        self.pp.update(dt)
        if self.crash_timer > 0: self.crash_timer -= dt
        if self.shatter_timer > 0: self.shatter_timer -= dt
        if self.impact_shatter_timer > 0: self.impact_shatter_timer -= dt
        if self.memory_percent < 0.5 and self.shatter_timer <= 0:
            if random.random() < (0.5 - self.memory_percent) * 6.0 * dt: self.crash_timer = 0.05
        
    def on_headbang(self): self.pp.trigger_shake(20.0); self.pp.trigger_glitch(0.8); self.crash_timer = 0.15 
    def trigger_glitch(self, intensity): self.pp.trigger_glitch(intensity)
    def trigger_impact_shatter(self, pos): self.impact_shatter_timer = 0.3; self.impact_pos = pos.copy(); self.pp.trigger_shake(15.0); self.pp.trigger_glitch(0.5)
    def trigger_shatter(self, iteration): self.is_shattered = True; self.shatter_timer = 3.5; self.loss_iteration = iteration; self.pp.trigger_glitch(1.0); self.pp.trigger_shake(40.0)

    def set_corruption(self, mem_p):
        self.memory_percent = mem_p
        self.corruption_level = max(0.0, min(1.0, (0.75 - mem_p) / 0.65)) if mem_p < 0.75 else 0.0
        self.pp.glitch = 1.0 if mem_p < 0.1 else self.corruption_level

    def render_vignette(self, canvas, w, h):
        if 0 < self.shatter_timer < 2.0: return
        grad = skia.GradientShader.MakeRadial((w/2, h/2), w*0.9, [skia.ColorTRANSPARENT, skia.Color(0, 0, 0, int(220 * self.corruption_level))], None, skia.TileMode.kClamp)
        canvas.drawPaint(skia.Paint(Shader=grad))

    def render_crash(self, canvas, w, h):
        if self.crash_timer <= 0: return
        pa = skia.Paint(Color=skia.ColorWHITE)
        for _ in range(3 if self.memory_percent > 0.1 else 8): canvas.drawRect(skia.Rect.MakeXYWH(0, random.uniform(0, h), w, random.uniform(2, 40)), pa)

    def render_shatter(self, canvas, w, h):
        if self.shatter_timer <= 0: return
        if self.shatter_timer >= 2.0:
            canvas.drawPaint(skia.Paint(Color=skia.Color(255, 255, 255, int((3.5 - self.shatter_timer) / 1.5 * 255))))
            pa = skia.Paint(Color=skia.ColorBLACK, StrokeWidth=2); random.seed(int(self.shatter_timer * 100))
            for _ in range(30): canvas.drawLine(random.uniform(0, w), random.uniform(0, h), random.uniform(0, w), random.uniform(0, h), pa)
            random.seed()
        else: canvas.clear(skia.ColorBLACK); self._render_glitch_text(canvas, "deja vu", w/2, h/2, self.loss_iteration, True)

    def render_void_text(self, canvas, text, w, h): self._render_glitch_text(canvas, text, w/2, h/2, 0.5)

    def _render_glitch_text(self, canvas, text, cx, cy, intensity, is_shatter=False):
        font = skia.Font(skia.Typeface.MakeFromFile("assets/font.ttf") or skia.Typeface.MakeDefault(), 42)
        paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE); chars = "01X#!?@$<>[]"
        disp = "".join([random.choice(chars) if random.random() < (0.15 * intensity if is_shatter else 0.05) else c for c in text])
        for i in range(3):
            canvas.save(); canvas.clipRect(skia.Rect.MakeXYWH(cx - 200, cy - 42 + (i * 14), 400, 14))
            ox, oy = (random.uniform(-5, 5) * intensity if random.random() > 0.7 else 0), random.uniform(-1, 1) * intensity
            if is_shatter and random.random() > 0.5:
                paint.setColor(skia.ColorRED); canvas.drawString(disp, cx - 80 + ox + 2, cy + oy, font, paint)
                paint.setColor(skia.ColorCYAN); canvas.drawString(disp, cx - 80 + ox - 2, cy + oy, font, paint); paint.setColor(skia.ColorWHITE)
            canvas.drawString(disp, cx - 80 + ox, cy + oy, font, paint); canvas.restore()

    def render_impact_shatter(self, canvas):
        if self.impact_shatter_timer <= 0: return
        pa = skia.Paint(Color=skia.Color(255, 255, 255, int(self.impact_shatter_timer / 0.3 * 200)), Style=skia.Paint.kStroke_Style, StrokeWidth=2, AntiAlias=True)
        random.seed(42)
        for _ in range(8):
            path = skia.Path(); path.moveTo(self.impact_pos.x, self.impact_pos.y); curr = self.impact_pos
            for _ in range(4): curr = curr + Vec2(random.uniform(-100, 100), random.uniform(-100, 100)); path.lineTo(curr.x, curr.y)
            canvas.drawPath(path, pa)
        random.seed()

    def render_cracks(self, canvas, w, h):
        if (self.corruption_level < 0.15 and self.boss_crack_level < 0.05) or (0 < self.shatter_timer < 2.0): return
        val = max(self.corruption_level, self.boss_crack_level); pa = skia.Paint(Color=skia.Color(255, 255, 255, int(180 * val)), Style=skia.Paint.kStroke_Style, StrokeWidth=1, AntiAlias=True)
        random.seed(42)
        for _ in range(int(30 * val)):
            side = random.randint(0, 3)
            if side == 0: start = Vec2(random.uniform(0, w), random.uniform(0, 50))
            elif side == 1: start = Vec2(random.uniform(0, w), random.uniform(h-50, h))
            elif side == 2: start = Vec2(random.uniform(0, 50), random.uniform(0, h))
            else: start = Vec2(random.uniform(w-50, w), random.uniform(0, h))
            if random.random() > val * 1.5:
                start = Vec2(random.uniform(0, w), random.uniform(0, h))
                if 180 < start.x < w - 180 and 180 < start.y < h - 180: continue
            path = skia.Path(); path.moveTo(start.x, start.y); curr, dir = start, (Vec2(w/2, h/2) - start).normalized()
            for _ in range(8): curr = curr + dir * 30 + Vec2(random.uniform(-20, 20), random.uniform(-20, 20)); path.lineTo(curr.x, curr.y)
            canvas.drawPath(path, pa)
        random.seed()
