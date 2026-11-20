"""Build a checked portable archive on top of a verified RestoRenate 1.0 runtime."""
import argparse
from hashlib import file_digest
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA256 = {
    'windows': '81c894f560d12d3c91904e2b9417d8add4cd6cec50151c03ae3baf888249ae5b',
    'linux': '98f09666bb138daade9ae4fb4e6a4e46ecc63f2ed6efbe6a043a10a4810226cf',
    'macos': '3e84419d9afec764b19eda741c50c1b931b169cf567c6d6d1ceecf93875ae6bd',
}


def extract(base, stage):
    if base.name.endswith('.tar.gz'):
        with tarfile.open(base, 'r:gz') as package:
            package.extractall(stage, filter='data')
        return
    with ZipFile(base) as package:
        for member in package.infolist():
            relative = Path(member.filename)
            if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'RestoRenate':
                raise ValueError(f'Unsafe archive member: {member.filename}')
            path = stage / relative
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                link = package.read(member).decode('utf-8')
                if not (path.parent / link).resolve().is_relative_to(stage):
                    raise ValueError(f'Unsafe archive link: {member.filename}')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(link)
            else:
                package.extract(member, stage)
                if mode & 0o777:
                    path.chmod(mode & 0o777)


def zip_portable(stage, output):
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=4) as package:
        for path in sorted(stage.rglob('*')):
            name = path.relative_to(stage).as_posix()
            if path.is_symlink():
                entry = ZipInfo(name)
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                package.writestr(entry, path.readlink().as_posix())
            else:
                package.write(path, name)
    with ZipFile(output) as package:
        if package.testzip() is not None or len(set(package.namelist())) != len(package.namelist()):
            raise ValueError('The archive integrity check failed.')


def build(base, output, platform, smoke_dir, base_sha256=None):
    with base.open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != (base_sha256 or BASE_SHA256[platform]):
            raise ValueError('The original package differs from the verified runtime.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='restorenate-build-') as temp:
        stage = Path(temp)
        extract(base, stage)
        package = stage / 'RestoRenate'
        code = package / '_internal'
        for path in ROOT.glob('*.py'):
            shutil.copy2(path, code / path.name)
        for name in ('constraints-comfy-unix.txt', 'download_manifest.json', 'method_downloads.json',
                     'exiftool_restorenate.config'):
            shutil.copy2(ROOT / name, code / name)
        for name in ('README.md', 'README_DE_EN.txt'):
            (package / name).unlink(missing_ok=True)
        for name in ('README_DE.md', 'README_EN.md'):
            shutil.copy2(ROOT / 'docs/portable' / name, package / name)
        for name in ('LICENSE', 'THIRD_PARTY.txt'):
            shutil.copy2(ROOT / name, package / name)
        (package / 'assets/dismiss-circle.png').unlink(missing_ok=True)
        shutil.copytree(ROOT / 'assets/luts', package / 'assets/luts', dirs_exist_ok=True)
        shutil.copytree(ROOT / 'licenses', package / 'licenses', dirs_exist_ok=True)
        shutil.copytree(ROOT / 'vendor/ComfyUI-VOSR2', package / 'vendor/ComfyUI-VOSR2', dirs_exist_ok=True)
        from bundle_upscalers import bundle_upscalers
        bundle_upscalers(package)
        if platform == 'windows':
            from freeze_windows import build_windows_gui
            build_windows_gui(package)
        if platform == 'macos' and sys.platform == 'darwin':
            bundle = package / 'RestoRenate.app'
            shutil.copy2(ROOT / 'scripts/macos/Info.plist', bundle / 'Contents/Info.plist')
            subprocess.run(['codesign', '--force', '--sign', '-', str(bundle)], check=True)
        if smoke_dir is not None:
            smoke_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(package, smoke_dir / 'RestoRenate', symlinks=True)
        temporary_output = output.with_name(output.name + '.part')
        try:
            if platform == 'linux':
                with tarfile.open(temporary_output, 'w:gz', compresslevel=4) as archive:
                    archive.add(package, arcname=package.name)
            else:
                zip_portable(stage, temporary_output)
            temporary_output.replace(output)
        finally:
            temporary_output.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform', choices=BASE_SHA256)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--smoke-dir', type=Path)
    parser.add_argument('--base-sha256')
    args = parser.parse_args()
    build(args.base, args.output, args.platform, args.smoke_dir, args.base_sha256)
