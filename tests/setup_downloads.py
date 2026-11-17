"""Regression checks for local verification and download approval."""
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from shutil import copy2
from threading import Barrier, Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import Application
from methods import DDCOLOR_PAPER, LANCZOS, MICROSOFT, UPSCALING, VOSR2
from portable_paths import CODE
from portable_setup import COMFY_CONSTRAINTS, CPU, Setup, SetupCancelled, UNIX_RUNTIME


def check_downloads(root):
    root = root.resolve()
    original = b'sample model with known bytes'
    spec = {
        'path': 'models/test/model.bin',
        'size': len(original),
        'sha256': sha256(original).hexdigest(),
    }

    for kind in ('copied-model', 'bad-model', 'bad-complete-part', 'oversized-part'):
        folder = root / kind
        folder.mkdir()
        files = ['download_manifest.json', 'method_downloads.json']
        if UNIX_RUNTIME:
            files.append(COMFY_CONSTRAINTS)
        for name in files:
            copy2(CODE / name, folder / name)
        confirm = Mock(return_value=False)
        setup = Setup(folder, notify=lambda _: None, upscaler=LANCZOS, confirm_download=confirm)
        setup.models = [spec]
        setup.comfy = False
        target = folder / spec['path']
        target.parent.mkdir(parents=True)
        part = target.with_name(target.name + '.part')
        if kind == 'copied-model':
            target.write_bytes(original)
        elif kind == 'bad-model':
            target.write_bytes(b'x' * len(original))
        else:
            part.write_bytes(b'x' * (len(original) + int(kind == 'oversized-part')))
        setup.stream = Mock(side_effect=AssertionError('Network contacted before approval'))
        quoted_bytes = setup.remaining_download_bytes()
        assert quoted_bytes == (len(original) if kind == 'oversized-part' else 0)
        if kind == 'copied-model':
            assert setup.download(spec) == target and setup.valid(spec)
            confirm.assert_not_called()
            continue

        try:
            setup.download(spec)
        except SetupCancelled:
            pass
        else:
            raise AssertionError('Download refusal was not handled')
        setup.stream.assert_not_called()
        confirm.assert_called_once_with('model.bin', len(original))
        if kind == 'bad-model':
            assert target.read_bytes() == b'x' * len(original)

        def transfer(specification, partial, digest, offset, _attempt):
            assert specification == spec and offset == 0
            partial.write_bytes(original)
            digest.update(original)
            return digest, len(original)

        confirm.reset_mock()
        confirm.return_value = True
        setup.stream = Mock(side_effect=transfer)
        assert setup.download(spec).read_bytes() == original and setup.valid(spec)
        setup.stream.assert_called_once()
        confirm.assert_called_once_with('model.bin', len(original))
        if kind == 'bad-model':
            assert len(list(target.parent.glob('model.bin.invalid-*'))) == 1

    setup = Mock(method='test', faces=False, colorizer_method=None)
    setup.ready.return_value = False
    setup.remaining_downloads.return_value = {}
    setup.runtime_needs_setup.return_value = False
    controller = SimpleNamespace(approve_setup=Mock(return_value=False), start_worker=Mock(),
                                 save_settings=Mock(), work=Mock(), closing=False,
                                 preload_installing=False, preload_download_paths=frozenset())
    Application.launch(controller, 'job', upscaler=LANCZOS, setup=setup)
    controller.approve_setup.assert_not_called()
    controller.start_worker.assert_called_once_with('run_setup', controller.work, 'test', False, 'job', LANCZOS, {}, None)
    controller.start_worker.reset_mock()
    setup.runtime_needs_setup.return_value = True
    Application.launch(controller, 'job', upscaler=LANCZOS, setup=setup)
    controller.approve_setup.assert_called_once_with(setup, LANCZOS, {}, True)
    controller.start_worker.assert_not_called()

    folder = root / 'concurrent-downloads'
    folder.mkdir()
    for name in files:
        copy2(CODE / name, folder / name)
    back = Setup(folder, notify=lambda _: None, upscaler=LANCZOS)
    fore = Setup(folder, notify=lambda _: None, upscaler=LANCZOS)
    runtime = Setup(folder, notify=lambda _: None, upscaler=LANCZOS)
    other = dict(spec, path='models/test/another-model.bin')
    barrier = Barrier(2, timeout=5)
    started = Event()

    def concurrent_transfer(specification, partial, digest, offset, _attempt):
        assert offset == 0
        if specification is spec:
            started.set()
        barrier.wait()
        partial.write_bytes(original)
        digest.update(original)
        return digest, len(original)

    back.stream = Mock(side_effect=concurrent_transfer)
    fore.stream = Mock(side_effect=concurrent_transfer)
    already_waiting = Setup(folder, notify=lambda _: None, upscaler=LANCZOS)
    already_waiting.stream = Mock(side_effect=AssertionError('Duplicate transfer started'))
    with ThreadPoolExecutor(max_workers=3) as workers:
        first = workers.submit(back.download, spec)
        assert started.wait(4)
        duplicate = workers.submit(already_waiting.download, spec)
        second = workers.submit(fore.download, other)
        for task in (first, duplicate, second):
            assert task.result(timeout=8).read_bytes() == original

    runtime.backend_state['setup_signature'] = 'test-signature'
    runtime.persist()
    fresh = Setup(folder, notify=lambda _: None, upscaler=LANCZOS)
    assert fresh.valid(spec) and fresh.valid(other)
    assert fresh.backend_state['setup_signature'] == 'test-signature'
    already_waiting.stream.assert_not_called()

    vosr = Setup(folder, method=UPSCALING, upscaler=VOSR2, compute=CPU, notify=lambda _: None)
    config_specs = [spec for spec in vosr.models if spec['path'].endswith('.json')]
    assert {Path(spec['path']).name for spec in config_specs} == {'args.json', 'config.json'}
    payload = b'{"test":true}'

    def response(content_type, body=payload):
        result = BytesIO(body)
        result.headers = Message()
        result.headers['Content-Type'] = content_type
        result.headers['Content-Length'] = str(len(body))
        result.getcode = lambda: 200
        return result

    for spec, content_type in zip(config_specs, ('text/plain; charset=utf-8', 'application/json'), strict=True):
        spec = dict(spec, size=len(payload), sha256=sha256(payload).hexdigest())
        with patch('portable_setup.open_download', return_value=response(content_type)):
            assert vosr.download(spec).read_bytes() == payload and vosr.valid(spec)

    binary = next(spec for spec in vosr.models if spec['path'].endswith('.safetensors'))
    for spec, content_type in ((binary, 'text/plain'), (config_specs[0], 'text/html')):
        with patch('portable_setup.open_download', return_value=response(content_type)):
            try:
                vosr.stream(spec, folder / 'rejected-download.part', sha256(), 0, 0)
            except OSError as exc:
                assert content_type in str(exc)
            else:
                raise AssertionError(f'Unexpected response type was accepted: {content_type}')
    assert not (folder / 'rejected-download.part').exists()

    microsoft = Setup(folder, method=MICROSOFT, faces=True, upscaler=LANCZOS, compute=CPU)
    colorizer = Setup(folder, method=DDCOLOR_PAPER, upscaler=LANCZOS, compute=CPU)
    combined = Setup(folder, method=MICROSOFT, faces=True, upscaler=LANCZOS, compute=CPU, colorization=DDCOLOR_PAPER)
    assert microsoft.colorizer_path is None and combined.colorizer_path == colorizer.colorizer_path
    assert combined.colorizer_method == DDCOLOR_PAPER
    assert combined.models == microsoft.models + colorizer.models
    assert combined.microsoft_wheels == microsoft.microsoft_wheels
