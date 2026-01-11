import math, random, glfw, skia
from engine.assets import AssetManager
from engine.file import FileManager, resource_path
from engine.physics import Vec2
from engine.sprite import Sprite

class IntroManager:
    def __init__(self, w, h, audio):
        self.w, self.h, self.audio = w, h, audio
        for s in ["type", "explode", "dialup", "step"]: self.audio.load(f"assets/{s}.wav", s)
        self.state, self.t = "WALKING_IN", 0.0
        self.guide_pos, self.guide_spritesheet = Vec2(w - 250, h - 80), AssetManager.get().load_spritesheet("assets/guide.png", 16, 16, 1, "guide")
        self.guide_frame, self.guide_vanished = 2, False
        self.player_visual_pos, self.player_target_x = Vec2(-50, h - 80), 200
        self.dialog_lines, self.current_line_idx, self.current_text, self.char_timer, self.char_speed = [], 0, "", 0.0, 0.03
        self.matrix_t, self.door_glitch_t, self.boot_t = 0.0, 0.0, 0.0
        self.boot_lines = ["Entering mainframe #c312...", "Traversing CPU, destination: CORE2", "..."]
        self.current_boot_line, self.boot_text = 0, ""
        self.load_dialog()
        tf = skia.Typeface.MakeFromFile(resource_path("assets/font.ttf")) or skia.Typeface.MakeDefault()
        self.font, self.boot_font, self.ui_font = skia.Font(tf, 20), skia.Font(tf, 24), skia.Font(tf, 21)

    def load_dialog(self):
        root = FileManager.get().load_xml("dialog_intro.xml")
        if root is not None:
            for line in root.findall("line"): self.dialog_lines.append(line.text)
        else: self.dialog_lines = ["Hello...", "Initialization complete."]

    def update(self, dt, keys, particles):
        old_t, self.t = self.t, self.t + dt
        if self.state in ["WALKING_IN", "DOOR_WAIT"] and int(old_t * 5) != int(self.t * 5): self.audio.play("step", volume=0.2)
        if self.state == "WALKING_IN":
            self.player_visual_pos.x += 150 * dt
            if self.player_visual_pos.x >= self.player_target_x: self.player_visual_pos.x = self.player_target_x; self.state = "TALKING"
        elif self.state == "TALKING":
            if self.current_line_idx < len(self.dialog_lines):
                target = self.dialog_lines[self.current_line_idx]
                if len(self.current_text) < len(target):
                    self.char_timer += dt
                    if self.char_timer >= self.char_speed: self.char_timer = 0; self.current_text += target[len(self.current_text)]; self.audio.play("type", volume=0.2)
                elif glfw.KEY_SPACE in keys or glfw.KEY_ENTER in keys: self.current_line_idx += 1; self.current_text = ""
            else:
                self.state = "DISAPPEARING"; self.matrix_t = 0.0; self.audio.play("explode", volume=0.5)
                particles.emit(self.guide_pos, 40, skia.ColorWHITE, (100, 400), size_range=(2, 5)); self.guide_vanished = True
        elif self.state == "DISAPPEARING":
            self.matrix_t += dt
            if self.matrix_t >= 1.0: self.state = "DOOR_WAIT"; self.door_glitch_t = 0.0
        elif self.state == "DOOR_WAIT":
            self.door_glitch_t += dt
            if self.player_visual_pos.x > self.w - 300: self.state = "BOOTING"; self.boot_t = 0.0; self.audio.play("dialup", volume=0.5)
            if glfw.KEY_D in keys or glfw.KEY_RIGHT in keys: self.player_visual_pos.x += 200 * dt
        elif self.state == "BOOTING":
            self.boot_t += dt
            if self.current_boot_line < len(self.boot_lines):
                target = self.boot_lines[self.current_boot_line]
                if len(self.boot_text) < len(target):
                    self.char_timer += dt
                    if self.char_timer >= 0.04: self.char_timer = 0; self.boot_text += target[len(self.boot_text)]; self.audio.play("type", volume=0.1)
                elif self.boot_t > (self.current_boot_line + 1) * 2.5: self.current_boot_line += 1; self.boot_text = ""
            elif self.boot_t > (len(self.boot_lines) * 2.5 + 1.0): return "FINISHED"
        return None

    def render(self, canvas, player_sprite):
        if self.state == "BOOTING":
            canvas.clear(skia.ColorBLACK); pa = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
            for i in range(self.current_boot_line): canvas.drawString(self.boot_lines[i], 100, 200 + i * 40, self.boot_font, pa)
            canvas.drawString(self.boot_text, 100, 200 + self.current_boot_line * 40, self.boot_font, pa); return
        canvas.drawRect(skia.Rect.MakeXYWH(0, self.h - 50, self.w, 50), skia.Paint(Color=skia.Color(30, 30, 30)))
        if not self.guide_vanished and self.guide_spritesheet:
            sprite = Sprite(self.guide_spritesheet.get_frame(self.guide_frame)); sprite.scale = Vec2(6, 6); sprite.flip_x = True; sprite.render(canvas, self.guide_pos)
        player_sprite.animation_frame = (1 if (int(self.t * 10) % 2 == 0) else 0) if self.state == "WALKING_IN" or (self.state == "DOOR_WAIT" and self.player_visual_pos.x > 200) else 2
        player_sprite.render_at(canvas, self.player_visual_pos, flip=False)
        if self.state == "TALKING" and self.current_text: self.render_dialog(canvas)
        if self.state == "DOOR_WAIT": self.render_door(canvas)
        self.render_controls(canvas)

    def render_controls(self, canvas):
        pa = skia.Paint(AntiAlias=True, Color=skia.Color(100, 100, 100))
        for i, text in enumerate(["A/D : MOVE", "W/SPACE : JUMP", "SHIFT : DASH (DEFEEAT GHOSTS)", "SPACE : CONTINUE DIALOG", "F3 : SKIP LEVEL"]):
            canvas.drawString(text, 20, 40 + i * 30, self.ui_font, pa)

    def render_dialog(self, canvas):
        max_w, lines, curr_line = 400, [], ""
        for w in self.current_text.split(" "):
            if self.font.measureText(curr_line + (" " if curr_line else "") + w) < max_w: curr_line += (" " if curr_line else "") + w
            else: lines.append(curr_line); curr_line = w
        lines.append(curr_line); bh = len(lines) * 25 + 20; bx, by = self.guide_pos.x - 200, self.guide_pos.y - 100 - bh
        rect = skia.Rect.MakeXYWH(bx, by, max_w + 20, bh)
        canvas.drawRect(rect, skia.Paint(Color=skia.Color(0, 0, 0, 200))); canvas.drawRect(rect, skia.Paint(Color=skia.ColorWHITE, Style=skia.Paint.kStroke_Style, StrokeWidth=2))
        pa = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
        for i, l in enumerate(lines): canvas.drawString(l, bx + 10, by + 25 + i * 25, self.font, pa)

    def render_door(self, canvas):
        if self.door_glitch_t < 0.5 and random.random() > 0.5: return
        dx, dy, dw, dh = self.w - 200, self.h - 140, 60, 90; gs = 5 + math.sin(self.t * 5) * 3
        canvas.drawRect(skia.Rect.MakeXYWH(dx-gs, dy-gs, dw+gs*2, dh+gs*2), skia.Paint(Color=skia.Color(0, 255, 255, 100), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, gs)))
        canvas.drawRect(skia.Rect.MakeXYWH(dx, dy, dw, dh), skia.Paint(Color=skia.Color(0, 50, 50, 200))); canvas.drawRect(skia.Rect.MakeXYWH(dx + 10, dy + 10, dw - 20, dh - 20), skia.Paint(Color=skia.Color(0, 200, 200, 255)))