import math
import random
from dataclasses import dataclass, field

import skia
from skia import Paint

from engine.collision import CollisionInfo, rect_vs_rect, resolve_rect_vs_static
from engine.file import FileManager, resource_path
from engine.physics import RigidBody, Vec2


@dataclass
class Platform:
    x: float
    y: float
    w: float
    h: float
    is_false: bool = False
    alpha: float = 1.0
    is_lost: bool = False
    glitch_t: float = 0.0
    memory_req: float | None = None
    was_visible: bool = False
    appear_t: float = 0.0
    is_permanent: bool = False
    glitch_type: str | None = None  # e.g. "chaos"
    orig_x: float = 0.0
    orig_y: float = 0.0
    temp_corrupt_t: float = 0.0
    is_hidden: bool = False
    reveal_t: float = 0.0
    memory_min: float | None = None
    fragment_req: int | None = None
    blink_freq: float | None = None


@dataclass
class Cable:
    x: float
    y: float
    length: float
    timer: float = 0.0


@dataclass
class Relay:
    x: float
    y: float
    type: str  # "weight", "spark", "ghost"
    active: bool = False
    glow_t: float = 0.0


@dataclass
class Door:
    x: float
    y: float
    w: float = 60.0
    h: float = 90.0
    target_level: str = ""
    active: bool = False
    glow_t: float = 0.0
    is_locked: bool = False
    reconstruction_percent: float = 0.0


class LevelManager:
    def __init__(self, width: int, height: int, phys, coll, items):
        self.platforms = []
        self.doors = []
        self.cables = []
        self.relays = []
        self.boss_spawn_pos = None
        self.w = width
        self.h = height
        self.phys = phys
        self.coll = coll
        self.items = items
        self.current_level_name = ""
        self.tutorial_text = ""
        self.dialogs = []
        self.active_dialog = None
        self.dialog_timer = 0.0
        self.pulse_timer = 0.0

        # Font for tutorial text
        self.typeface = (
            skia.Typeface.MakeFromFile(resource_path("assets/font.ttf"))
            or skia.Typeface.MakeDefault()
        )
        self.font = skia.Font(self.typeface, 24)

    def load_from_xml(self, level_name: str):
        self.platforms.clear()
        self.doors.clear()
        self.cables.clear()
        self.relays.clear()
        self.boss_spawn_pos = None
        self.items.reset()
        self.current_level_name = level_name
        self.tutorial_text = ""
        self.dialogs.clear()
        self.active_dialog = None
        self.dialog_timer = 0.0

        path = f"levels/{level_name}.xml"
        root = FileManager.get().load_xml(path)
        if root is None:
            self.generate(0)
            return

        # Load tutorial text from root attribute
        self.tutorial_text = root.get("tutorial", "")

        for d_elem in root.findall("dialog"):
            tx = float(d_elem.get("trigger_x", 0))
            self.dialogs.append(
                {"trigger_x": tx, "text": d_elem.text, "triggered": False}
            )

        boss_elem = root.find("boss")
        if boss_elem is not None:
            bx = float(boss_elem.get("x", 0))
            by = float(boss_elem.get("y", 0))
            self.boss_spawn_pos = Vec2(bx, by)

        for p_elem in root.findall("platform"):
            x, y = float(p_elem.get("x", 0)), float(p_elem.get("y", 0))
            w, h = float(p_elem.get("w", 100)), float(p_elem.get("h", 20))
            mem_req = p_elem.get("memory_req")
            mem_min = p_elem.get("memory_min")
            is_perm = p_elem.get("permanent") == "true" or (y > 600 and w > 200)
            glitch_type = p_elem.get("glitch_type")
            is_hidden = p_elem.get("hidden") == "true"
            frag_req = p_elem.get("fragment_req")
            blink_freq = p_elem.get("blink_freq")
            p = Platform(
                x,
                y,
                w,
                h,
                memory_req=float(mem_req) if mem_req else None,
                memory_min=float(mem_min) if mem_min else None,
                fragment_req=int(frag_req) if frag_req else None,
                blink_freq=float(blink_freq) if blink_freq else None,
                is_permanent=is_perm,
                glitch_type=glitch_type,
                is_hidden=is_hidden,
            )
            p.orig_x, p.orig_y = x, y
            self.platforms.append(p)

        for d_elem in root.findall("door"):
            x, y = float(d_elem.get("x", 0)), float(d_elem.get("y", 0))
            is_locked = d_elem.get("locked") == "true"
            self.doors.append(
                Door(x, y, target_level=d_elem.get("target", ""), is_locked=is_locked)
            )

        for i_elem in root.findall("item"):
            x, y = float(i_elem.get("x", 0)), float(i_elem.get("y", 0))
            typ = i_elem.get("type", "fruit")
            if typ == "fragment":
                rot = float(i_elem.get("rotation", 0))
                self.items.add_fragment(Vec2(x, y), rot)
            else:
                frame = int(i_elem.get("frame", 0))
                self.items.add_fruit(Vec2(x, y), frame)

        for c_elem in root.findall("cable"):
            x, y = float(c_elem.get("x", 0)), float(c_elem.get("y", 0))
            length = float(c_elem.get("len", 100))
            self.cables.append(Cable(x, y, length, timer=random.uniform(1.0, 3.0)))

        for r_elem in root.findall("relay"):
            x, y = float(r_elem.get("x", 0)), float(r_elem.get("y", 0))
            typ = r_elem.get("type", "weight")
            self.relays.append(Relay(x, y, typ))

    def generate(self, level_idx: int = 1):
        self.platforms.clear()
        self.doors.clear()
        self.platforms.append(Platform(0, self.h - 50, self.w, 50))
        self.doors.append(Door(self.w - 100, self.h - 140, target_level="level2"))

    def lose_random_platforms(self, count: int = 1) -> list[Vec2]:
        lost_spawn_points = []
        targets = [p for p in self.platforms if not p.is_lost and p.memory_req is None]
        if not targets:
            return []
        to_lose = random.sample(targets, min(count, len(targets)))
        for p in to_lose:
            p.is_lost = True
            lost_spawn_points.append(Vec2(p.x + p.w / 2, p.y + p.h / 2))
        return lost_spawn_points

    def revive_all_platforms(self):
        for p in self.platforms:
            p.is_lost = False
            p.appear_t = 0.5  # Play appear animation

    def check_standing_on_corrupted(
        self,
        body: RigidBody,
        width: float,
        height: float,
        mem_percent: float,
        fragments_collected: int = 0,
    ) -> bool:
        px, py = body.position.x - width / 2, body.position.y - height / 2
        check_rect = (px + 4, py + height, width - 8, 2)
        visible = self.get_visible_platforms(mem_percent, fragments_collected)
        for p in visible:
            # Drains memory if it's lost, chaos, has a memory requirement, or is temporarily corrupted
            if not (
                p.is_lost
                or p.memory_req is not None
                or p.memory_min is not None
                or p.fragment_req is not None
                or p.glitch_type is not None
                or p.temp_corrupt_t > 0
            ):
                continue
            if (
                check_rect[0] < p.x + p.w
                and check_rect[0] + check_rect[2] > p.x
                and check_rect[1] < p.y + p.h
                and check_rect[1] + check_rect[3] > p.y
            ):
                return True
        return False

    def update(
        self,
        dt: float,
        player_memory_percent: float,
        particles,
        fragments_collected: int = 0,
        player_x: float = 0.0,
    ):
        # Update dialog triggers
        for d in self.dialogs:
            if not d["triggered"] and player_x >= d["trigger_x"]:
                d["triggered"] = True
                # We'll use a property to track the "active" dialog for rendering
                self.active_dialog = d["text"]
                self.dialog_timer = 5.0  # Show for 5 seconds

        for p in self.platforms:
            is_visible_req = (p.memory_req is None) or (
                player_memory_percent <= p.memory_req
            )
            is_visible_min = (p.memory_min is None) or (
                player_memory_percent >= p.memory_min
            )
            is_visible_frag = (p.fragment_req is None) or (
                fragments_collected >= p.fragment_req
            )

            # Blinking logic
            is_visible_blink = True
            if p.blink_freq is not None:
                # Frequency increases with memory level
                freq = p.blink_freq * (0.2 + player_memory_percent * 2.0)
                is_visible_blink = math.sin(self.glow_t_accum * freq) > 0

            is_visible = (
                is_visible_req
                and is_visible_min
                and is_visible_frag
                and is_visible_blink
            )

            if (
                is_visible
                and not p.was_visible
                and (
                    p.memory_req is not None
                    or p.memory_min is not None
                    or p.fragment_req is not None
                )
            ):
                p.appear_t = 0.5
                particles.emit(
                    Vec2(p.x + p.w / 2, p.y + p.h / 2),
                    15,
                    skia.Color(150, 100, 255),
                    speed_range=(50, 150),
                )
            p.was_visible = is_visible
            if p.appear_t > 0:
                p.appear_t -= dt

            # Glitch timer for all glitchy things
            if (
                p.is_lost
                or p.temp_corrupt_t > 0
                or p.glitch_type is not None
                or p.blink_freq is not None
            ):
                p.glitch_t += dt

            if p.temp_corrupt_t > 0:
                p.temp_corrupt_t -= dt

            if p.glitch_type == "chaos" and not p.is_permanent:
                # Move, rotate, jump slightly
                noise_x = math.sin(p.glitch_t * 5) * 25
                noise_y = math.cos(p.glitch_t * 7) * 20
                p.x = p.orig_x + noise_x
                p.y = p.orig_y + noise_y

                # Resizing glitch
                if random.random() < 0.05:
                    p.w = p.w * random.uniform(0.9, 1.1)
                    if p.w < 20:
                        p.w = 20
                    if p.w > 500:
                        p.w = 500
            elif p.is_lost or p.glitch_type is not None:
                # Reset to original position if not chaos (to be safe)
                p.x = p.orig_x
                p.y = p.orig_y

        for d in self.doors:
            d.glow_t += dt
            d.active = True

        # Use a global timer for synchronized blinking
        if not hasattr(self, "glow_t_accum"):
            self.glow_t_accum = 0.0
        self.glow_t_accum += dt

        for c in self.cables:
            c.timer -= dt

        # Neural Pulse logic for Level 5
        self.pulse_timer -= dt
        if self.pulse_timer <= 0:
            self.pulse_timer = 3.0
            for p in self.platforms:
                if p.is_hidden:
                    p.reveal_t = 0.8  # Reveal for 0.8 seconds
                    # Emit a pulse effect at platform
                    particles.emit(
                        Vec2(p.x + p.w / 2, p.y + p.h / 2),
                        10,
                        skia.Color(100, 255, 200, 150),
                    )

        for p in self.platforms:
            if p.reveal_t > 0:
                p.reveal_t -= dt

    def get_visible_platforms(
        self, player_memory_percent: float, fragments_collected: int = 0
    ):
        # We need self.glow_t_accum for synchronized blinking in collision check too
        t = getattr(self, "glow_t_accum", 0.0)

        visible = []
        for p in self.platforms:
            is_visible_req = (
                p.memory_req is None or player_memory_percent <= p.memory_req
            )
            is_visible_min = (
                p.memory_min is None or player_memory_percent >= p.memory_min
            )
            is_visible_frag = (
                p.fragment_req is None or fragments_collected >= p.fragment_req
            )

            is_visible_blink = True
            if p.blink_freq is not None:
                freq = p.blink_freq * (0.2 + player_memory_percent * 2.0)
                is_visible_blink = math.sin(t * freq) > 0

            if (
                is_visible_req
                and is_visible_min
                and is_visible_frag
                and is_visible_blink
            ):
                if not p.is_hidden or p.reveal_t > 0:
                    visible.append(p)
        return visible

    def resolve_rect_vs_static(self, body, width, height, static_rects):
        return resolve_rect_vs_static(body, width, height, static_rects)

    def resolve_level_collision(
        self,
        player_body: RigidBody,
        player_width: float,
        player_height: float,
        player_memory_percent: float,
        world_corruption: float = 0.0,
        fragments_collected: int = 0,
    ) -> tuple:
        visible = self.get_visible_platforms(player_memory_percent, fragments_collected)
        collision_rects = []
        for p in visible:
            if p.temp_corrupt_t > 0 and not p.is_permanent:
                continue
            scale_w = 1.0 - (world_corruption * 0.2)
            nw = p.w * scale_w
            nx = p.x + (p.w - nw) / 2
            collision_rects.append((nx, p.y, nw, p.h))

        return resolve_rect_vs_static(
            player_body, player_width, player_height, collision_rects
        )

    def _render_dialog_box(self, canvas: skia.Canvas, text: str):
        margin = 100
        box_h = 80
        box_y = self.h - box_h - 450  # Higher up
        rect = skia.Rect.MakeXYWH(margin, box_y, self.w - margin * 2, box_h)

        # Background
        bg_paint = skia.Paint(
            Color=skia.Color(0, 0, 0, 200), Style=skia.Paint.kFill_Style
        )
        canvas.drawRect(rect, bg_paint)

        # Border
        border_paint = skia.Paint(
            Color=skia.Color(0, 255, 255, 150),
            Style=skia.Paint.kStroke_Style,
            StrokeWidth=2,
        )
        canvas.drawRect(rect, border_paint)

        # Text
        text_paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
        text_font = skia.Font(self.typeface, 20)
        # Simple word wrap or just centering for now (assuming short text)
        text_w = text_font.measureText(text)
        canvas.drawString(
            text, self.w / 2 - text_w / 2, box_y + box_h / 2 + 7, text_font, text_paint
        )

    def render(
        self,
        canvas,
        t: float,
        player_memory_percent: float,
        particles,
        world_corruption: float = 0.0,
        is_glitched: bool = False,
        hide_tutorial: bool = False,
        fragments_collected: int = 0,
    ):
        pa = skia.Paint(Style=skia.Paint.kFill_Style)

        if is_glitched:
            # Draw a subtle purple/glitchy tint to the background
            tint_pa = skia.Paint(Color=skia.Color(40, 0, 60, 40))
            canvas.drawRect(skia.Rect.MakeXYWH(0, 0, self.w, self.h), tint_pa)

            # Draw some background "static" or scanlines
            line_pa = skia.Paint(Color=skia.Color(100, 100, 255, 20), StrokeWidth=1)
            for i in range(0, self.h, 4):
                canvas.drawLine(0, i + (t * 20 % 4), self.w, i + (t * 20 % 4), line_pa)

        # Render Cables
        cable_pa = skia.Paint(
            Color=skia.Color(50, 50, 70), StrokeWidth=3, Style=skia.Paint.kStroke_Style
        )
        spark_pa = skia.Paint(
            Color=skia.Color(255, 150, 0),
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 3),
        )
        for c in self.cables:
            # Swaying effect
            sway = math.sin(t * 2 + c.x) * 10
            path = skia.Path()
            path.moveTo(c.x, 0)
            path.quadTo(c.x + sway, c.length / 2, c.x, c.length)
            canvas.drawPath(path, cable_pa)

            # Draw terminal/spark point
            canvas.drawCircle(c.x, c.length, 4, spark_pa)
            if random.random() < 0.1:
                particles.emit(
                    Vec2(c.x, c.length), 1, skia.Color(255, 100, 0), speed_range=(5, 20)
                )

        # Render Relays and Beams
        relay_inactive_pa = skia.Paint(
            Color=skia.Color(100, 100, 100, 150), Style=skia.Paint.kFill_Style
        )
        relay_active_pa = skia.Paint(
            Color=skia.Color(0, 200, 255),
            Style=skia.Paint.kFill_Style,
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 5),
        )
        beam_pa = skia.Paint(
            Color=skia.Color(0, 255, 255, 150),
            StrokeWidth=2,
            Style=skia.Paint.kStroke_Style,
            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 2),
        )

        for r in self.relays:
            r.glow_t += 0.01
            # Draw relay box
            curr_pa = relay_active_pa if r.active else relay_inactive_pa
            canvas.drawRect(skia.Rect.MakeXYWH(r.x - 15, r.y - 15, 30, 30), curr_pa)
            # Draw inner detail
            canvas.drawRect(
                skia.Rect.MakeXYWH(r.x - 5, r.y - 5, 10, 10),
                skia.Paint(Color=skia.ColorWHITE),
            )

            if r.active:
                # Draw beam to first door
                if self.doors:
                    d = self.doors[0]
                    canvas.drawLine(r.x, r.y, d.x + d.w / 2, d.y + d.h / 2, beam_pa)
                    if random.random() < 0.2:
                        particles.emit(
                            Vec2(r.x, r.y),
                            1,
                            skia.Color(0, 255, 255),
                            speed_range=(20, 50),
                        )

        # Render Tutorial Text
        if self.tutorial_text and not hide_tutorial:
            text_paint = skia.Paint(
                AntiAlias=True, Color=skia.Color(160, 160, 160)
            )  # Grayer

            # Simple line wrapping
            max_w = self.w - 200
            words = self.tutorial_text.split(" ")
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

            for i, line in enumerate(lines):
                line_w = self.font.measureText(line)
                canvas.drawString(
                    line, self.w / 2 - line_w / 2, 140 + i * 30, self.font, text_paint
                )

        # Render Dialog
        if self.active_dialog:
            self._render_dialog_box(canvas, self.active_dialog)

        self.items.render(canvas)

        visible = self.get_visible_platforms(player_memory_percent, fragments_collected)
        for p in visible:
            rot = (
                math.sin(t * 2 + p.x) * world_corruption * 5
                if world_corruption > 0
                else 0
            )
            if p.glitch_type == "chaos":
                rot += math.sin(p.glitch_t * 10) * 10

            scale_w = 1.0 - (world_corruption * 0.2)

            canvas.save()
            canvas.translate(p.x + p.w / 2, p.y + p.h / 2)
            canvas.rotate(rot)

            if p.is_hidden:
                # Ghostly green appearance for hidden platforms
                alpha = int(255 * (p.reveal_t / 0.8))
                pa.setColor(skia.Color(100, 255, 150, alpha))
                canvas.drawRect(skia.Rect.MakeXYWH(-p.w / 2, -p.h / 2, p.w, p.h), pa)
                # Draw outline
                pa_stroke = skia.Paint(
                    Style=skia.Paint.kStroke_Style,
                    Color=skia.Color(200, 255, 200, alpha),
                    StrokeWidth=1,
                )
                canvas.drawRect(
                    skia.Rect.MakeXYWH(-p.w / 2, -p.h / 2, p.w, p.h), pa_stroke
                )
            elif p.blink_freq is not None:
                # Blinking platforms have an orange/warning tint
                pa.setColor(skia.Color(255, 150, 50, 200))
                canvas.drawRect(skia.Rect.MakeXYWH(-p.w / 2, -p.h / 2, p.w, p.h), pa)
                pa_stroke = skia.Paint(
                    Style=skia.Paint.kStroke_Style,
                    Color=skia.Color(255, 200, 100, 255),
                    StrokeWidth=2,
                )
                canvas.drawRect(
                    skia.Rect.MakeXYWH(-p.w / 2, -p.h / 2, p.w, p.h), pa_stroke
                )
            elif (
                p.is_lost
                or p.memory_req is not None
                or p.memory_min is not None
                or p.fragment_req is not None
                or p.temp_corrupt_t > 0
            ):
                scale = 1.0 - (p.appear_t / 0.5) if p.appear_t > 0 else 1.0
                canvas.scale(scale * scale_w, scale)
                random.seed(
                    int(
                        p.x
                        + p.y
                        + (p.glitch_t * 5 if (p.is_lost or p.temp_corrupt_t > 0) else 0)
                    )
                )
                num_blocks = 5
                block_w = p.w / num_blocks
                for i in range(num_blocks):
                    bx, by = -p.w / 2 + i * block_w, -p.h / 2
                    off_y = random.uniform(-5, 5) if random.random() > 0.7 else 0
                    if p.is_lost or p.temp_corrupt_t > 0:
                        pa.setColor4f(
                            skia.Color4f(
                                random.uniform(0.3, 0.5),
                                random.uniform(0.3, 0.5),
                                random.uniform(0.3, 0.5),
                                1.0,
                            )
                        )
                    else:
                        pa.setColor4f(skia.Color4f(0.4, 0.2, 0.6, 0.8))
                    canvas.drawRect(
                        skia.Rect.MakeXYWH(bx, by + off_y, block_w, p.h), pa
                    )
                line_pa = skia.Paint(Color=skia.Color(255, 255, 255, 60), StrokeWidth=1)
                for _ in range(3):
                    ly = random.uniform(-p.h / 2, p.h / 2)
                    canvas.drawLine(-p.w / 2, ly, p.w / 2, ly, line_pa)
                random.seed()
            else:
                r, g, b = (
                    0.3 + world_corruption * 0.2,
                    0.3 + world_corruption * 0.1,
                    0.3 - world_corruption * 0.1,
                )
                pa.setColor4f(skia.Color4f(r, g, b, 1.0))
                canvas.scale(scale_w, 1.0)
                canvas.drawRect(skia.Rect.MakeXYWH(-p.w / 2, -p.h / 2, p.w, p.h), pa)
            canvas.restore()

        for d in self.doors:
            glow_size = 5 + math.sin(d.glow_t * 5) * 3

            if d.is_locked:
                # Reconstructing/Gray look
                pa_gray = skia.Paint(Color=skia.Color(100, 100, 100, 150))
                pa_outline = skia.Paint(
                    Style=skia.Paint.kStroke_Style,
                    Color=skia.Color(150, 150, 150, 100),
                    StrokeWidth=2,
                )

                # Draw "fragments" of the door
                num_frags = 6
                frag_h = d.h / num_frags
                for i in range(num_frags):
                    off_x = (
                        math.sin(d.glow_t + i) * 5 * (1.0 - d.reconstruction_percent)
                    )
                    canvas.drawRect(
                        skia.Rect.MakeXYWH(
                            d.x + off_x, d.y + i * frag_h, d.w, frag_h - 2
                        ),
                        pa_gray,
                    )

                # Progress bar for reconstruction
                canvas.drawRect(
                    skia.Rect.MakeXYWH(
                        d.x, d.y - 10, d.w * d.reconstruction_percent, 4
                    ),
                    skia.Paint(Color=skia.ColorWHITE),
                )
            else:
                # Active door
                canvas.drawRect(
                    skia.Rect.MakeXYWH(
                        d.x - glow_size,
                        d.y - glow_size,
                        d.w + glow_size * 2,
                        d.h + glow_size * 2,
                    ),
                    skia.Paint(
                        Color=skia.Color(0, 255, 255, 100),
                        MaskFilter=skia.MaskFilter.MakeBlur(
                            skia.kNormal_BlurStyle, glow_size
                        ),
                    ),
                )
                canvas.drawRect(
                    skia.Rect.MakeXYWH(d.x, d.y, d.w, d.h),
                    skia.Paint(Color=skia.Color(0, 50, 50, 200)),
                )
                canvas.drawRect(
                    skia.Rect.MakeXYWH(d.x + 10, d.y + 10, d.w - 20, d.h - 20),
                    skia.Paint(Color=skia.Color(0, 200, 200, 255)),
                )
                if random.random() < 0.2:
                    particles.emit(
                        Vec2(d.x + d.w / 2, d.y + d.h / 2),
                        1,
                        skia.Color(0, 255, 255),
                        speed_range=(10, 50),
                        size_range=(1, 3),
                    )
