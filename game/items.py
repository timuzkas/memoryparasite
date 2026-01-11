import math, random, skia
from engine.file import resource_path
from engine.physics import Vec2

class Fruit:
    def __init__(self, pos, idx=0):
        self.pos, self.start_y, self.idx, self.t = pos, pos.y, idx, random.uniform(0, math.pi * 2)
        self.radius, self.collected, self.type = 20.0, False, "fruit"
        self.image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(resource_path("assets/fruit.png"))); self.f_sz = 16 

    def update(self, dt, player_pos, part):
        if self.collected: return False
        self.t += dt * 3.0; self.pos.y = self.start_y + math.sin(self.t) * 10.0
        if random.random() < 0.15: part.emit(self.pos + Vec2(8, 8), 1, skia.Color(100, 150, 255), (20, 50), life_range=(0.5, 1.0), size_range=(1, 3), gravity=-50)
        if (self.pos + Vec2(8, 8) - player_pos).length() < 30.0:
            self.collected = True; part.emit(self.pos + Vec2(8, 8), 20, skia.Color(150, 200, 255), (100, 300)); return True
        return False

    def render(self, canvas):
        if self.collected: return
        if not self.image: canvas.drawCircle(self.pos.x + 8, self.pos.y + 8, 8, skia.Paint(Color=skia.Color(100, 150, 255))); return
        canvas.save(); canvas.drawCircle(self.pos.x + 16, self.pos.y + 16, 12, skia.Paint(Color=skia.Color(200, 200, 255, 120), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)))
        canvas.drawImageRect(self.image, skia.Rect.MakeXYWH(self.idx * self.f_sz, 0, self.f_sz, self.f_sz), skia.Rect.MakeXYWH(self.pos.x, self.pos.y, self.f_sz * 2, self.f_sz * 2)); canvas.restore()

class Fragment(Fruit):
    def __init__(self, pos, rot=0.0):
        super().__init__(pos, 0); self.type, self.rot = "fragment", rot
        self.image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(resource_path("assets/items.png")))
    def render(self, canvas):
        if self.collected: return
        canvas.save(); canvas.translate(self.pos.x + 16, self.pos.y + 16); canvas.rotate(self.rot + math.sin(self.t) * 20)
        canvas.drawCircle(0, 0, 10, skia.Paint(Color=skia.Color(200, 200, 255, 120), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)))
        canvas.drawImageRect(self.image, skia.Rect.MakeXYWH(0, 0, 16, 16), skia.Rect.MakeXYWH(-16, -16, 32, 32)); canvas.restore()

class ItemManager:
    def __init__(self): self.items = []
    def add_fruit(self, pos, idx=0): self.items.append(Fruit(pos, idx))
    def add_fragment(self, pos, rot=0.0): self.items.append(Fragment(pos, rot))
    def reset(self): self.items.clear()
    def update(self, dt, p_pos, part): return [it.type for it in self.items if it.update(dt, p_pos, part)]
    def render(self, canvas): [it.render(canvas) for it in self.items]