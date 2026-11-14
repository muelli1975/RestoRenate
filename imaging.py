"""Photo preparation, colour-managed output and metadata transfer."""
from __future__ import annotations

from hashlib import sha256
import io
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageCms, ImageOps, PngImagePlugin

from language import translate
from export_metadata import compact, png_metadata

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.bmp', '.avif'}
FORMATS = {
    'JPEG 95 · 4:4:4': ('JPEG', '.jpg'),
    'PNG': ('PNG', '.png'),
    'TIFF': ('TIFF', '.tif'),
}
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
INVALIDATED_TAGS = (
    'IFD1:all', 'SubIFD:all', 'ThumbnailImage', 'PreviewImage', 'OtherImage',
    'JpgFromRaw', 'MakerNotes', 'Orientation', 'ImageWidth', 'ImageLength',
    'ImageHeight', 'ExifImageWidth', 'ExifImageHeight', 'ColorSpace',
    'StripOffsets', 'StripByteCounts', 'TileOffsets', 'TileByteCounts',
    'BitsPerSample', 'Compression', 'PhotometricInterpretation',
    'SamplesPerPixel', 'PlanarConfiguration', 'YCbCrSubSampling',
)


def photo_size(path, *, rotation=0):
    """Read the dimensions in display orientation without decoding pixels."""
    with Image.open(path) as source:
        # Pillow already exposes the oriented dimensions for TIFF.
        swap = source.format != 'TIFF' and source.getexif().get(274) in (5, 6, 7, 8)
        return source.size[::-1] if swap != bool(rotation % 2) else source.size


def open_photo(path, *, crop=None, rotation=0):
    """Return upright, sRGB pixels and optional original resolution metadata."""
    with Image.open(path) as source:
        upright = ImageOps.exif_transpose(source)
        if rotation:
            with upright:
                upright = upright.transpose({
                    1: Image.Transpose.ROTATE_270,
                    2: Image.Transpose.ROTATE_180,
                    3: Image.Transpose.ROTATE_90,
                }[rotation])
        if crop is not None:
            with upright:
                if upright.size != crop.original_size:
                    raise ValueError(translate('Die Bildgröße hat sich geändert. Bitte den Beschnitt neu wählen.'))
                upright = upright.crop(crop.box)
        dpi = source.info.get('dpi')
        if dpi and rotation % 2:
            dpi = dpi[::-1]
        profile = source.info.get('icc_profile')
        alpha = (upright.convert('RGBA').getchannel('A')
                 if 'A' in upright.getbands() or 'transparency' in upright.info else None)
        if profile:
            rgb_source = upright if upright.mode in ('RGB', 'CMYK', 'L', 'LAB') else upright.convert('RGB')
            try:
                rgb = ImageCms.profileToProfile(
                    rgb_source, ImageCms.ImageCmsProfile(io.BytesIO(profile)), SRGB, outputMode='RGB',
                )
            except (OSError, ValueError, ImageCms.PyCMSError) as exc:
                raise ValueError(translate('Das eingebettete Farbprofil konnte nicht nach sRGB umgerechnet werden.')) from exc
        else:
            rgb = upright.convert('RGB')
        if alpha is not None:
            rgb = Image.composite(rgb, Image.new('RGB', rgb.size, 'white'), alpha)
        rgb.info.clear()
        return rgb, dpi


def prepare(image, size, *, alignment=16, canvas=None):
    """Resize and center the photo on the working canvas, retaining its crop."""
    width, height = size
    if image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    if canvas is None:
        pad_w, pad_h = (-width) % alignment, (-height) % alignment
    else:
        pad_w, pad_h = canvas[0] - width, canvas[1] - height
    x, y = pad_w // 2, pad_h // 2
    if pad_w or pad_h:
        padded = np.pad(np.asarray(image), ((y, pad_h - y), (x, pad_w - x), (0, 0)), mode='edge')
        image = Image.fromarray(padded)
    return image, (x, y, width, height)


def exiftool_executable(root):
    executable = 'exiftool.exe' if os.name == 'nt' else 'exiftool'
    path = root / 'tools/exiftool' / executable
    if path.is_file():
        return path
    raise FileNotFoundError(translate('ExifTool fehlt. Bitte die portable ZIP vollständig entpacken.'))


def copy_metadata(exiftool, source, destination, size, settings=None):
    # UTF-8 arguments via stdin support Windows paths outside the system code page.
    # Geometry and the sRGB profile belong to the processed pixels.
    width, height = size
    args = ['-overwrite_original', '-TagsFromFile', str(source.resolve())]
    args.append('-EXIF:all')
    config = []
    if destination.suffix.lower() == '.jpg':
        if source.suffix.lower() == '.png':
            args.extend((
                '-XMP-dc:Title<PNG:Title', '-XMP-dc:Creator<PNG:Author',
                '-XMP-dc:Description<PNG:Description', '-XMP-dc:Rights<PNG:Copyright',
                '-XMP-xmp:CreatorTool<PNG:Software',
            ))
        args.extend(('-IPTC:all', '-XMP:all', '-Comment'))
        if settings:
            config = ['-config', str(Path(__file__).with_name('exiftool_restorenate.config'))]
            args.append('--XMP-restorenate:Settings')
    args.extend((
        *('--' + tag for tag in INVALIDATED_TAGS),
        '-IFD0:Orientation#=1', '-ExifIFD:ColorSpace#=1',
        f'-ExifIFD:ExifImageWidth={width}', f'-ExifIFD:ExifImageHeight={height}',
    ))
    if config:
        args.append('-XMP-restorenate:Settings=' + compact(settings))
    args.append(str(destination.resolve()))
    if any('\n' in arg or '\r' in arg for arg in args):
        raise ValueError(translate('Dateipfade mit Zeilenumbrüchen werden von ExifTool nicht unterstützt.'))
    result = subprocess.run(
        [str(exiftool), *config, '-charset', 'filename=UTF8', '-api', 'WindowsLongPath=1', '-@', '-'],
        input=('\n'.join(args) + '\n').encode('utf-8'),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    details = result.stderr.decode('utf-8', 'replace').strip()
    if result.returncode:
        raise RuntimeError(translate(
                               'Metadaten konnten nicht übernommen werden: {0}',
                               details or result.returncode,
                           ))
    return '\n'.join(line for line in details.splitlines()
                     if not line.startswith('Warning: No writable tags set from '))


def commit_result(temp, folder, stem, labels):
    encoded_stem = stem.encode('utf-8')
    digest = sha256(stem.casefold().encode('utf-8')).hexdigest()
    # Leave room for the sequence, both model labels and the extension.
    if len(encoded_stem) > 200:
        stem = encoded_stem[:188].decode('utf-8', errors='ignore') + '-' + digest[:10]

    extensions = {suffix for _, suffix in FORMATS.values()}
    pattern = re.compile(rf'{re.escape(stem.casefold())}_([0-9]{{2,}})(?:_[a-z0-9.-]+){{0,2}}')

    def last_number():
        return max((int(match[1]) for path in folder.iterdir()
                    if path.suffix.lower() in extensions
                    and (match := pattern.fullmatch(path.stem.casefold()))
                    and path.is_file()), default=0)

    number = last_number() + 1
    for _ in range(100_000):
        # The reservation is shared by all models and formats for this image stem.
        reservation = folder / f'.fotorestaurierung-{digest[:20]}-{number}.lock'
        try:
            reservation.mkdir()
        except FileExistsError:
            number += 1
            continue
        try:
            # Another exporter may have committed the number before we acquired it.
            current = last_number()
            if current >= number:
                number = current + 1
                continue
            name = '_'.join((stem, f'{number:02d}', *labels))
            output = folder / (name + temp.suffix)
            if os.name == 'nt':
                temp.rename(output)
            else:
                os.link(temp, output)
            return output
        except FileExistsError:
            number += 1
        finally:
            reservation.rmdir()
    raise FileExistsError(translate('Für dieses Bild ist keine freie Dateinummer verfügbar.'))


def save_result(image, source, folder, output_format, dpi, exiftool,
                *, settings=None, graph=None, definitions=None, labels=()):
    encoding, suffix = FORMATS[output_format]
    if encoding == 'PNG':
        png_info = PngImagePlugin.PngInfo()
        for key, value in png_metadata(settings or {}, graph, definitions or {}, source.name).items():
            png_info.add_text(key, value)
        # Pillow otherwise reuses a source profile or transparency from image.info.
        options = {'pnginfo': png_info, 'icc_profile': None, 'transparency': None}
    else:
        options = {'icc_profile': SRGB.tobytes()}
        if encoding == 'JPEG':
            options.update(quality=95, subsampling=0)
        else:
            options['compression'] = 'tiff_lzw'
        if dpi and all(math.isfinite(v) and v > 0 for v in dpi):
            options['dpi'] = dpi
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fotorestaurierung-', dir=folder) as scratch:
        temp = Path(scratch) / ('Ausgabe' + suffix)
        image.save(temp, encoding, **options)
        warnings = '' if encoding == 'PNG' else copy_metadata(exiftool, source, temp, image.size, settings)
        return commit_result(temp, folder, source.stem, labels), warnings


def collect(source):
    if source.is_file() and source.suffix.lower() in EXTENSIONS:
        return [source]
    if source.is_dir():
        return sorted(
            (path for path in source.iterdir() if path.is_file() and path.suffix.lower() in EXTENSIONS),
            key=lambda path: (path.name.casefold(), path.name),
        )
    raise ValueError(translate('Bitte ein unterstütztes Bild oder einen Eingabeordner wählen.'))
