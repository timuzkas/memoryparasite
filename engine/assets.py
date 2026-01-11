import skia

from engine.file import FileManager, SpriteSheet
from engine.sound import SoundManager
from lib import tlog


class AssetManager:
    _instance = None

    def __init__(self):
        self.files = FileManager.get()
        self.audio = SoundManager.get()
        self.images = {}
        self.spritesheets = {}
        self.fonts = {}
        self._default_font = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = AssetManager()
        return cls._instance

    def load_image(self, path: str, key: str = None) -> skia.Image:
        key = key or path
        if key in self.images:
            return self.images[key]

        img = self.files.load_image(path)
        if img:
            self.images[key] = img
            tlog.info(f"AssetManager: Loaded image '{key}'")
        return img

    def get_image(self, key: str) -> skia.Image:
        return self.images.get(key)

    def load_spritesheet(
        self, path: str, frame_w: int, frame_h: int, offset: int = 0, key: str = None
    ) -> SpriteSheet:
        key = key or path
        if key in self.spritesheets:
            return self.spritesheets[key]

        sheet = self.files.load_spritesheet(path, frame_w, frame_h, offset)
        if sheet:
            self.spritesheets[key] = sheet
            tlog.info(f"AssetManager: Loaded spritesheet '{key}'")
        return sheet

    def load_sound(self, path: str, key: str = None):
        self.audio.load(path, key)

    def play_sound(self, key: str, volume: float = 1.0):
        self.audio.play(key, volume)

    def get_font(self, name: str, size: float) -> skia.Font:
        k = f"{name}_{size}"
        if k in self.fonts:
            return self.fonts[k]

        tf = skia.Typeface.MakeFromName(name, skia.FontStyle.Normal())
        if not tf:
            tf = skia.Typeface.MakeDefault()

        font = skia.Font(tf, size)
        self.fonts[k] = font
        return font
