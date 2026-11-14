"""CPU inference for DDColor and DeOldify colorization."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

from methods import DDCOLOR, DEOLDIFY_METHODS

SRGB = ImageCms.createProfile('sRGB')
LAB = ImageCms.createProfile('LAB')
TO_LAB = ImageCms.buildTransform(SRGB, LAB, 'RGB', 'LAB')
TO_RGB = ImageCms.buildTransform(LAB, SRGB, 'LAB', 'RGB')


class Colorizer:
    def __init__(self, model_path, *, method=DDCOLOR):
        import onnxruntime as ort

        self.model_name = Path(model_path).name
        self.deoldify = method in DEOLDIFY_METHODS
        options = ort.SessionOptions()
        options.enable_cpu_mem_arena = False
        self.session = ort.InferenceSession(str(model_path), sess_options=options, providers=['CPUExecutionProvider'])
        self.input = self.session.get_inputs()[0]
        fallback = 256 if self.deoldify else 512
        _, _, height, width = self.input.shape
        self.size = tuple(side if isinstance(side, int) and side > 0 else fallback
                          for side in (width, height))

    def process(self, original):
        if self.deoldify:
            gray_rgb = original.convert('L').resize(self.size, Image.Resampling.LANCZOS).convert('RGB')
        else:
            grayscale = ImageCms.applyTransform(original.resize(self.size, Image.Resampling.LANCZOS), TO_LAB).getchannel('L')
            neutral = Image.new('L', self.size, 128)
            gray_rgb = ImageCms.applyTransform(Image.merge('LAB', (grayscale, neutral, neutral)), TO_RGB)
        data = np.asarray(gray_rgb, dtype=np.float32).transpose(2, 0, 1)[None]
        if not self.deoldify:
            data /= 255
        prediction = self.session.run(None, {self.input.name: np.ascontiguousarray(data)})[0][0]
        if self.deoldify:
            # DeOldify exports RGB in 0–255. Only its chroma is used in the result.
            rgb = Image.fromarray(np.clip(np.moveaxis(prediction, 0, -1), 0, 255).astype(np.uint8))
            chroma = ImageCms.applyTransform(rgb, TO_LAB).split()[1:]
        else:
            chroma = [Image.fromarray(np.clip(np.rint(channel + 128), 0, 255).astype(np.uint8))
                      for channel in prediction]
        # Keep the scan's original lightness and all of its spatial detail.
        luminance = ImageCms.applyTransform(original, TO_LAB).getchannel('L')
        bands = (luminance, *(channel.resize(original.size, Image.Resampling.BICUBIC) for channel in chroma))
        return ImageCms.applyTransform(Image.merge('LAB', bands), TO_RGB)
