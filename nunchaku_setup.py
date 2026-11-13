"""App-local installer for the CUDA extension and the single Qwen-Image node."""
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from language import translate
from methods import NUNCHAKU_LOADER

NUNCHAKU_NODE = 'RestoRenate-Nunchaku'
NUNCHAKU_CAPABILITIES = ((8, 0), (8, 6), (8, 9))
NUNCHAKU_GPU_REQUIRED = 'Qwen 2509 Nunchaku INT4 benötigt eine NVIDIA-GPU der RTX-30- oder RTX-40-Serie und einen CUDA-13-tauglichen Treiber.'
DEPENDENCIES = ('diffusers==0.42.0', 'peft==0.21.2', 'accelerate==1.15.0')
NUNCHAKU_SETUP = 'b600f879a777fdef1466c362e850f7e8c31bf89a/1'

CHECK_GPU = f"""
import sys
import torch
print(sys.version, torch.__version__, torch.version.cuda, flush=True)
assert sys.version_info[:2] == (3, 13), 'Nunchaku requires CPython 3.13'
assert torch.__version__.split('.')[:2] == ['2', '14'] and torch.version.cuda == '13.0', 'Wrong PyTorch/CUDA ABI'
assert torch.cuda.is_available(), 'CUDA is unavailable'
capability = torch.cuda.get_device_capability(0)
print(torch.cuda.get_device_name(0), capability, flush=True)
assert capability in {NUNCHAKU_CAPABILITIES!r}, 'The INT4 checkpoint requires Ampere or Ada'
"""

CHECK_NODE = """
import asyncio
import os
import sys
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
import torch
from nunchaku.models.linear import SVDQW4A4Linear

comfy, node, name = sys.argv[1:]
sys.argv = [sys.argv[0], '--offline', '--disable-dynamic-vram']
sys.path.insert(0, comfy)
import comfy.options
comfy.options.enable_args_parsing()
from app import governance
governance.initialize()
import nodes

assert asyncio.run(nodes.load_custom_node(node)), 'Nunchaku node import failed'
loader = nodes.NODE_CLASS_MAPPINGS[name]
assert loader.FUNCTION == 'load_model' and 'model_name' in loader.INPUT_TYPES()['required']
with torch.inference_mode():
    layer = SVDQW4A4Linear(256, 256, rank=32, bias=False, precision='int4', device='cuda')
    for weight in layer.parameters():
        weight.zero_()
    layer.smooth_factor.fill_(1)
    layer.wscales.fill_(1)
    result = layer(torch.ones((1, 256, 256), dtype=torch.bfloat16, device='cuda'))
    assert result.shape == (1, 256, 256) and torch.count_nonzero(result).item() == 0
print('Nunchaku Qwen loader and CUDA INT4 kernel OK')
"""


def signature(setup):
    return '/'.join((NUNCHAKU_SETUP, *DEPENDENCIES, *(spec['sha256'] for spec in setup.nunchaku_runtime)))


def nunchaku_ready(setup, comfy):
    return (setup.backend_state.get('nunchaku_setup') == signature(setup)
            and (comfy / 'custom_nodes' / NUNCHAKU_NODE / '__init__.py').is_file())


def install_nunchaku(setup, python, comfy):
    setup.notify(translate('Nunchaku und CUDA werden geprüft …'))
    python_args = [python, '-I', '-X', 'utf8']
    try:
        setup.command([*python_args, '-c', CHECK_GPU])
    except RuntimeError as exc:
        raise RuntimeError(translate(NUNCHAKU_GPU_REQUIRED) + translate('\nDetails in logs/setup.log.')) from exc

    wheels = [setup.download(spec) for spec in setup.nunchaku_runtime]
    pip = [*python_args, '-m', 'pip', '--isolated', 'install', '--no-cache-dir',
           '--disable-pip-version-check', '--no-warn-script-location', '--only-binary=:all:']
    node = comfy / 'custom_nodes' / NUNCHAKU_NODE
    setup.notify(translate('Nunchaku-Modelllader wird eingerichtet …'))
    try:
        with TemporaryDirectory(dir=setup.root / 'runtime') as directory:
            # Preserve the CUDA ABI and the libraries used by ComfyUI.
            constraints = Path(directory) / 'constraints.txt'
            setup.command([*python_args, '-c',
                           'import importlib.metadata as m, sys; from pathlib import Path; '
                           'Path(sys.argv[1]).write_text("\\n".join(n + "==" + m.version(n) for n in '
                           '("torch", "torchvision", "torchaudio", "transformers", "tokenizers")))',
                           constraints])
            setup.command([*pip, '--index-url', 'https://pypi.org/simple', '--constraint', constraints, *DEPENDENCIES])
            setup.command([*pip, '--no-deps', '--no-index', '--force-reinstall', *wheels])
        shutil.copytree(setup.root / 'vendor' / NUNCHAKU_NODE, node, dirs_exist_ok=True)
        setup.command([*python_args, '-c', CHECK_NODE, comfy, node, NUNCHAKU_LOADER])
    except RuntimeError as exc:
        raise RuntimeError(translate('Nunchaku konnte nicht eingerichtet werden. Details stehen in logs/setup.log.')) from exc
    setup.backend_state['nunchaku_setup'] = signature(setup)
    setup.persist()
