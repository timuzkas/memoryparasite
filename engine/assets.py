import skia
from engine.file import FileManager, SpriteSheet
from engine.sound import SoundManager

class AssetManager:
    _instance = None
    def __init__(self):
        self.files = FileManager.get(); self.audio = SoundManager.get()
        self.images, self.spritesheets, self.fonts = {}, {}, {}

    @classmethod
    def get(cls):
        if cls._instance is None: cls._instance = AssetManager()
        return cls._instance

    def load_image(self, path, key=None):
        key = key or path
        if key in self.images: return self.images[key]
        img = self.files.load_image(path)
        if img: self.images[key] = img
        return img

    def load_spritesheet(self, path, frame_w, frame_h, offset=0, key=None):
        key = key or path
        if key in self.spritesheets: return self.spritesheets[key]
        sheet = self.files.load_spritesheet(path, frame_w, frame_h, offset)
        if sheet: self.spritesheets[key] = sheet
        return sheet

    def load_sound(self, path, key=None): self.audio.load(path, key)
    def play_sound(self, key, volume=1.0): self.audio.play(key, volume)

    def get_font(self, name, size):
        k = f"{name}_{size}"
        if k in self.fonts: return self.fonts[k]
        tf = skia.Typeface.MakeFromName(name, skia.FontStyle.Normal()) or skia.Typeface.MakeDefault()
        font = skia.Font(tf, size); self.fonts[k] = font
        return font