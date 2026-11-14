"""Verify that the Linux package installs ROCm and handles a missing Radeon."""
from pathlib import Path
import subprocess
import sys


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

from methods import UPSCALING
from portable_setup import AMD, LINUX, ComputeUnavailable, Setup


assert LINUX
setup = Setup(root, method=UPSCALING, compute=AMD, notify=print)
setup.prepare_unix_runtime()
assert setup.runtime_ready()
python, _ = setup.paths()
device = subprocess.check_output([
    python, '-I', '-c',
    'import torch, torchvision; assert torch.version.hip.startswith("7.2"); print(torch.cuda.is_available())',
], text=True).strip()
if device == 'True':
    setup.verify_compute(python)
    print('ROCm and a Radeon GPU operation passed.')
else:
    assert device == 'False', device
    try:
        setup.verify_compute(python)
    except ComputeUnavailable:
        print('ROCm wheel imports; the app reports the missing Radeon on this runner.')
    else:
        raise AssertionError('The GPU check accepted a runner without Radeon.')
