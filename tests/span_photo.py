"""Verify download identity, model selection, native scale, and a real CPU forward pass."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

import torch
from spandrel import ModelLoader

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from methods import CLEARREALITY, MULTIJPG, PUREPHOTO, UPSCALERS, UPSCALING, model_specs
from model_hints import DESCRIPTIONS

manifest = json.loads((root / "download_manifest.json").read_text())
optional = json.loads((root / "method_downloads.json").read_text())
assert set(DESCRIPTIONS) == set(UPSCALERS)
assert all(len(DESCRIPTIONS[name]) == 2 and all(DESCRIPTIONS[name]) for name in UPSCALERS)
with TemporaryDirectory() as folder, torch.inference_mode():
    for name in (CLEARREALITY, MULTIJPG, PUREPHOTO):
        spec, = model_specs(manifest, optional, UPSCALING, upscaler=name)
        path = Path(folder) / Path(spec["path"]).name
        urlretrieve(spec["url"], path)
        assert path.stat().st_size == spec["size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec["sha256"]
        model = ModelLoader().load_from_file(path).eval()
        assert model.scale == 4
        output = model(torch.rand(1, 3, 24, 32))
        assert output.shape == (1, 3, 96, 128) and torch.isfinite(output).all()
        print(name, model.architecture.name, tuple(output.shape))
