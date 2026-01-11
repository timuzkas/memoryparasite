# Pygu Engine Documentation

## Overview
Pygu is a lightweight 2D game engine built with Python, Skia for 2D rendering, and ModernGL for GPU-accelerated post-processing effects. It is designed for rapid prototyping and small to medium-sized games.

## Core Components

### 1. Engine Initialization
The `CoreEngine` class is the main entry point for the engine. It handles window creation, input management, and the game loop.

**Example:**
```python
from engine.engine import CoreEngine

# Initialize the engine with a window size of 1280x720
engine = CoreEngine(width=1280, height=720, title="My Game")
```

### 2. Components
Components are modular units of functionality that can be added to the engine. They handle initialization, event processing, updates, and rendering.

**Example:**
```python
from engine.component import Component

class MyComponent(Component):
    def __init__(self):
        super().__init__("MyComponent")
    
    def on_init(self, ctx, canvas):
        print("Component initialized")
    
    def on_update(self, dt):
        print(f"Update called with delta time: {dt}")
    
    def on_render_ui(self, canvas):
        # Render logic here
        pass

# Add the component to the engine
engine.add_component(MyComponent())
```

### 3. Sprites
The `Sprite` class allows for rendering images with various transformations such as scaling, rotation, and flipping.

**Example:**
```python
from engine.sprite import Sprite, Rect
import skia

# Load an image
image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName("path/to/image.png"))

# Create a sprite
sprite = Sprite(image, src_rect=Rect(x=0, y=0, w=32, h=32))
sprite.scale = Vec2(2.0, 2.0)
sprite.rotation = 0.5  # Radians

# Render the sprite
sprite.render(canvas, Vec2(100, 100))
```

### 4. Animated Sprites
The `AnimatedSprite` class extends the `Sprite` class to support animations.

**Example:**
```python
from engine.sprite import AnimatedSprite

# Create an animated sprite
animated_sprite = AnimatedSprite(image, frame_width=32, frame_height=32, frame_duration=0.1)

# Add an animation
animated_sprite.add_animation("walk", [0, 1, 2, 3])

# Play the animation
animated_sprite.play("walk", loop=True)

# Update and render the sprite
animated_sprite.update(dt)
animated_sprite.render(canvas, Vec2(100, 100))
```

### 5. Physics
The `PhysicsWorld` class manages rigid bodies and their interactions.

**Example:**
```python
from engine.physics import PhysicsWorld, RigidBody, Vec2

# Create a physics world
world = PhysicsWorld(gravity=Vec2(0, 9.8))

# Create a rigid body
body = RigidBody(position=Vec2(100, 100), velocity=Vec2(0, 0), mass=1.0)

# Add the body to the world
world.add_body(body)

# Update the physics world
world.update(dt)
```

### 6. Collision Detection
The `CollisionWorld` class handles collision detection between circles and rectangles.

**Example:**
```python
from engine.collision import CollisionWorld
from engine.physics import RigidBody, Vec2

# Create a collision world
collision_world = CollisionWorld()

# Create rigid bodies
body1 = RigidBody(position=Vec2(100, 100))
body2 = RigidBody(position=Vec2(150, 150))

# Add bodies to the collision world
collision_world.add_circle(body1, radius=20)
collision_world.add_circle(body2, radius=20)

# Check and resolve collisions
collision_world.check_and_resolve()
```

### 7. Particle System
The `ParticleSystem` class allows for creating and managing particle effects.

**Example:**
```python
from engine.particles import ParticleSystem
from engine.physics import Vec2

# Create a particle system
particle_system = ParticleSystem()

# Emit particles
particle_system.emit(Vec2(100, 100), count=10, color=skia.ColorRED, speed_range=(50, 200), life_range=(0.3, 0.8), size_range=(2, 6))

# Update and render particles
particle_system.update(dt)
particle_system.render(canvas)
```

### 8. Post-Processing Effects
The `PostProcessSystem` class manages post-processing effects such as screen shake and glitch effects.

**Example:**
```python
from engine.effects import PostProcessSystem

# Create a post-processing system
post_process = PostProcessSystem(engine)

# Trigger effects
post_process.trigger_shake(5.0)
post_process.trigger_glitch(1.0)

# Update the post-processing system
post_process.update(dt)
```

### 9. Asset Management
The `AssetManager` class handles loading and managing assets such as images, spritesheets, sounds, and fonts.

**Example:**
```python
from engine.assets import AssetManager

# Get the asset manager instance
asset_manager = AssetManager.get()

# Load an image
image = asset_manager.load_image("path/to/image.png", "my_image")

# Load a spritesheet
spritesheet = asset_manager.load_spritesheet("path/to/spritesheet.png", frame_w=32, frame_h=32, key="my_spritesheet")

# Load a sound
asset_manager.load_sound("path/to/sound.wav", "my_sound")

# Play a sound
asset_manager.play_sound("my_sound", volume=1.0)
```

### 10. File Management
The `FileManager` class handles loading files such as JSON, XML, and images.

**Example:**
```python
from engine.file import FileManager

# Get the file manager instance
file_manager = FileManager.get()

# Load a JSON file
data = file_manager.load_json("path/to/data.json")

# Load an XML file
root = file_manager.load_xml("path/to/data.xml")

# Load an image
image = file_manager.load_image("path/to/image.png")
```

### 11. Sound Management
The `SoundManager` class handles loading and playing sounds.

**Example:**
```python
from engine.sound import SoundManager

# Get the sound manager instance
sound_manager = SoundManager.get()

# Load a sound
sound_manager.load("path/to/sound.wav", "my_sound")

# Play a sound
sound_manager.play("my_sound", volume=1.0)
```

### 12. Animation
The `Animator` class handles tweening and animations.

**Example:**
```python
from engine.animation import Animator, AnimationCurve

# Create an animator
animator = Animator()

# Create a tween
animator.to(start=0.0, end=1.0, duration=1.0, curve=AnimationCurve.EASE_IN_OUT)

# Update the animator
animator.update(dt)
```

### 13. Shaders
The engine includes several built-in shaders for post-processing effects.

**Example:**
```python
from engine.shaders import DEFAULT_VERT, DEFAULT_FRAG, GLITCH_FRAG, CRT_FRAG, VHS_FRAG

# Use a shader in the engine
engine.set_active_shader("glitch")
```

## Game Loop
The main game loop is managed by the `CoreEngine` class. It handles input, updates, and rendering.

**Example:**
```python
import glfw
import time

# Main game loop
last_time = time.time()
while not glfw.window_should_close(engine.window):
    # Calculate delta time
    current_time = time.time()
    dt = current_time - last_time
    last_time = current_time

    # Update
    engine.update(dt)

    # Render
    engine.render()

    # Swap buffers and poll events
    glfw.swap_buffers(engine.window)
    glfw.poll_events()
```

## Conclusion
This documentation covers the core components and features of the Pygu engine. For more detailed information, refer to the source code and comments within each module.