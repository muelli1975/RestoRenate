"""Regression checks for local verification and download approval."""
from hashlib import sha256
from pathlib import Path
from shutil import copy2
from types import SimpleNamespace
from unittest.mock import Mock

from app import Application
from methods import LANCZOS
from portable_paths import CODE
from portable_setup import COMFY_CONSTRAINTS, Setup, SetupCancelled, UNIX_RUNTIME


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

    setup = Mock(method='test', faces=False)
    setup.ready.return_value = False
    setup.remaining_downloads.return_value = {}
    setup.runtime_needs_setup.return_value = False
    controller = SimpleNamespace(approve_setup=Mock(return_value=False), start_worker=Mock(),
                                 save_settings=Mock(), work=Mock())
    Application.launch(controller, 'job', upscaler=LANCZOS, setup=setup)
    controller.approve_setup.assert_not_called()
    controller.start_worker.assert_called_once_with('run_setup', controller.work, 'test', False, 'job', LANCZOS, {})
    controller.start_worker.reset_mock()
    setup.runtime_needs_setup.return_value = True
    Application.launch(controller, 'job', upscaler=LANCZOS, setup=setup)
    controller.approve_setup.assert_called_once_with(setup, LANCZOS, {}, True)
    controller.start_worker.assert_not_called()
