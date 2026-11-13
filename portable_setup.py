"""Application-local, resumable first-run setup. No system installation."""
from __future__ import annotations

import hashlib
import http.client
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import tempfile
import zipfile

from language import translate
from download_https import open_download
from methods import (COLORIZATION_METHODS, DEFAULT_METHOD, GGUF_METHODS, MICROSOFT,
                     QWEN2509_NUNCHAKU, model_specs, resolve_upscaler, uses_comfy)
from nunchaku_setup import (NUNCHAKU_GPU_REQUIRED, install_nunchaku, nunchaku_ready)
from microsoft_setup import install_microsoft, microsoft_ready
from technical_logs import TechnicalLog, drain_process_log

ROOT = Path(__file__).resolve().parent
NVIDIA = 'nvidia'
AMD = 'amd'
CPU = 'cpu'
COMPUTE_DEVICES = {NVIDIA: 'NVIDIA', AMD: 'AMD (ROCm)', CPU: 'CPU'}
GPU_HINTS = {
    NVIDIA: 'NVIDIA/CUDA ist nicht verfügbar. Prüfe den NVIDIA-Treiber.',
    AMD: ('AMD/ROCm konnte die Grafikkarte nicht verwenden. Prüfe, ob deine Radeon '
          'und der installierte Treiber vom ROCm-Paket unterstützt werden.'),
}
GGUF_NODE = 'ComfyUI-GGUF'
GGUF_PACKAGE = 'gguf==0.19.0'
GGUF_SETUP = '6ea2651e7df66d7585f6ffee804b20e92fb38b8a/' + GGUF_PACKAGE
# Official GitHub API endpoints for the pinned archives.
GITHUB_RELEASE_ASSETS = {
    '7170c2db49c182a81adcc051e80234f99dd891656fb200737f87797876348f96':
        'https://api.github.com/repos/Comfy-Org/ComfyUI/releases/assets/707497157',
    '636f41a1975ad40cf226868ae06a62f7f5bb157532cc10cf3475ff54547e063e':
        'https://api.github.com/repos/Comfy-Org/ComfyUI/releases/assets/732122740',
    '3ff4c52a3a65d71e458ff24b1d7339b326d216ef793c2027761e11efb30f7882':
        'https://api.github.com/repos/microsoft/Bringing-Old-Photos-Back-to-Life/releases/assets/40140422',
    'dc804c850bf167f3d256a349f2c771c585fdc0cf46c210853a86e05a0d7c4be3':
        'https://api.github.com/repos/microsoft/Bringing-Old-Photos-Back-to-Life/releases/assets/40140386',
}


class SetupCancelled(InterruptedError):
    pass


class ComputeUnavailable(RuntimeError):
    pass


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path outside the portable application')
    return path


def local_environment(root):
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    locations = {
        'TEMP':'work/temp', 'TMP':'work/temp', 'TMPDIR':'work/temp',
        'PIP_CACHE_DIR':'work/cache/pip', 'HF_HOME':'work/cache/huggingface',
        'TORCH_HOME':'work/cache/torch', 'TORCH_EXTENSIONS_DIR':'work/cache/torch_extensions',
        'TORCHINDUCTOR_CACHE_DIR':'work/cache/inductor', 'TRITON_CACHE_DIR':'work/cache/triton',
        'CUDA_CACHE_PATH':'work/cache/cuda', 'XDG_CACHE_HOME':'work/cache',
    }
    for name, relative in locations.items():
        path = contained(root, relative)
        path.mkdir(parents=True, exist_ok=True)
        env[name] = str(path)
    env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', PIP_DISABLE_PIP_VERSION_CHECK='1',
               HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
    return env


def remove_readonly(function, path, error):
    if not isinstance(error, PermissionError):
        raise error
    os.chmod(path, stat.S_IWRITE)
    function(path)


class Setup:
    def __init__(self, root=ROOT, notify=print, transfer=None, cancelled=lambda: False,
                 method=DEFAULT_METHOD, faces=False, upscaler=None, compute=NVIDIA):
        self.root = Path(root).resolve()
        self.manifest_bytes = (self.root / 'download_manifest.json').read_bytes()
        self.manifest = json.loads(self.manifest_bytes)
        self.signature = hashlib.sha256(self.manifest_bytes).hexdigest()
        self.compute = compute
        self.runtime = self.manifest['runtime']
        self.backend_root = self.root / 'backend'
        if compute == AMD:
            self.runtime = json.loads((self.root / 'amd_runtime.json').read_bytes())
            self.backend_root /= 'amd'
            self.signature += '/' + self.runtime['sha256']
        self.method = method
        self.faces = method == MICROSOFT and faces
        self.comfy = uses_comfy(method, resolve_upscaler(method, upscaler))
        optional = json.loads((self.root / 'method_downloads.json').read_text(encoding='utf-8'))
        if compute == AMD and method == MICROSOFT:
            optional[MICROSOFT] = [
                spec for spec in optional[MICROSOFT] if not spec['path'].endswith('cp313-cp313-win_amd64.whl')
            ] + optional['microsoft-amd-wheels']
        self.models = model_specs(self.manifest, optional, method, self.faces, upscaler)
        self.nunchaku_runtime = optional['nunchaku-runtime'] if method == QWEN2509_NUNCHAKU else []
        self.colorizer_path = contained(self.root, optional[method][0]['path']) if method in COLORIZATION_METHODS else None
        self.color_runtime = optional['color-runtime'] if self.colorizer_path else []
        self.color_runtime_path = self.root / 'runtime/color-python'
        if self.color_runtime:
            self.models.extend(self.color_runtime)
        self.notify, self.transfer, self.cancelled = notify, transfer, cancelled
        self.state_path = self.root / 'runtime/download_receipts.json'
        try:
            self.state = json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            self.state = {'files': {}}
        self.state.setdefault('files', {})
        self.backend_state = self.state.setdefault('amd_backend', {}) if compute == AMD else self.state
        self.log = self.root / 'logs/setup.log'
        self.log.parent.mkdir(parents=True, exist_ok=True)

    def check(self):
        if self.cancelled():
            raise SetupCancelled(translate('Einrichtung abgebrochen. Teil-Downloads bleiben erhalten.'))

    def persist(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix('.partial.json')
        temporary.write_text(json.dumps(self.state, indent=2), encoding='utf-8')
        temporary.replace(self.state_path)

    def valid(self, spec):
        path = contained(self.root, spec['path'])
        try:
            stat = path.stat()
            receipt = self.state['files'].get(spec['path'], {})
            return (path.is_file() and stat.st_size == spec['size'] and
                    receipt == {'size':stat.st_size, 'mtime_ns':stat.st_mtime_ns, 'sha256':spec['sha256']})
        except OSError:
            return False

    def mark(self, spec):
        path = contained(self.root, spec['path'])
        stat = path.stat()
        self.state['files'][spec['path']] = {'size':stat.st_size, 'mtime_ns':stat.st_mtime_ns, 'sha256':spec['sha256']}
        self.persist()

    def progress(self, spec, current, phase):
        if self.transfer:
            self.transfer(Path(spec['path']).name, current, spec['size'], phase)

    def digest(self, path, spec):
        sha = hashlib.sha256()
        count = 0
        tick = 0
        self.notify(translate('{0} wird geprüft …', path.name))
        self.progress(spec, 0, translate('Prüfen'))
        with path.open('rb') as stream:
            while block := stream.read(4 * 1024 * 1024):
                self.check()
                sha.update(block)
                count += len(block)
                now = time.monotonic()
                if now - tick >= .2:
                    self.progress(spec, count, translate('Prüfen'))
                    tick = now
        return sha, count

    def adopt_runtime_archive(self, spec):
        target = contained(self.root, spec['path'])
        filename = Path(urllib.parse.urlsplit(spec['url']).path).name
        if filename == target.name:
            return
        source = target.with_name(filename)
        if not target.exists() and source.is_file() and source.stat().st_size == spec['size']:
            digest, count = self.digest(source, spec)
            if count == spec['size'] and digest.hexdigest() == spec['sha256']:
                source.replace(target)
                self.mark(spec)
                target.with_name(target.name + '.part').unlink(missing_ok=True)
                self.notify(translate('Manuell geladenes ComfyUI-Archiv geprüft und übernommen.'))
            else:
                self.notify(translate('Manuell geladenes ComfyUI-Archiv hat eine abweichende SHA-256-Prüfsumme.'))

    def stream(self, spec, part, sha, offset, attempt):
        size = spec['size']
        url = spec['url']
        asset_api = GITHUB_RELEASE_ASSETS.get(spec['sha256'])
        headers = {'User-Agent': 'RestoRenate portable', 'Accept-Encoding': 'identity'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        if asset_api and attempt:
            if attempt == 1:
                url = asset_api
                headers['Accept'] = 'application/octet-stream'
            headers['Cache-Control'] = 'no-cache'
            separator = '&' if '?' in url else '?'
            url += f'{separator}fr_retry={time.time_ns()}'

        request = urllib.request.Request(url, headers=headers)
        with open_download(request, timeout=30) as response:
            status = response.getcode()
            if response.headers.get('Content-Type'):
                content_type = response.headers.get_content_type()
                if content_type.startswith('text/') or content_type in ('application/json', 'application/problem+json'):
                    raise OSError(translate('Server liefert {0} statt der erwarteten Datei.', content_type))
            content_length = response.headers.get('Content-Length')
            if status == 206:
                value = response.headers.get('Content-Range', '')
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', value)
                if not match:
                    raise OSError(translate('Server liefert einen ungültigen Downloadbereich.'))
                first, last, total = map(int, match.groups())
                if not (first == offset <= last < size and total == size):
                    raise OSError(translate('Server bestätigt den fortgesetzten Download nicht.'))
                end = last + 1
            elif status == 200:
                end = size
                offset, sha = 0, hashlib.sha256()
            else:
                raise OSError(translate('Unerwarteter HTTP-Status {0}.', status))
            if content_length is not None and content_length != str(end - offset):
                raise OSError(translate('Server meldet eine vom Manifest abweichende Dateigröße.'))

            mode = 'ab' if offset else 'wb'
            tick = 0
            with part.open(mode) as output:
                while block := response.read(1024 * 1024):
                    self.check()
                    if offset + len(block) > end:
                        raise OSError(translate('Download größer als der erwartete Dateibereich.'))
                    output.write(block)
                    sha.update(block)
                    offset += len(block)
                    now = time.monotonic()
                    if now - tick >= .2:
                        self.progress(spec, offset, translate('Download läuft'))
                        tick = now
        if offset != end:
            raise OSError(translate('Download unvollständig. Der nächste Versuch setzt ihn fort.'))
        return sha, offset

    def download(self, spec):
        self.check()
        target = contained(self.root, spec['path'])
        if self.valid(spec):
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file():
            if target.stat().st_size == spec['size'] and self.digest(target, spec)[0].hexdigest() == spec['sha256']:
                self.mark(spec)
                return target
            # Preserve an invalid user-provided file instead of silently accepting it.
            target.replace(target.with_name(target.name + '.invalid-' + str(time.time_ns())))
        if spec == self.runtime:
            self.adopt_runtime_archive(spec)
            if self.valid(spec):
                return target
        part = target.with_name(target.name + '.part')
        for attempt in range(3):
            self.check()
            if part.exists() and part.stat().st_size > spec['size']:
                part.unlink()
            sha, offset = self.digest(part, spec) if part.exists() else (hashlib.sha256(), 0)
            self.notify(translate('{0} wird heruntergeladen …', target.name))
            self.progress(spec, offset, translate('Download läuft'))
            try:
                while offset < spec['size']:
                    self.check()
                    sha, offset = self.stream(spec, part, sha, offset, attempt)
                if part.stat().st_size != spec['size'] or sha.hexdigest() != spec['sha256']:
                    part.unlink()
                    raise OSError(translate('SHA-256-Prüfsumme stimmt nicht. Download wird wiederholt.'))
                # Validate the bytes on disk before registering a successful download.
                disk_sha, disk_size = self.digest(part, spec)
                if disk_size != spec['size'] or disk_sha.hexdigest() != spec['sha256']:
                    part.unlink()
                    raise OSError(translate('Gespeicherte Datei ist beschädigt. Download wird wiederholt.'))
                self.check()
                part.replace(target)
                self.mark(spec)
                self.progress(spec, offset, translate('Download läuft'))
                return target
            except SetupCancelled:
                raise
            except (OSError, http.client.HTTPException) as exc:
                TechnicalLog(self.log).write(f'{time.ctime()} {target.name}: {exc}\n')
                if attempt == 2:
                    manual = ''
                    if spec == self.runtime:
                        original = Path(urllib.parse.urlsplit(spec['url']).path).name
                        manual = translate(
                                     '\n\nDu kannst {0} auch im Browser laden und im Programmordner unter downloads ablegen.',
                                     original,
                                 )
                    raise RuntimeError(
                        translate(
                            'Download fehlgeschlagen: {0}\n{1}\nTeil-Download bleibt erhalten. Details: logs/setup.log{2}',
                            target.name, exc, manual,
                        )
                    ) from exc
                self.notify(translate('Download unterbrochen. Versuch {0}/3 …', attempt + 2))
                for _ in range(15):
                    self.check()
                    time.sleep(.1)

    def paths(self, backend=None):
        backend = self.backend_root if backend is None else backend
        for base in (backend / 'ComfyUI_windows_portable', backend):
            python = base / 'python_embeded/python.exe'
            comfy = base / 'ComfyUI'
            if python.is_file() and (comfy / 'main.py').is_file():
                return python, comfy
        return None

    def command(self, args, env=None):
        self.check()
        env = env or local_environment(self.root)
        log = TechnicalLog(self.log)
        process = subprocess.Popen([str(v) for v in args], cwd=self.root, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        reader = threading.Thread(target=drain_process_log, args=(process.stdout, log), daemon=True)
        reader.start()
        try:
            while process.poll() is None:
                self.check()
                time.sleep(.2)
            if process.returncode:
                raise RuntimeError(translate('Einrichtung fehlgeschlagen. Details stehen in logs/setup.log.'))
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise
        finally:
            reader.join(timeout=5)

    def runtime_ready(self):
        return self.paths() and self.backend_state.get('runtime_sha256') == self.runtime['sha256']

    def remaining_downloads(self):
        specs = self.models + self.nunchaku_runtime
        if self.comfy and not self.runtime_ready():
            specs.append(self.runtime)
        remaining = {}
        for spec in specs:
            target = contained(self.root, spec['path'])
            if target.is_file() and target.stat().st_size == spec['size']:
                continue
            if spec == self.runtime:
                name = Path(urllib.parse.urlsplit(spec['url']).path).name
                local = target.with_name(name)
                if local.is_file() and local.stat().st_size == spec['size']:
                    continue
            part = target.with_name(target.name + '.part')
            existing = min(part.stat().st_size, spec['size']) if part.is_file() else 0
            remaining[spec['path']] = spec['size'] - existing
        return remaining

    def remaining_download_bytes(self):
        return sum(self.remaining_downloads().values())

    def color_ready(self):
        return not self.color_runtime or (self.color_runtime_path / 'onnxruntime/__init__.py').is_file()

    def gguf_ready(self, comfy):
        return (self.backend_state.get('gguf_setup') == GGUF_SETUP and
                (comfy / 'custom_nodes' / GGUF_NODE / '__init__.py').is_file())

    def ready(self):
        if self.nunchaku_runtime and self.compute != NVIDIA:
            return False
        if not self.color_ready() or not all(self.valid(spec) for spec in self.models):
            return False
        if not self.comfy:
            return True
        paths = self.paths()
        return (self.backend_state.get('setup_signature') == self.signature and paths is not None and
                self.backend_state.get('runtime_sha256') == self.runtime['sha256'] and
                (self.method not in GGUF_METHODS or self.gguf_ready(paths[1])) and
                (not self.nunchaku_runtime or nunchaku_ready(self, paths[1])) and
                (self.method != MICROSOFT or microsoft_ready(self, paths[1])))

    def install_packages(self, python, *packages):
        self.command([python, '-I', '-X', 'utf8', '-m', 'pip', '--isolated', 'install', '--no-cache-dir',
                      '--no-index', '--find-links', self.root / 'vendor/wheels',
                      '--no-warn-script-location', '--only-binary=:all:', *packages])

    def verify_compute(self, python):
        if self.compute == CPU:
            return
        label = COMPUTE_DEVICES[self.compute]
        self.notify(translate('{0} wird geprüft …', label))
        torch_backend = 'torch.version.hip' if self.compute == AMD else 'torch.version.cuda'
        probe = (f'import torch; assert {torch_backend} and torch.cuda.is_available(); '
                 'assert (torch.ones(1, device="cuda") + 1).item() == 2; '
                 'print(torch.cuda.get_device_name(0))')
        try:
            self.command([python, '-I', '-X', 'utf8', '-c', probe])
        except SetupCancelled:
            raise
        except RuntimeError as exc:
            raise ComputeUnavailable(translate(GPU_HINTS[self.compute]) + translate('\nDetails in logs/setup.log.')) from exc

    def ensure_color_runtime(self):
        if self.color_ready():
            return
        self.notify(translate('CPU-Laufzeit für die Kolorierung wird eingerichtet …'))
        with tempfile.TemporaryDirectory(dir=self.root / 'runtime') as directory:
            stage = Path(directory)
            for spec in self.color_runtime:
                with zipfile.ZipFile(contained(self.root, spec['path'])) as wheel:
                    for name in wheel.namelist():
                        contained(stage, name)
                    wheel.extractall(stage)
            if self.color_runtime_path.exists():
                shutil.rmtree(self.color_runtime_path)
            stage.rename(self.color_runtime_path)

    def ensure(self):
        self.check()
        if self.nunchaku_runtime and self.compute != NVIDIA:
            raise ComputeUnavailable(translate(NUNCHAKU_GPU_REQUIRED))
        if not self.comfy:
            if self.ready():
                return None
            required = self.remaining_download_bytes()
            if shutil.disk_usage(self.root).free < required + 128 * 1024**2:
                raise RuntimeError(translate('Für die Einrichtung ist zu wenig freier Speicher vorhanden.'))
            for spec in self.models:
                self.download(spec)
            self.ensure_color_runtime()
            return None
        if len(str(self.root)) > 80:
            raise RuntimeError(translate('Bitte das gesamte Programm in einen kürzeren Pfad entpacken, z. B. D:\\RestoRenate. Windows kann sonst lange Dateinamen der Laufzeit nicht öffnen.'))
        if self.ready():
            self.notify(translate('Verfahren ist bereit.'))
            return self.paths()
        # Copying to another filesystem can change timestamp precision.
        # Revalidate complete local models before assuming another download.
        for spec in self.models:
            target = contained(self.root, spec['path'])
            if not self.valid(spec) and target.is_file() and target.stat().st_size == spec['size']:
                if self.digest(target, spec)[0].hexdigest() == spec['sha256']:
                    self.mark(spec)
        if self.ready():
            self.notify(translate('Modelldateien geprüft. Verfahren ist bereit.'))
            return self.paths()
        runtime_missing = not self.runtime_ready()
        if runtime_missing:
            self.adopt_runtime_archive(self.runtime)
        required = self.remaining_download_bytes() + 2 * 1024**3
        if runtime_missing:
            required += 8 * 1024**3
        if shutil.disk_usage(self.root).free < required:
            raise RuntimeError(translate(
                                   'Für die Einrichtung werden derzeit mindestens {0:.1f} GB freier Speicher im Programm-Laufwerk benötigt.',
                                   required / 1000000000.0,
                               ))
        if runtime_missing:
            archive = self.download(self.runtime)
            extractor = contained(self.root, 'tools/7zr.exe')
            if hashlib.sha256(extractor.read_bytes()).hexdigest() != self.manifest['extractor_sha256']:
                raise RuntimeError(translate('Mitgelieferter Entpacker ist beschädigt. Bitte das Programm-ZIP neu entpacken.'))
            backend = contained(self.root, self.backend_root.relative_to(self.root))
            backend.mkdir(parents=True, exist_ok=True)
            self.notify(translate('ComfyUI wird entpackt …'))
            with tempfile.TemporaryDirectory(dir=backend.parent, prefix='rr-') as directory:
                temporary = Path(directory)
                stage = temporary / 'new'
                self.command([extractor, 'x', '-y', '-o' + str(stage), archive])
                paths = self.paths(stage)
                if paths is None:
                    raise RuntimeError(translate('Das ComfyUI-Archiv hat eine unerwartete Ordnerstruktur.'))
                for name in ('.git', 'custom_nodes'):
                    bundled = paths[1] / name
                    if bundled.is_dir():
                        shutil.rmtree(bundled, onexc=remove_readonly)
                (paths[1] / 'custom_nodes').mkdir()
                self.check()
                target = backend / 'ComfyUI_windows_portable'
                previous = temporary / 'previous'
                if target.exists():
                    target.rename(previous)
                try:
                    paths[1].parent.rename(target)
                except OSError:
                    if previous.exists():
                        previous.rename(target)
                    raise
            for key in ('dependencies_signature', 'setup_signature', 'gguf_setup', 'microsoft_wheels', 'nunchaku_setup'):
                self.backend_state.pop(key, None)
            self.backend_state['runtime_sha256'] = self.runtime['sha256']
            self.persist()
        python, comfy = self.paths()
        if self.backend_state.get('dependencies_signature') != self.signature:
            self.notify(translate('ComfyUI wird eingerichtet …'))
            self.install_packages(python, *self.manifest['extra_packages'])
            probe = 'import torch, google.protobuf, sentencepiece, spandrel'
            self.command([python,'-I','-X','utf8','-c',probe])
            self.backend_state['dependencies_signature'] = self.signature
            self.persist()
        self.verify_compute(python)
        if self.method in GGUF_METHODS and not self.gguf_ready(comfy):
            self.notify(translate('GGUF-Modelllader wird eingerichtet …'))
            self.install_packages(python, GGUF_PACKAGE)
            self.command([python, '-I', '-X', 'utf8', '-c', 'import gguf'])
            shutil.copytree(self.root / 'vendor' / GGUF_NODE, comfy / 'custom_nodes' / GGUF_NODE,
                            dirs_exist_ok=True)
            self.backend_state['gguf_setup'] = GGUF_SETUP
            self.persist()
        if self.nunchaku_runtime and not nunchaku_ready(self, comfy):
            install_nunchaku(self, python, comfy)
        for number, spec in enumerate(self.models, 1):
            self.check()
            self.notify(translate('Modelldatei {0}/{1} wird geprüft …', number, len(self.models)))
            self.download(spec)
        self.ensure_color_runtime()
        if self.method == MICROSOFT and not microsoft_ready(self, comfy):
            install_microsoft(self, python, comfy)
        self.backend_state['setup_signature'] = self.signature
        self.persist()
        importlib.invalidate_caches()
        return python, comfy
