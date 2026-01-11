import skia
import math
import random
import glfw
from engine.file import resource_path

class UIManager:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        # Retro colors
        self.color_bg = skia.Color(30, 30, 30)
        self.color_frame = skia.Color(150, 150, 150)
        self.color_bar_high = skia.Color(0, 255, 100)
        self.color_bar_mid = skia.Color(255, 200, 0)
        self.color_bar_low = skia.Color(255, 50, 50)
        self.color_text = skia.ColorWHITE

        # Font setup
        typeface = skia.Typeface.MakeFromFile(resource_path("assets/font.ttf"))
        if not typeface:
            typeface = skia.Typeface.MakeDefault()
        self.typeface = typeface
        self.font = skia.Font(self.typeface, 18)

        # Fruit indicator setup
        self.fruit_image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(resource_path("assets/fruit.png")))
        self.fruit_frame_size = 16

    def render(self, canvas: skia.Canvas, memory: float, max_memory: float, fruits: int = 0):
        percent = max(0.0, min(1.0, memory / max_memory))
        
        # Position and size
        bar_w = 300
        bar_h = 24
        x = 40
        y = 40

        # Draw Label
        paint_text = skia.Paint(AntiAlias=True, Color=self.color_text)
        canvas.drawString(f"MEMORY SYSTEM: {int(percent * 100)}%", x, y - 10, self.font, paint_text)

        # Draw Outer Frame
        paint_frame = skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color=self.color_frame)
        canvas.drawRect(skia.Rect.MakeXYWH(x - 2, y - 2, bar_w + 4, bar_h + 4), paint_frame)

        # Draw Background
        paint_bg = skia.Paint(Color=self.color_bg, Style=skia.Paint.kFill_Style)
        canvas.drawRect(skia.Rect.MakeXYWH(x, y, bar_w, bar_h), paint_bg)

        # Draw Segments (Retro blocky look)
        if percent > 0:
            num_segments = 20
            filled_segments = int(percent * num_segments)
            seg_w = (bar_w / num_segments)
            
            # Select color based on health
            if percent > 0.6:
                bar_color = self.color_bar_high
            elif percent > 0.3:
                bar_color = self.color_bar_mid
            else:
                bar_color = self.color_bar_low
                
            paint_seg = skia.Paint(Color=bar_color, Style=skia.Paint.kFill_Style)
            
            for i in range(filled_segments):
                # Draw individual blocks with a 1px gap
                canvas.drawRect(
                    skia.Rect.MakeXYWH(x + i * seg_w + 1, y + 1, seg_w - 2, bar_h - 2), 
                    paint_seg
                )

        # Add scanline effect over the bar for extra retro feel
        paint_scan = skia.Paint(Color=skia.Color(0, 0, 0, 50), Style=skia.Paint.kFill_Style)
        for i in range(0, bar_h, 4):
            canvas.drawRect(skia.Rect.MakeXYWH(x, y + i, bar_w, 1), paint_scan)

        if fruits > 0:
            self._render_fruit_indicator(canvas, x + bar_w + 20, y - 5, fruits, percent)

    def _render_fruit_indicator(self, canvas: skia.Canvas, x: float, y: float, fruits: int, mem_percent: float):
        if not self.fruit_image:
            return

        # Frame selection: frame 0=fruit, frame 1=3, frame 2=2, frame 3=1
        frame_idx = 0
        if fruits >= 3:
            frame_idx = 1
        elif fruits == 2:
            frame_idx = 2
        elif fruits == 1:
            frame_idx = 3
        
        src = skia.Rect.MakeXYWH(frame_idx * self.fruit_frame_size, 0, self.fruit_frame_size, self.fruit_frame_size)
        dst_size = 40 # Slightly larger
        dst = skia.Rect.MakeXYWH(x, y, dst_size, dst_size)

        # Pulse effect
        t = glfw.get_time() if hasattr(glfw, 'get_time') else 0
        pulse = math.sin(t * 4.0) * 2.0
        dst = dst.makeOutset(pulse, pulse)

        # Background glow
        glow_pa = skia.Paint(
            Color=skia.Color(100, 200, 255, 60),
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)
        )
        canvas.drawCircle(x + dst_size/2, y + dst_size/2, dst_size/2 + 5, glow_pa)

        # Glitch effect intensity based on memory loss
        glitch_intensity = max(0.0, 1.0 - mem_percent)
        
        if random.random() < glitch_intensity * 0.4:
            # Ghost/RGB split effect
            for i in range(3):
                ox = random.uniform(-6, 6) * glitch_intensity
                oy = random.uniform(-6, 6) * glitch_intensity
                
                colors = [skia.ColorRED, skia.ColorCYAN, skia.ColorWHITE]
                p = skia.Paint(ColorFilter=skia.ColorFilters.Blend(colors[i], skia.BlendMode.kModulate))
                p.setAlpha(180)
                
                canvas.drawImageRect(self.fruit_image, src, dst.makeOffset(ox, oy), paint=p)
        else:
            # Subtle double image glitch even at high memory
            if random.random() < 0.1:
                p = skia.Paint(Alphaf=0.5)
                canvas.drawImageRect(self.fruit_image, src, dst.makeOffset(random.uniform(-2, 2), 0), paint=p)
            
            canvas.drawImageRect(self.fruit_image, src, dst)
            
        # Occasional horizontal slice glitch
        if random.random() < glitch_intensity * 0.15:
            slice_y = random.uniform(0, dst_size)
            slice_h = random.uniform(2, 8)
            canvas.save()
            canvas.clipRect(skia.Rect.MakeXYWH(x - 10, y + slice_y, dst_size + 20, slice_h))
            canvas.drawImageRect(self.fruit_image, src, dst.makeOffset(random.uniform(-15, 15), 0))
            canvas.restore()
        
        # Draw "1" key hint
        hint_font = skia.Font(self.typeface, 14)
        hint_paint = skia.Paint(Color=skia.Color(200, 200, 200, 220), AntiAlias=True)
        canvas.drawString("[1] USE", x + dst_size/2 - 25, y + dst_size + 18, hint_font, hint_paint)
