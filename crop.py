"""Crop geometry in upright, full-resolution source pixels."""
from dataclasses import dataclass
from fractions import Fraction
from math import sqrt
import re

Box = tuple[int, int, int, int]
Aspect = tuple[int, int]

ASPECTS = ((1, 1), (3, 2), (2, 3), (4, 3), (3, 4), (5, 4), (4, 5), (16, 9), (9, 16))


def box_size(box: Box) -> tuple[int, int]:
    return box[2] - box[0], box[3] - box[1]


def parse_aspect(text: str, size: tuple[int, int]) -> Aspect:
    parts = re.fullmatch(r'\s*([0-9]+(?:[.,][0-9]+)?)\s*:\s*([0-9]+(?:[.,][0-9]+)?)\s*', text)
    invalid = 'Bitte ein positives Seitenverhältnis wie 7:5 eingeben.'
    if parts is None:
        raise ValueError(invalid)
    width, height = (Fraction(value.replace(',', '.')) for value in parts.groups())
    if width <= 0 or height <= 0:
        raise ValueError(invalid)
    aspect = (width / height).as_integer_ratio()
    if aspect[0] > size[0] or aspect[1] > size[1]:
        raise ValueError('Dieses Seitenverhältnis passt nicht in das Bild.')
    return aspect


@dataclass(frozen=True)
class CropRegion:
    original_size: tuple[int, int]
    box: Box
    aspect: Aspect | None = None

    def __post_init__(self):
        if (len(self.original_size) != 2 or len(self.box) != 4
                or any(type(value) is not int for value in (*self.original_size, *self.box))):
            raise ValueError('Invalid crop coordinates')
        width, height = self.original_size
        left, top, right, bottom = self.box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError('Crop is outside the source image')

    @property
    def size(self):
        return box_size(self.box)

    @classmethod
    def from_record(cls, record):
        size, box = record.get('original_size'), record.get('source_crop')
        if isinstance(size, (tuple, list)) and isinstance(box, (tuple, list)):
            try:
                return cls(tuple(size), tuple(box))
            except ValueError:
                pass
        return None


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


def move_box(box: Box, size: tuple[int, int], dx: int, dy: int) -> Box:
    left, top, right, bottom = box
    dx = clamp(dx, -left, size[0] - right)
    dy = clamp(dy, -top, size[1] - bottom)
    return left + dx, top + dy, right + dx, bottom + dy


def aspect_size(scale: float, available: tuple[int, int], aspect: Aspect) -> tuple[int, int]:
    """Fit proportionally before rounding, so the limiting side can touch the image edge."""
    aw, ah = aspect
    max_width, max_height = available
    limit = min(max_width / aw, max_height / ah)
    scale = clamp(scale, min(1, limit), limit)
    return clamp(round(scale * aw), 1, max_width), clamp(round(scale * ah), 1, max_height)


def fit_aspect(box: Box, size: tuple[int, int], aspect: Aspect) -> Box:
    """Keep the center where possible and round the dimensions to pixels."""
    width, height = box_size(box)
    aw, ah = aspect
    width, height = aspect_size(sqrt(width * height / (aw * ah)), size, aspect)
    left = clamp(round((box[0] + box[2] - width) / 2), 0, size[0] - width)
    top = clamp(round((box[1] + box[3] - height) / 2), 0, size[1] - height)
    return left, top, left + width, top + height


def resize_box(box: Box, size: tuple[int, int], handle: tuple[int, int],
               pointer: tuple[int, int], aspect: Aspect | None) -> Box | None:
    """Keep the opposite edge or corner anchored during resizing."""
    horizontal, vertical = handle
    x = box[2] if horizontal < 0 else box[0]
    y = box[3] if vertical < 0 else box[1]
    max_width = x if horizontal < 0 else size[0] - x
    max_height = y if vertical < 0 else size[1] - y
    dx = (pointer[0] - x) * horizontal
    dy = (pointer[1] - y) * vertical
    if aspect:
        aw, ah = aspect
        if not max_width or not max_height:
            return None
        old_width, old_height = box_size(box)
        if (dx, dy) == (old_width, old_height) and old_width and old_height:
            return box
        # Follow the dominant change so a horizontal or vertical drag alone can resize a corner.
        horizontal_change = abs(dx - old_width) / aw
        vertical_change = abs(dy - old_height) / ah
        scale = dx / aw if horizontal_change >= vertical_change else dy / ah
        width, height = aspect_size(scale, (max_width, max_height), aspect)
    else:
        if (horizontal and not max_width) or (vertical and not max_height):
            return None
        width = clamp(dx, 1, max_width)
        height = clamp(dy, 1, max_height)
    left, right = sorted((x, x + horizontal * width)) if horizontal else (box[0], box[2])
    top, bottom = sorted((y, y + vertical * height)) if vertical else (box[1], box[3])
    return left, top, right, bottom
