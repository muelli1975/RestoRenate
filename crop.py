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


def fit_aspect(box: Box, size: tuple[int, int], aspect: Aspect) -> Box:
    """Keep the center where possible and snap to an exact integer aspect."""
    width, height = box_size(box)
    aw, ah = aspect
    preferred = round(sqrt(width * height / (aw * ah)))
    units = clamp(preferred, 1, min(size[0] // aw, size[1] // ah))
    width, height = units * aw, units * ah
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
        limit = min(max_width // aw, max_height // ah)
        if not limit:
            return None
        # Project the pointer onto the line defined by the locked aspect.
        units = round((max(0, dx) * aw + max(0, dy) * ah) / (aw * aw + ah * ah))
        units = clamp(units, 1, limit)
        width, height = units * aw, units * ah
    else:
        if (horizontal and not max_width) or (vertical and not max_height):
            return None
        width = clamp(dx, 1, max_width)
        height = clamp(dy, 1, max_height)
    left, right = sorted((x, x + horizontal * width)) if horizontal else (box[0], box[2])
    top, bottom = sorted((y, y + vertical * height)) if vertical else (box[1], box[3])
    return left, top, right, bottom
