"""StereoFine's display-referred RGB Cube tables and strength interpolation (MIT)."""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from PIL import ImageFilter

from portable_paths import ROOT


@dataclass(frozen=True)
class Look:
    key: str
    strength: int

    def record(self):
        return {'id': self.key, 'strength': self.strength}


@dataclass(frozen=True)
class ColorLUT:
    table: np.ndarray
    domain_min: tuple
    domain_max: tuple


def read_cube(path: Path) -> ColorLUT:
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError('LUT file is too large.')
    raw = path.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    size = None
    lower, upper = (0., 0., 0.), (1., 1., 1.)
    values = []
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.partition('#')[0].strip().split()
        if not fields:
            continue
        key = fields[0]
        if key == 'TITLE':
            continue
        if key == 'LUT_3D_SIZE':
            if size is not None or len(fields) != 2:
                raise ValueError('Invalid LUT_3D_SIZE.')
            size = int(fields[1])
            if not 2 <= size <= 129:
                raise ValueError('Supported 3D LUT sizes: 2 through 129.')
            continue
        if key in ('DOMAIN_MIN', 'DOMAIN_MAX'):
            if len(fields) != 4:
                raise ValueError('Invalid LUT domain.')
            vector = tuple(map(float, fields[1:]))
            if key == 'DOMAIN_MIN': lower = vector
            else: upper = vector
            continue
        if key == 'LUT_1D_SIZE':
            raise ValueError('This file contains a 1D LUT; a 3D LUT is required.')
        if len(fields) != 3:
            raise ValueError(f'Invalid LUT data on line {number}.')
        try:
            values.append(tuple(map(float, fields)))
        except ValueError as exc:
            raise ValueError(f'Invalid LUT data on line {number}.') from exc
        if len(values) > 129 ** 3:
            raise ValueError('Too many LUT entries.')
    if size is None or len(values) != size ** 3:
        raise ValueError('LUT entry count does not match LUT_3D_SIZE.')
    table = np.asarray(values, dtype=np.float32)
    if not np.isfinite(table).all() or not np.isfinite([lower, upper]).all():
        raise ValueError('LUT contains non-finite values.')
    if not np.all(np.asarray(upper) > lower):
        raise ValueError('LUT domain maximum must exceed minimum.')
    table = table.reshape(size, size, size, 3)
    table.setflags(write=False)
    return ColorLUT(table, lower, upper)


@lru_cache(maxsize=1)
def catalog():
    data = json.loads((ROOT / 'assets/luts/manifest.json').read_text(encoding='utf-8'))
    return {entry['id']: entry for entry in data}


@lru_cache(maxsize=5)
def _table(key):
    return read_cube(ROOT / 'assets/luts' / catalog()[key]['file'])


@lru_cache(maxsize=6)
def _filter(look):
    lut = _table(look.key)
    n = lut.table.shape[0]
    if n > 65 or lut.domain_min != (0., 0., 0.) or lut.domain_max != (1., 1., 1.):
        raise ValueError('Unsupported bundled LUT domain.')
    strength = look.strength / 100
    table = lut.table * strength
    identity = np.linspace(0., 1. - strength, n, dtype=np.float32)
    table[..., 0] += identity[None, None, :]
    table[..., 1] += identity[None, :, None]
    table[..., 2] += identity[:, None, None]
    return ImageFilter.Color3DLUT(n, table.ravel().tolist(), channels=3)


def apply_look(image, look):
    if look is None or look.strength == 0:
        return image.copy()
    return image.filter(_filter(look))
