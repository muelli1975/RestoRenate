"""Install the verified Microsoft inference weights and optional face dependencies."""
import bz2
import shutil
from zipfile import ZipFile
from language import translate
from methods import METHODS, MICROSOFT

NODE_NAME = 'FotoRestaurierung-Microsoft'
GLOBAL_FILES = {
    'restoration/VAE_A_quality/latest_net_G.pth': 3498887,
    'restoration/VAE_B_quality/latest_net_G.pth': 3498887,
    'restoration/VAE_B_scratch/latest_net_G.pth': 3498887,
    'restoration/mapping_quality/latest_net_mapping_net.pth': 144549781,
    'restoration/mapping_scratch/latest_net_mapping_net.pth': 205392667,
    'restoration/mapping_Patch_Attention/latest_net_mapping_net.pth': 295645915,
    'detection/FT_Epoch_latest.pt': 451663663,
}
FACE_FILES = {'Setting_9_epoch_100/latest_net_G.pth': 368738923}
LANDMARK = 'shape_predictor_68_face_landmarks.dat'
LANDMARK_BYTES = 99693937


def weights_present(folder, files):
    return all((folder / name).is_file() and (folder / name).stat().st_size == size
               for name, size in files.items())


def microsoft_ready(setup, comfy):
    vendor = setup.root / 'vendor' / NODE_NAME / '__init__.py'
    node = comfy / 'custom_nodes' / NODE_NAME / '__init__.py'
    if not vendor.is_file() or not node.is_file() or node.read_bytes() != vendor.read_bytes():
        return False
    receipts = setup.backend_state.get('microsoft_wheels', {})
    if any(receipts.get(item['path']) != item['sha256'] for item in setup.models if item['path'].endswith('.whl')):
        return False
    folder = setup.root / 'models/microsoft/checkpoints'
    if not weights_present(folder, GLOBAL_FILES):
        return False
    return not setup.faces or (weights_present(folder / 'faces', FACE_FILES)
                               and weights_present(folder, {LANDMARK: LANDMARK_BYTES}))


def copy_weight(setup, source, target, size):
    if target.is_file() and target.stat().st_size == size:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.part')
    with temporary.open('wb') as output:
        while block := source.read(1024 * 1024):
            setup.check()
            output.write(block)
    if temporary.stat().st_size != size:
        raise RuntimeError(translate('Entpackte Modelldatei hat eine falsche Größe: {0}', target.name))
    setup.check()
    temporary.replace(target)


def extract_weights(setup, archive, folder, files):
    with ZipFile(archive) as zip_file:
        for relative, size in files.items():
            with zip_file.open('checkpoints/' + relative) as source:
                copy_weight(setup, source, folder / relative, size)


def install_microsoft(setup, python, comfy):
    vendor = setup.root / 'vendor' / NODE_NAME
    node = comfy / 'custom_nodes' / NODE_NAME
    shutil.copytree(vendor, node, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    downloads = setup.root / 'downloads/microsoft'
    folder = setup.root / 'models/microsoft/checkpoints'
    wheel_receipts = setup.backend_state.setdefault('microsoft_wheels', {})
    method_name = METHODS[MICROSOFT]
    wheels = [item for item in setup.models if item['path'].endswith('.whl')
              and wheel_receipts.get(item['path']) != item['sha256']]
    if wheels:
        setup.notify(translate('{0} wird eingerichtet …', method_name))
        setup.command([python, '-I', '-X', 'utf8', '-m', 'pip', '--isolated', 'install', '--no-index', '--no-deps',
                       '--no-cache-dir', '--no-warn-script-location', *[setup.root / item['path'] for item in wheels]])
        for item in wheels:
            wheel_receipts[item['path']] = item['sha256']
        setup.persist()
    setup.notify(translate('Modelle für {0} werden entpackt …', method_name))
    extract_weights(setup, downloads / 'global_checkpoints.zip', folder, GLOBAL_FILES)
    if setup.faces:
        extract_weights(setup, downloads / 'face_checkpoints.zip', folder / 'faces', FACE_FILES)
        with bz2.open(downloads / (LANDMARK + '.bz2'), 'rb') as source:
            copy_weight(setup, source, folder / LANDMARK, LANDMARK_BYTES)
    if not microsoft_ready(setup, comfy):
        raise RuntimeError(translate('{0} konnte nicht eingerichtet werden.', method_name))
