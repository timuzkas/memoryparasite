import skia
import glfw
import time
import moderngl
from engine.engine import CoreEngine
from engine.effects import PostProcessSystem
from game.game import MemoryParasiteGame


def main():
    # Create the engine
    engine = CoreEngine(width=1280, height=720, title="Memory Parasite")

    # Initialize Post Processing
    post_process = PostProcessSystem(engine)

    # Create and add the game component
    game = MemoryParasiteGame()
    # Inject post process system into game so it can trigger effects
    game.post_process = post_process

    engine.add_component(game)

    last_time = time.time()

    while not engine.window or not glfw.window_should_close(engine.window):
        # Calculate delta time
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        # Update
        post_process.update(dt)
        game.on_update(dt)

        # Render
        canvas = engine.surface.getCanvas()
        canvas.clear(skia.ColorBLACK)

        # Apply Screen Shake (Canvas Offset)
        canvas.save()
        if engine.canvas_offset != (0, 0):
            canvas.translate(engine.canvas_offset[0], engine.canvas_offset[1])

        game.on_render_ui(canvas)
        canvas.restore()

        # 4. Post-process and blit with chaining (VHS -> Matrix -> CRT)
        engine._update_shader_uniforms(dt)
        engine._upload_skia_to_texture()

        engine.ctx.enable(moderngl.BLEND)
        engine.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        
        # Pass 1: UI Texture -> VHS shader -> Temp Texture (FBO)
        engine.fbo.use()
        engine.ctx.clear(0, 0, 0, 0)
        engine.ui_texture.use(0)
        engine.blit_vaos["vhs"].render(moderngl.TRIANGLE_STRIP)
        
        # Pass 2: Temp Texture -> Matrix shader -> Temp Texture 2 (FBO2)
        engine.fbo2.use()
        engine.ctx.clear(0, 0, 0, 0)
        engine.temp_texture.use(0)
        engine.screen_vaos["matrix"].render(moderngl.TRIANGLE_STRIP)
        
        # Pass 3: Temp Texture 2 -> CRT shader -> Screen
        engine.ctx.screen.use()
        engine.ctx.clear(0, 0, 0, 1)
        engine.temp_texture2.use(0)
        engine.screen_vaos["crt"].render(moderngl.TRIANGLE_STRIP)

        # FPS tracking
        engine.fps = 1.0 / dt if dt > 0 else 60
        # Draw FPS on top (if we want it unaffected by shader, we should do it separately, 
        # but here we draw to canvas which is shader-affected. That's fine.)
        engine._render_fps(canvas)

        # Swap buffers and poll events
        glfw.swap_buffers(engine.window)
        glfw.poll_events()

        # Heartbeat logging
        engine.run_heartbeat()

    # Cleanup
    glfw.terminate()


if __name__ == "__main__":
    main()
