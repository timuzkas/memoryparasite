import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import skia

from lib import tlog


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


@dataclass
class SpriteSheet:
    image: skia.Image
    frame_width: int
    frame_height: int
    offset: int
    rows: int
    cols: int

    def get_frame(self, index: int) -> skia.Image:
        # Note: Extracting sub-images can be expensive if done repeatedly.
        # Prefer using src_rect in rendering.
        # But if needed:
        c = index % self.cols
        r = index // self.cols
        subset = skia.IRect.MakeXYWH(
            c * (self.frame_width + self.offset),
            r * (self.frame_height + self.offset),
            self.frame_width,
            self.frame_height,
        )
        return self.image.makeSubset(subset)


class FileManager:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = FileManager()
        return cls._instance

    def load_json(self, path: str) -> dict:
        full_path = resource_path(path)
        try:
            with open(full_path, "r") as f:
                return json.load(f)
        except Exception as e:
            tlog.err(f"FileManager: Failed to load JSON {full_path}: {e}")
            return None

    def load_xml(self, path: str) -> ET.Element:
        full_path = resource_path(path)
        try:
            tree = ET.parse(full_path)
            return tree.getroot()
        except Exception as e:
            tlog.err(f"FileManager: Failed to load XML {full_path}: {e}")
            return None

    def load_image(self, path: str) -> skia.Image:
        full_path = resource_path(path)
        if not os.path.exists(full_path):
            tlog.err(f"FileManager: Image not found {full_path}")
            return None
        try:
            image = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(full_path))
            return image
        except Exception as e:
            tlog.err(f"FileManager: Failed to decode image {full_path}: {e}")
            return None

    def load_spritesheet(
        self, path: str, frame_w: int, frame_h: int, offset: int = 0
    ) -> SpriteSheet:
        img = self.load_image(path) # load_image already uses resource_path
        if not img:
            return None

        cols = img.width() // frame_w
        rows = img.height() // frame_h
        return SpriteSheet(img, frame_w, frame_h, offset, rows, cols)

