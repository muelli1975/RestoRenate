"""Output dimensions, shared by restoration and standalone upscaling."""
from functools import lru_cache
from math import ceil, floor, sqrt

from language import translate
from methods import (COLORIZATION_METHODS, FIBO2_TURBO, FIRERED_LIGHTNING, FLUX2, MICROSOFT,
                     NATIVE_METHODS, QWEN2509_NUNCHAKU, QWEN2511_LIGHTNING, UPSCALING)

NO_RESCALE = 'Ohne Nachskalierung'
DOUBLE_SIZE = '2×'
QUADRUPLE_SIZE = '4×'
FULL_HD = '1080 px Bildhöhe'
ULTRA_HD = '2160 px Bildhöhe'
CUSTOM_SIZE = 'Lange Seite'
SHORT_SIDE = 'Kurze Seite'
CUSTOM_SIZES = (CUSTOM_SIZE, SHORT_SIDE)
SIZE_CHOICES = (NO_RESCALE, DOUBLE_SIZE, QUADRUPLE_SIZE, FULL_HD, ULTRA_HD, *CUSTOM_SIZES)
MAX_PIXELS = 60_000_000
MAX_SIDE = 16_384

# ComfyUI FluxKontextImageScale sizes used by the Qwen 2511 and FireRed workflows.
KONTEXT_RESOLUTIONS = (
    (672, 1568), (688, 1504), (720, 1456), (752, 1392), (800, 1328),
    (832, 1248), (880, 1184), (944, 1104), (1024, 1024), (1104, 944),
    (1184, 880), (1248, 832), (1328, 800), (1392, 752), (1456, 720),
    (1504, 688), (1568, 672),
)


def size_choices(method):
    return SIZE_CHOICES[1:] if method == UPSCALING else SIZE_CHOICES


def method_size(method, requested):
    if requested in size_choices(method):
        return requested
    return NO_RESCALE if method in COLORIZATION_METHODS else ULTRA_HD


def limited_size(size, *, max_pixels=None, max_side=None):
    width, height = size
    factor = min(1.0, max_side / max(size)) if max_side else 1.0
    if max_pixels is not None:
        factor = min(factor, sqrt(max_pixels / (width * height)))
    return max(1, round(width * factor)), max(1, round(height * factor))


@lru_cache(maxsize=128)
def fibo_canvas(original):
    # Match TextEncodeFibo2's automatic size selection in ComfyUI v0.44.0.
    area = 1024 * 1024
    aspect = original[0] / original[1]
    sizes = (
        (width, height)
        for width in range(64, 2 * area // 64, 16)
        for height in range(max(64, 16 * ceil(0.9 * area / width / 16)),
                            16 * floor(1.1 * area / width / 16) + 1, 16)
    )
    return min(sizes, key=lambda size: (
        round(1 - min(size[0] / size[1] / aspect, aspect * size[1] / size[0]), 9),
        abs(size[0] * size[1] - area), -size[0],
    ))


def restoration_canvas(original, method):
    if method == FIBO2_TURBO:
        return fibo_canvas(original)
    if method in (QWEN2511_LIGHTNING, FIRERED_LIGHTNING):
        aspect = original[0] / original[1]
        return min(KONTEXT_RESOLUTIONS, key=lambda size: abs(aspect - size[0] / size[1]))
    return None


def restoration_size(original, method):
    if method in NATIVE_METHODS:
        return original
    if method == MICROSOFT:
        return limited_size(original, max_side=2048)
    if method in (FLUX2, QWEN2509_NUNCHAKU):
        # Both reference workflows use ImageScaleToTotalPixels at 1 MP.
        width, height = original
        factor = sqrt((1024 * 1024) / (width * height))
        return max(1, round(width * factor)), max(1, round(height * factor))
    canvas = restoration_canvas(original, method)
    if canvas is not None:
        width, height = original
        canvas_width, canvas_height = canvas
        factor = min(canvas_width / width, canvas_height / height)
        return max(1, round(width * factor)), max(1, round(height * factor))
    return limited_size(original, max_pixels=1_000_000)


def needs_enlargement(current, target):
    return target[0] > current[0] or target[1] > current[1]


def output_size(original, choice=ULTRA_HD, side_pixels=2160, *, method):
    width, height = original
    if choice == NO_RESCALE:
        result = restoration_size(original, method)
    else:
        if choice in (DOUBLE_SIZE, QUADRUPLE_SIZE):
            factor = 2 if choice == DOUBLE_SIZE else 4
        elif choice in CUSTOM_SIZES:
            if not 1 <= side_pixels <= MAX_SIDE:
                raise ValueError(translate('Bitte eine Seitenlänge zwischen 1 und {0} px eingeben.', MAX_SIDE))
            reference = min(original) if choice == SHORT_SIDE else max(original)
            factor = side_pixels / reference
        else:
            factor = (1080 if choice == FULL_HD else 2160) / height
        result = max(1, round(width * factor)), max(1, round(height * factor))
    if max(result) > MAX_SIDE or result[0] * result[1] > MAX_PIXELS:
        raise ValueError(translate('Die Zielgröße überschreitet 16.384 px pro Seite oder 60 Megapixel.'))
    return result
