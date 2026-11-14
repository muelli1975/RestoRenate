"""Build and verify the v1.0 archive layout from the existing Windows release."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import os
import shutil
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile


REPO = Path(__file__).resolve().parents[1]
APP = 'RestoRenate'
ARCHIVE = 'RestoRenate_1.0_Windows_x64.zip'
PREVIOUS_SHA256 = '2a191233d4f7c990a0c4128ed52c1d108a4ede4def00949eafe1dffc13fc4954'
ROOT_FILES = {'RestoRenate.exe', 'README_DE_EN.txt', 'LICENSE', 'THIRD_PARTY.txt'}
UPDATED_CODE = {'app.py', 'bootstrap.py', 'language.py', 'portable_paths.py', 'portable_setup.py',
                'preload_models.py', 'theme.py', 'methods.py'}


def build(original, destination):
    expected = os.environ.get('RESTORENATE_PREVIOUS_SHA256', PREVIOUS_SHA256)
    if sha256(original.read_bytes()).hexdigest() != expected:
        raise ValueError('The input archive differs from the verified v1.0 release.')

    compiler = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    launcher = destination.parent / 'RestoRenate.exe'
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                    f'/out:{launcher}', f'/win32icon:{REPO / "assets/restorenate.ico"}',
                    str(REPO / 'RestoRenateLauncher.cs')], check=True)

    with ZipFile(original) as source, ZipFile(destination, 'w', compression=ZIP_DEFLATED) as target:
        for item in source.infolist():
            relative = PurePosixPath(item.filename).relative_to(APP)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError(f'Unsafe archive member: {item.filename}')
            name = relative.as_posix()
            if item.is_dir() or name == 'Start.cmd':
                continue
            if name == 'RestoRenate.exe':
                target.write(launcher, f'{APP}/{name}')
            elif name in {'restorenate.ico', 'assets/restorenate.ico'}:
                target.write(REPO / 'assets/restorenate.ico', f'{APP}/assets/restorenate.ico')
            elif name in ROOT_FILES:
                document = REPO / name
                target.writestr(f'{APP}/{name}', document.read_bytes() if document.is_file() else source.read(item))
            elif relative.name in UPDATED_CODE and (len(relative.parts) == 1 or relative.parts[0] == '_internal'):
                target.write(REPO / relative.name, f'{APP}/_internal/{relative.name}')
            elif len(relative.parts) == 1:
                target.writestr(f'{APP}/_internal/{name}',
                                source.read(item))
            else:
                with source.open(item) as incoming, target.open(item.filename, 'w') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
        target.write(REPO / 'assets/dismiss-circle.png', f'{APP}/assets/dismiss-circle.png')
        if f'{APP}/_internal/portable_paths.py' not in target.namelist():
            target.write(REPO / 'portable_paths.py', f'{APP}/_internal/portable_paths.py')

    with ZipFile(destination) as package:
        names = package.namelist()
        assert package.testzip() is None and len(names) == len(set(names))
        assert {name.split('/')[1] for name in names if name.count('/') == 1} == ROOT_FILES
        for name in ('_internal/bootstrap.py', '_internal/download_manifest.json', '_internal/app.py',
                     'assets/restorenate.ico', 'assets/dismiss-circle.png', 'assets/ready.wav', 'runtime/python/pythonw.exe',
                     'tools/exiftool/exiftool.exe', 'vendor/ComfyUI-GGUF/ops.py'):
            assert f'{APP}/{name}' in names, name
        assert not any(name.endswith(('.onnx', '.safetensors', '.gguf')) for name in names)
        package.extractall(destination.parent / 'smoke')


if __name__ == '__main__':
    build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
