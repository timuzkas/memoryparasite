import json, os, sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import skia
from lib import tlog

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

@dataclass
class SpriteSheet:
    image: skia.Image; frame_width: int; frame_height: int; offset: int; rows: int; cols: int
    def get_frame(self, index: int) -> skia.Image:
        c, r = index % self.cols, index // self.cols
        subset = skia.IRect.MakeXYWH(c * (self.frame_width + self.offset), r * (self.frame_height + self.offset), self.frame_width, self.frame_height)
        return self.image.makeSubset(subset)

class FileManager:
    _instance = None
    @classmethod
    def get(cls):
        if cls._instance is None: cls._instance = FileManager()
        return cls._instance
    def load_json(self, path):
        try:
            with open(resource_path(path), "r") as f: return json.load(f)
        except Exception as e: tlog.err(f"FileManager: JSON fail {path}: {e}"); return None
    def load_xml(self, path):
        try: return ET.parse(resource_path(path)).getroot()
        except Exception as e: tlog.err(f"FileManager: XML fail {path}: {e}"); return None
    def load_image(self, path):
        fp = resource_path(path)
        if not os.path.exists(fp): return None
        try: return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(fp))
        except Exception as e: tlog.err(f"FileManager: Image fail {path}: {e}"); return None
    def load_spritesheet(self, path, frame_w, frame_h, offset=0):
        img = self.load_image(path)
        if not img: return None
        cols, rows = img.width() // frame_w, img.height() // frame_h
        return SpriteSheet(img, frame_w, frame_h, offset, rows, cols)