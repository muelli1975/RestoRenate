"""Own hidden local backend; never attach to an existing ComfyUI instance."""
import atexit
from datetime import datetime, timezone
from pathlib import Path
import socket
import subprocess
from tempfile import NamedTemporaryFile
from threading import Thread
import time
import urllib.error
import urllib.request
import uuid

from language import translate
from cpu_threads import THREAD_VARIABLES, choose_cpu_threads, cpu_thread_override
from methods import DEFAULT_METHOD, GGUF_METHODS, MICROSOFT, QWEN2509_NUNCHAKU
from microsoft_setup import NODE_NAME
from nunchaku_setup import NUNCHAKU_NODE
from portable_setup import COMPUTE_DEVICES, CPU, GGUF_NODE, GPU_HINTS, NVIDIA, ROOT, SetupCancelled, contained, local_environment
from technical_logs import TechnicalLog, drain_process_log


class BackendStartError(RuntimeError):
    pass


def patch_cpu_quant_formats(root, comfy):
    """Resolve the CPU device in the default ComfyUI 0.44 quantization check."""
    target = contained(root, comfy / 'comfy/ops.py')
    source = target.read_bytes()
    line_end = b'\r\n' if b'\r\n' in source else b'\n'
    header = b'def get_disabled_quant_formats(device=None):'
    original = line_end.join((header, b'    disabled = set()'))
    # The model can be initialized on CPU even in a GPU session. Resolve the
    # default device only for a true CPU session, as discussed in ComfyUI #17170.
    patched = line_end.join((
        header,
        b'    if device is None and comfy.model_management.cpu_mode():',
        b'        device = comfy.model_management.get_torch_device()',
        b'        logging.info("RestoRenate CPU: PyTorch intra-op threads=%d", torch.get_num_threads())',
        b'    disabled = set()',
    ))
    if patched in source:
        return 'aktiv'
    if source.count(original) != 1:
        return 'nicht angewendet (abweichender ComfyUI-Quellstand)'

    handle = NamedTemporaryFile(dir=target.parent, suffix='.tmp', delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(source.replace(original, patched, 1))
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return 'angewendet'


class Backend:
    def __init__(self, root=ROOT, compute=NVIDIA):
        self.root = Path(root).resolve()
        self.compute = compute
        self.process = None
        self.url = None
        self.log_reader = None
        self.method = None
        self.cpu_threads = None
        atexit.register(self.close)

    def start(self, paths, notify=print, cancelled=lambda: False, method=DEFAULT_METHOD):
        if self.process is not None and self.process.poll() is None and self.method == method:
            return self.url
        self.close()
        self.method = method
        python, comfy = paths
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        self.url = 'http://127.0.0.1:' + str(port)
        static = self.root / 'work/private_frontend'
        static.mkdir(parents=True, exist_ok=True)
        token = 'RestoRenate-private-' + uuid.uuid4().hex
        local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        (static / 'index.html').write_text(token, encoding='utf-8')
        directories = {}
        for name in ['input', 'output', 'temp', 'user']:
            directories[name] = self.root / 'work' / name
            directories[name].mkdir(parents=True, exist_ok=True)
        env = local_environment(self.root)
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        args = [python, '-E', '-s', '-X', 'utf8', '-u', comfy / 'main.py',
                '--listen', '127.0.0.1', '--port', str(port), '--disable-auto-launch',
                '--offline', '--disable-assets', '--disable-metadata', '--preview-method', 'none', '--front-end-root', static,
                '--models-directory', self.root / 'models',
                '--disable-all-custom-nodes']
        if self.compute == CPU:
            args.append('--cpu')
        if method == MICROSOFT:
            args.extend(('--whitelist-custom-nodes', NODE_NAME))
        elif method in GGUF_METHODS:
            args.extend(('--whitelist-custom-nodes', GGUF_NODE))
        elif method == QWEN2509_NUNCHAKU:
            args.extend(('--whitelist-custom-nodes', NUNCHAKU_NODE, '--disable-dynamic-vram'))
        for name, directory in directories.items():
            args.extend(['--' + name + '-directory', directory])
        log = TechnicalLog(self.root / 'logs/backend.log')
        try:
            if self.compute == CPU:
                try:
                    patch_status = patch_cpu_quant_formats(self.root, comfy)
                except (OSError, ValueError) as exc:
                    patch_status = f'nicht angewendet ({exc})'
                utc = datetime.now(timezone.utc).isoformat(timespec='seconds')
                log.write(f'[{utc}] RestoRenate CPU · Geräteprüfung: {patch_status}\n')
                threads = cpu_thread_override(env)
                if threads is not None:
                    log.write(f'RestoRenate CPU: feste Threadvorgabe {threads}\n')
                else:
                    if self.cpu_threads is None:
                        notify(translate('CPU-Threads werden ermittelt …'))
                        self.cpu_threads = choose_cpu_threads(python, self.root, env, cancelled, log)
                    threads = self.cpu_threads
                if cancelled():
                    raise SetupCancelled(translate('Start abgebrochen.'))
                if threads is not None:
                    env.update(dict.fromkeys(THREAD_VARIABLES, str(threads)))
            self.process = subprocess.Popen([str(a) for a in args], cwd=comfy, env=env,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            reader = Thread(target=drain_process_log, args=(self.process.stdout, log), daemon=True)
            reader.start()
            self.log_reader = reader
            notify(translate('ComfyUI wird gestartet …'))
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                if cancelled():
                    raise SetupCancelled(translate('Start abgebrochen.'))
                if self.process.poll() is not None:
                    label = COMPUTE_DEVICES[self.compute]
                    hint = translate(GPU_HINTS.get(self.compute, ''))
                    message = translate(
                                  'ComfyUI konnte im Modus {0} nicht starten. Details in logs/backend.log.',
                                  label,
                              )
                    raise BackendStartError(f'{message}\n\n{hint}' if hint else message)
                try:
                    with local_http.open(self.url + '/', timeout=1) as response:
                        ready_token = response.read(4096).decode('utf-8','replace')
                    if ready_token == token:
                        with local_http.open(self.url + '/object_info', timeout=2) as response:
                            if response.status == 200:
                                notify(translate('ComfyUI ist bereit.'))
                                return self.url
                except (urllib.error.URLError, TimeoutError, OSError):
                    pass
                time.sleep(.2)
            raise BackendStartError(translate('Der Start von ComfyUI dauerte zu lange. Details: logs/backend.log'))
        except BaseException:
            self.close()
            raise

    def close(self):
        process = self.process
        self.process = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        if self.log_reader is not None:
            self.log_reader.join(timeout=5)
            self.log_reader = None
        self.url = None
