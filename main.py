import time

import glfw
import moderngl
import skia

from engine.effects import PostProcessSystem
from engine.engine import CoreEngine
from game.game import MemoryParasiteGame


def main():
    engine = CoreEngine(width=1280, height=720, title="Memory Parasite")
    post_process = PostProcessSystem(engine)
    game = MemoryParasiteGame()
    game.post_process = post_process
    engine.add_component(game)

    last_time = time.perf_counter()

    while not engine.window or not glfw.window_should_close(engine.window):
        current_time = time.perf_counter()
        dt = current_time - last_time
        last_time = current_time

        post_process.update(dt)
        game.on_update(dt)

        canvas = engine.surface.getCanvas()
        canvas.clear(skia.ColorBLACK)

        canvas.save()
        if engine.canvas_offset != (0, 0):
            canvas.translate(engine.canvas_offset[0], engine.canvas_offset[1])
        game.on_render_ui(canvas)
        canvas.restore()

        engine.fps = 1.0 / dt if dt > 0 else 60
        # engine._render_fps(canvas)

        engine._update_shader_uniforms(dt)
        engine._upload_skia_to_texture()

        engine.ctx.enable(moderngl.BLEND)
        engine.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # Pass 1: VHS
        engine.fbo.use()
        engine.ctx.clear(0, 0, 0, 0)
        engine.ui_texture.use(0)
        engine.blit_vaos["vhs"].render(moderngl.TRIANGLE_STRIP)

        # Pass 2: Matrix
        engine.fbo2.use()
        engine.ctx.clear(0, 0, 0, 0)
        engine.temp_texture.use(0)
        engine.screen_vaos["matrix"].render(moderngl.TRIANGLE_STRIP)

        # Pass 3: CRT
        engine.ctx.screen.use()
        engine.ctx.clear(0, 0, 0, 1)
        engine.temp_texture2.use(0)
        engine.screen_vaos["crt"].render(moderngl.TRIANGLE_STRIP)

        glfw.swap_buffers(engine.window)
        glfw.poll_events()
        engine.run_heartbeat()

    glfw.terminate()


if __name__ == "__main__":
    main()
