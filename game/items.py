import math
import random

import skia

from engine.file import resource_path
from engine.physics import Vec2


class Fruit:
    def __init__(self, pos: Vec2, frame_idx: int = 0):
        self.pos = pos
        self.start_y = pos.y
        self.frame_idx = frame_idx
        self.t = random.uniform(0, math.pi * 2)
        self.radius = 20.0
        self.collected = False
        self.type = "fruit"
        
        # Load spritesheet
        self.image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(resource_path("assets/fruit.png")))
        self.frame_size = 16 

    def update(self, dt: float, player_pos: Vec2, particles):
        if self.collected:
            return False
            
        self.t += dt * 3.0
        self.pos.y = self.start_y + math.sin(self.t) * 10.0
        
        # Emit blue particles
        if random.random() < 0.15:
            particles.emit(
                self.pos + Vec2(8, 8), 
                1, 
                skia.Color(100, 150, 255), 
                speed_range=(20, 50), 
                life_range=(0.5, 1.0),
                size_range=(1, 3),
                gravity=-50 # Float upwards
            )
            
        # Check collection
        if (self.pos + Vec2(8, 8) - player_pos).length() < 30.0:
            self.collected = True
            particles.emit(self.pos + Vec2(8, 8), 20, skia.Color(150, 200, 255), speed_range=(100, 300))
            return True
        return False

    def render(self, canvas: skia.Canvas):
        if self.collected:
            return
            
        if not self.image:
            # Fallback
            pa = skia.Paint(Color=skia.Color(100, 150, 255))
            canvas.drawCircle(self.pos.x + 8, self.pos.y + 8, 8, pa)
            return

        src = skia.Rect.MakeXYWH(self.frame_idx * self.frame_size, 0, self.frame_size, self.frame_size)
        dst = skia.Rect.MakeXYWH(self.pos.x, self.pos.y, self.frame_size * 2, self.frame_size * 2) # Scale up 2x
        
        canvas.save()
        # Add a little glow
        glow_pa = skia.Paint(
            Color=skia.Color(200, 200, 255, 120),
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)
        )
        canvas.drawCircle(self.pos.x + 16, self.pos.y + 16, 12, glow_pa)
        
        canvas.drawImageRect(self.image, src, dst)
        canvas.restore()

class Fragment(Fruit):
    def __init__(self, pos: Vec2, rotation: float = 0.0):
        super().__init__(pos, 0)
        self.type = "fragment"
        self.rotation = rotation
        self.image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(resource_path("assets/items.png")))
        
    def render(self, canvas: skia.Canvas):
        if self.collected: return
        src = skia.Rect.MakeXYWH(0, 0, 16, 16)
        dst = skia.Rect.MakeXYWH(-16, -16, 32, 32)
        
        canvas.save()
        canvas.translate(self.pos.x + 16, self.pos.y + 16)
        canvas.rotate(self.rotation + math.sin(self.t) * 20)
        
        # Glitchy glow
        glow_pa = skia.Paint(
            Color=skia.Color(200, 200, 255, 120),
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)
        )
        canvas.drawCircle(0, 0, 10, glow_pa)
        
        canvas.drawImageRect(self.image, src, dst)
        canvas.restore()

class ItemManager:
    def __init__(self):
        self.items = []

    def add_fruit(self, pos: Vec2, frame_idx: int = 0):
        self.items.append(Fruit(pos, frame_idx))

    def add_fragment(self, pos: Vec2, rotation: float = 0.0):
        self.items.append(Fragment(pos, rotation))

    def reset(self):
        self.items.clear()

    def update(
        self, dt: float, player_pos: Vec2, particles
    ) -> list:
        collected_types = []
        for it in self.items:
            if it.update(dt, player_pos, particles):
                collected_types.append(it.type)
        return collected_types

    def render(self, canvas: skia.Canvas):
        for it in self.items:
            it.render(canvas)
