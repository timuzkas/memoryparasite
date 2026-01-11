import os
import time

import glfw
import moderngl
import numpy as np
import skia

from engine.component import Component, Event, EventType
from engine.shaders import CRT_FRAG, DEFAULT_FRAG, DEFAULT_VERT, GLITCH_FRAG, VHS_FRAG, MATRIX_FRAG
from lib import tlog


class CoreEngine:
    def __init__(self, width=1280, height=720, title="T3 Engine"):
        tlog.init("engine.log")
        self.width, self.height = width, height
        self.mouse_x, self.mouse_y = 0.0, 0.0
        self.keys_pressed = set()
        self.show_fps = True
        self.debug_mode = False
        self.components: list[Component] = []
        self.last_heartbeat = time.perf_counter()
        self.frame_count = 0
        self.fps = 0.0
        self.fps_update_time = 0.0

        # Post Processing State
        self.canvas_offset = (0.0, 0.0)
        self.post_process_time = 0.0
        self.post_process_intensity = 0.0
        self.active_shader = "default"
        self.active_shaders = ["vhs", "matrix", "crt"]
        self.shaders = {}
        self.window = None
        self.ctx = None
        self.surface = None

        with tlog.Span("engine_startup"):
            tlog.info(f"Initializing T3 Engine | Target: {width}x{height}")

            if not glfw.init():
                tlog.err("Critical: GLFW initialization failed")
                raise RuntimeError("GLFW init failed")

            glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
            glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
            glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

            self.window = glfw.create_window(width, height, title, None, None)
            if not self.window:
                tlog.err("Critical: Window creation failed")
                glfw.terminate()
                raise RuntimeError("Window creation failed")

            glfw.make_context_current(self.window)
            glfw.swap_interval(1)
            self._setup_callbacks()

            self.ctx = moderngl.create_context()
            tlog.info(
                f"GPU: {self.ctx.info['GL_RENDERER']} | OpenGL: {self.ctx.info['GL_VERSION']}"
            )

            with tlog.Span("graphics_pipeline_setup"):
                self._init_skia_cpu(width, height)
                self._init_blit_pipeline()
                self._init_fonts()

            tlog.info("Engine Startup Complete")

    def _init_fonts(self):
        candidates = ["Inter", "Roboto", "DejaVu Sans", "Arial", "sans-serif"]
        typeface = None
        for name in candidates:
            typeface = skia.Typeface.MakeFromName(name, skia.FontStyle.Normal())
            if typeface:
                tlog.info(f"Font loaded: {name}")
                break
        self.fps_font = skia.Font(typeface or skia.Typeface.MakeDefault(), 14)

    def _setup_callbacks(self):
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_cursor_pos_callback(self.window, self._on_mouse_move)
        glfw.set_framebuffer_size_callback(self.window, self._on_resize)

    def _on_resize(self, window, width, height):
        if width == 0 or height == 0:
            return
        tlog.info(f"Event: Window Resize -> {width}x{height}")
        self.width, self.height = width, height
        self.ctx.viewport = (0, 0, width, height)
        self._init_skia_cpu(width, height)
        self.ui_texture.release()
        self.ui_texture = self.ctx.texture((width, height), 4)
        self.temp_texture.release()
        self.temp_texture = self.ctx.texture((width, height), 4)
        self.temp_texture2.release()
        self.temp_texture2 = self.ctx.texture((width, height), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.temp_texture])
        self.fbo2 = self.ctx.framebuffer(color_attachments=[self.temp_texture2])

    def _init_skia_cpu(self, w, h):
        self.surface = skia.Surface.MakeRasterN32Premul(w, h)

    def _init_blit_pipeline(self):
        flip_verts = np.array([-1, -1, 0, 1, 1, -1, 1, 1, -1, 1, 0, 0, 1, 1, 1, 0], dtype="f4")
        std_verts = np.array([-1, -1, 0, 0, 1, -1, 1, 0, -1, 1, 0, 1, 1, 1, 1, 1], dtype="f4")
        self.vbo = self.ctx.buffer(flip_verts)
        self.std_vbo = self.ctx.buffer(std_verts)

        shader_configs = {
            "default": DEFAULT_FRAG,
            "glitch": GLITCH_FRAG,
            "crt": CRT_FRAG,
            "vhs": VHS_FRAG,
            "matrix": MATRIX_FRAG,
        }

        for name, frag in shader_configs.items():
            try:
                self.shaders[name] = self.ctx.program(vertex_shader=DEFAULT_VERT, fragment_shader=frag)
            except moderngl.Error as e:
                tlog.err(f"Shader '{name}' compilation failed: {e}")

        self.ui_texture = self.ctx.texture((self.width, self.height), 4)
        self.temp_texture = self.ctx.texture((self.width, self.height), 4)
        self.temp_texture2 = self.ctx.texture((self.width, self.height), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.temp_texture])
        self.fbo2 = self.ctx.framebuffer(color_attachments=[self.temp_texture2])

        self.blit_vaos = {}
        self.screen_vaos = {}
        for name, prog in self.shaders.items():
            self.blit_vaos[name] = self.ctx.vertex_array(prog, [(self.vbo, "2f 2f", "in_pos", "in_uv")])
            self.screen_vaos[name] = self.ctx.vertex_array(prog, [(self.std_vbo, "2f 2f", "in_pos", "in_uv")])

        tlog.info(f"Compiled {len(self.shaders)} shaders")

    @property
    def active_shader_name(self) -> str:
        return self.active_shader

    @property
    def blit_vao(self):
        return self.blit_vaos.get(self.active_shader)

    @property
    def post_process_uniforms(self) -> dict:
        return {"time": self.post_process_time, "intensity": self.post_process_intensity}

    def set_shader(self, name):
        if name in self.shaders:
            self.active_shader = name
            tlog.info(f"Active shader set to: {name}")

    def set_post_process(self, intensity: float):
        self.post_process_intensity = max(0.0, min(1.0, intensity))

    def set_canvas_offset(self, x: float, y: float):
        self.canvas_offset = (x, y)

    def _on_key(self, w, k, s, a, m):
        if k == glfw.KEY_F1 and a == glfw.PRESS:
            self.debug_mode = not self.debug_mode
            tlog.info(f"Debug mode: {self.debug_mode}")
        if a == glfw.PRESS:
            if k == glfw.KEY_F2: self.set_shader("default")
            elif k == glfw.KEY_F3: self.set_shader("glitch")
            elif k == glfw.KEY_F4: self.set_shader("crt")
            elif k == glfw.KEY_F5: self.set_shader("vhs")
            self.keys_pressed.add(k)
            self._dispatch_event(Event(EventType.KEY_PRESS, key=k, mods=m))
        elif a == glfw.RELEASE:
            self.keys_pressed.discard(k)
            self._dispatch_event(Event(EventType.KEY_RELEASE, key=k, mods=m))

    def _on_mouse_button(self, w, b, a, m):
        etype = EventType.MOUSE_PRESS if a == glfw.PRESS else EventType.MOUSE_RELEASE
        self._dispatch_event(Event(etype, button=b, x=self.mouse_x, y=self.mouse_y, mods=m))

    def _on_mouse_move(self, w, x, y):
        self.mouse_x, self.mouse_y = x, y
        self._dispatch_event(Event(EventType.MOUSE_MOVE, x=x, y=y))

    def _dispatch_event(self, event):
        for comp in reversed(self.components):
            if comp.enabled and comp.on_event(event): break

    def _upload_skia_to_texture(self):
        image = self.surface.makeImageSnapshot()
        self.ui_texture.write(image.tobytes())

    def _render_fps(self, canvas: skia.Canvas):
        if not self.show_fps:
            return
        paint = skia.Paint(AntiAlias=True, Color=skia.ColorGREEN)
        canvas.drawString(f"FPS: {int(self.fps)}", 10, 20, self.fps_font, paint)

    def _update_shader_uniforms(self, dt: float):
        self.post_process_time += dt
        for name, prog in self.shaders.items():
            if "time" in prog: prog["time"].value = self.post_process_time
            if "intensity" in prog: prog["intensity"].value = self.post_process_intensity
            if "resolution" in prog: prog["resolution"].value = (self.width, self.height)

    def add_component(self, comp: Component):
        with tlog.Span(f"mounting_{comp.name}"):
            comp.on_init(self.ctx, self.surface.getCanvas())
            self.components.append(comp)

    def run_heartbeat(self):
        now = time.perf_counter()
        if now - self.last_heartbeat >= 5.0:
            tlog.info(f"Heartbeat: FPS: {int(self.fps)} | Components: {len(self.components)}")
            self.last_heartbeat = now

    def run(self):
        tlog.info("Entering main loop")
        self.last_time = time.perf_counter()
        while not glfw.window_should_close(self.window):
            now = time.perf_counter()
            dt = now - self.last_time
            self.last_time = now
            self.fps = 1.0 / dt if dt > 0 else 60

            for comp in self.components:
                if comp.enabled: comp.on_update(dt)

            canvas = self.surface.getCanvas()
            canvas.clear(skia.ColorTRANSPARENT)
            for comp in self.components:
                if comp.enabled: comp.on_render_ui(canvas)
            self._render_fps(canvas)

            self._update_shader_uniforms(dt)
            self._upload_skia_to_texture()

            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

            # Pass 1: UI -> VHS -> Temp
            self.fbo.use()
            self.ctx.clear(0, 0, 0, 0)
            self.ui_texture.use(0)
            self.blit_vaos["vhs"].render(moderngl.TRIANGLE_STRIP)

            # Pass 2: Temp -> Matrix -> Temp2
            self.fbo2.use()
            self.ctx.clear(0, 0, 0, 0)
            self.temp_texture.use(0)
            self.screen_vaos["matrix"].render(moderngl.TRIANGLE_STRIP)

            # Pass 3: Temp2 -> CRT -> Screen
            self.ctx.screen.use()
            self.ctx.clear(0, 0, 0, 1)
            self.temp_texture2.use(0)
            self.screen_vaos["crt"].render(moderngl.TRIANGLE_STRIP)

            glfw.swap_buffers(self.window)
            glfw.poll_events()
            self.run_heartbeat()

        tlog.info("Shutdown")
        glfw.terminate()