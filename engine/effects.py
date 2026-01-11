import random

class PostProcessSystem:
    def __init__(self, engine):
        self.engine = engine
        self.shake = 0.0
        self.glitch = 0.0
        self.time = 0.0

    def update(self, dt: float):
        self.time += dt
        self.shake = max(0.0, self.shake - dt * 10.0)
        self.glitch = max(0.0, self.glitch - dt * 2.0)
        
        if hasattr(self.engine, 'post_process_uniforms'):
            self.engine.post_process_uniforms['time'] = self.time
            self.engine.post_process_uniforms['intensity'] = self.glitch
        
        if hasattr(self.engine, 'canvas_offset'):
            if self.shake > 0:
                self.engine.canvas_offset = (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake))
            else:
                self.engine.canvas_offset = (0, 0)

    def trigger_shake(self, amount: float):
        self.shake = max(self.shake, amount)

    def trigger_glitch(self, amount: float):
        self.glitch = max(self.glitch, amount)
        
    def set_effect(self, effect_name: str):
        if hasattr(self.engine, 'set_active_shader'):
            self.engine.set_active_shader(effect_name)