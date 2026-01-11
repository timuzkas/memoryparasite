import math
import random

import glfw
import skia

from engine.assets import AssetManager
from engine.file import FileManager, resource_path
from engine.physics import Vec2
from engine.sprite import Sprite


class IntroManager:
    def __init__(self, w, h, audio):
        self.w = w
        self.h = h
        self.audio = audio
        self.audio.load("assets/type.wav", "type")
        self.audio.load("assets/explode.wav", "explode")
        self.audio.load("assets/dialup.wav", "dialup")
        self.audio.load("assets/step.wav", "step")

        self.state = (
            "WALKING_IN"  # WALKING_IN, TALKING, DISAPPEARING, DOOR_WAIT, BOOTING
        )
        self.t = 0.0

        # Guide setup
        self.guide_pos = Vec2(w - 250, h - 80)
        self.guide_spritesheet = AssetManager.get().load_spritesheet(
            "assets/guide.png", frame_w=16, frame_h=16, offset=1, key="guide"
        )
        self.guide_frame = 2  # Idle
        self.guide_vanished = False

        # Player walking in
        self.player_visual_pos = Vec2(-50, h - 80)
        self.player_target_x = 200

        # Dialog
        self.dialog_lines = []
        self.load_dialog()
        self.current_line_idx = 0
        self.current_text = ""
        self.char_timer = 0.0
        self.char_speed = 0.03

        # Effects
        self.matrix_t = 0.0
        self.door_glitch_t = 0.0
        self.boot_t = 0.0
        self.boot_lines = [
            "Entering mainframe #c312...",
            "Traversing CPU, destination: CORE2",
            "...",
        ]
        self.current_boot_line = 0
        self.boot_text = ""

        # Font
        tf = (
            skia.Typeface.MakeFromFile(resource_path("assets/font.ttf"))
            or skia.Typeface.MakeDefault()
        )
        self.font = skia.Font(tf, 20)
        self.boot_font = skia.Font(tf, 24)
        self.ui_font = skia.Font(tf, 21)

    def load_dialog(self):
        root = FileManager.get().load_xml("dialog_intro.xml")
        if root is not None:
            for line in root.findall("line"):
                self.dialog_lines.append(line.text)
        else:
            self.dialog_lines = ["Hello...", "Initialization complete."]

    def update(self, dt, keys, particles):
        old_t = self.t
        self.t += dt

        # Step sound logic (every 0.2s while walking)
        if self.state in ["WALKING_IN", "DOOR_WAIT"]:
            if int(old_t * 5) != int(self.t * 5):
                self.audio.play("step", volume=0.2)

        if self.state == "WALKING_IN":
            self.player_visual_pos.x += 150 * dt
            if self.player_visual_pos.x >= self.player_target_x:
                self.player_visual_pos.x = self.player_target_x
                self.state = "TALKING"

        elif self.state == "TALKING":
            if self.current_line_idx < len(self.dialog_lines):
                target_full_text = self.dialog_lines[self.current_line_idx]
                if len(self.current_text) < len(target_full_text):
                    self.char_timer += dt
                    if self.char_timer >= self.char_speed:
                        self.char_timer = 0
                        self.current_text += target_full_text[len(self.current_text)]
                        self.audio.play("type", volume=0.2)
                else:
                    if glfw.KEY_SPACE in keys or glfw.KEY_ENTER in keys:
                        self.current_line_idx += 1
                        self.current_text = ""
            else:
                self.state = "DISAPPEARING"
                self.matrix_t = 0.0
                self.audio.play("explode", volume=0.5)
                particles.emit(
                    self.guide_pos,
                    40,
                    skia.ColorWHITE,
                    speed_range=(100, 400),
                    size_range=(2, 5),
                )
                self.guide_vanished = True

        elif self.state == "DISAPPEARING":
            self.matrix_t += dt
            if self.matrix_t >= 1.0:
                self.state = "DOOR_WAIT"
                self.door_glitch_t = 0.0

        elif self.state == "DOOR_WAIT":
            self.door_glitch_t += dt
            if self.player_visual_pos.x > self.w - 300:
                self.state = "BOOTING"
                self.boot_t = 0.0
                self.audio.play("dialup", volume=0.5)

            if glfw.KEY_D in keys or glfw.KEY_RIGHT in keys:
                self.player_visual_pos.x += 200 * dt

        elif self.state == "BOOTING":
            self.boot_t += dt
            if self.current_boot_line < len(self.boot_lines):
                target = self.boot_lines[self.current_boot_line]
                if len(self.boot_text) < len(target):
                    self.char_timer += dt
                    if self.char_timer >= 0.04:
                        self.char_timer = 0
                        self.boot_text += target[len(self.boot_text)]
                        self.audio.play("type", volume=0.1)
                else:
                    # Delay between lines
                    line_finished_at = (self.current_boot_line + 1) * 2.5
                    if self.boot_t > line_finished_at:
                        self.current_boot_line += 1
                        self.boot_text = ""
            else:
                # User Request: Final delay reduced to ~1 second
                # Total time for all lines was roughly len*2.5, we just wait 1s more
                if self.boot_t > (len(self.boot_lines) * 2.5 + 1.0):
                    return "FINISHED"

        return None

    def render(self, canvas: skia.Canvas, player_sprite):
        if self.state == "BOOTING":
            canvas.clear(skia.ColorBLACK)
            paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
            for i in range(self.current_boot_line):
                canvas.drawString(
                    self.boot_lines[i], 100, 200 + i * 40, self.boot_font, paint
                )
            canvas.drawString(
                self.boot_text,
                100,
                200 + self.current_boot_line * 40,
                self.boot_font,
                paint,
            )
            return

        floor_paint = skia.Paint(Color=skia.Color(30, 30, 30))
        canvas.drawRect(skia.Rect.MakeXYWH(0, self.h - 50, self.w, 50), floor_paint)

        # Render Guide
        if not self.guide_vanished:
            if self.guide_spritesheet:
                img = self.guide_spritesheet.get_frame(self.guide_frame)
                sprite = Sprite(img)
                sprite.scale = Vec2(6, 6)
                sprite.flip_x = True
                sprite.render(canvas, self.guide_pos)

        # Render Player
        if self.state != "BOOTING":
            anim_frame = 2
            if self.state == "WALKING_IN" or (
                self.state == "DOOR_WAIT" and self.player_visual_pos.x > 200
            ):
                anim_frame = 1 if (int(self.t * 10) % 2 == 0) else 0

            player_sprite.animation_frame = anim_frame
            player_sprite.render_at(canvas, self.player_visual_pos, flip=False)

        if self.state == "TALKING" and self.current_text:
            self.render_dialog(canvas)

        if self.state == "DOOR_WAIT":
            self.render_door(canvas)

        self.render_controls(canvas)

    def render_controls(self, canvas: skia.Canvas):
        paint = skia.Paint(AntiAlias=True, Color=skia.Color(100, 100, 100))
        controls = [
            "A/D : MOVE",
            "W/SPACE : JUMP",
            "SHIFT : DASH (DEFEEAT GHOSTS)",
            "SPACE : CONTINUE DIALOG",
            "F3 : SKIP LEVEL (last resort)",
        ]
        for i, text in enumerate(controls):
            canvas.drawString(text, 20, 40 + i * 30, self.ui_font, paint)

    def render_dialog(self, canvas: skia.Canvas):
        max_w = 400
        words = self.current_text.split(" ")
        lines = []
        curr_line = ""
        for w in words:
            test_line = curr_line + (" " if curr_line else "") + w
            if self.font.measureText(test_line) < max_w:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = w
        lines.append(curr_line)

        bubble_h = len(lines) * 25 + 20
        bx = self.guide_pos.x - 200
        by = self.guide_pos.y - 100 - bubble_h

        paint_bg = skia.Paint(
            Color=skia.Color(0, 0, 0, 200), Style=skia.Paint.kFill_Style
        )
        paint_border = skia.Paint(
            Color=skia.ColorWHITE, Style=skia.Paint.kStroke_Style, StrokeWidth=2
        )

        rect = skia.Rect.MakeXYWH(bx, by, max_w + 20, bubble_h)
        canvas.drawRect(rect, paint_bg)
        canvas.drawRect(rect, paint_border)

        paint_text = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
        for i, l in enumerate(lines):
            canvas.drawString(l, bx + 10, by + 25 + i * 25, self.font, paint_text)

    def render_door(self, canvas: skia.Canvas):
        if self.door_glitch_t < 0.5:
            if random.random() > 0.5:
                return

        dx, dy = self.w - 200, self.h - 140
        dw, dh = 60, 90

        glow_size = 5 + math.sin(self.t * 5) * 3
        glow_paint = skia.Paint(
            Color=skia.Color(0, 255, 255, 100),
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, glow_size),
        )
        canvas.drawRect(
            skia.Rect.MakeXYWH(
                dx - glow_size, dy - glow_size, dw + glow_size * 2, dh + glow_size * 2
            ),
            glow_paint,
        )

        door_paint = skia.Paint(
            Color=skia.Color(0, 50, 50, 200), Style=skia.Paint.kFill_Style
        )
        canvas.drawRect(skia.Rect.MakeXYWH(dx, dy, dw, dh), door_paint)

        inner_paint = skia.Paint(
            Color=skia.Color(0, 200, 200, 255), Style=skia.Paint.kFill_Style
        )
        canvas.drawRect(
            skia.Rect.MakeXYWH(dx + 10, dy + 10, dw - 20, dh - 20), inner_paint
        )
