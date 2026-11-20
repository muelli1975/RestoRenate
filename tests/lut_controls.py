"""Exercise real LUT files, composition metadata and the Tk controls."""
import json
from hashlib import sha256
import os
from pathlib import Path
from shutil import copy2
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
import time
import tkinter as tk
from tkinter import font, ttk
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

if len(sys.argv) > 1:
    sys.path.insert(0, str(Path(sys.argv[1]) / '_internal'))
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app
from crop import CropRegion
from edit_models import has_choice_mark
from export_metadata import editor_graph
from imaging import LEGACY_RESULT_STEM_BYTES, exiftool_executable, numbered_stem, result_labels, save_result
from looks import Look, apply_look, catalog
from methods import (COLORIZATION_NAMES, DDCOLOR, DDCOLOR_ARTISTIC, DDCOLOR_PAPER, DDCOLOR_TINY,
                     DEOLDIFY_STABLE, FIBO2_TURBO, LANCZOS, MICROSOFT, UPSCALING)
from portable_paths import CODE
from portable_setup import COMFY_CONSTRAINTS, UNIX_RUNTIME
from preload_models import PreloadDialog
from restoration import export_look_variant, restore
from sizes import DOUBLE_SIZE, NO_RESCALE
from reference_controls import check_reference_controls
from setup_downloads import check_downloads


def test_export(root):
    source = root / 'scene.png'
    image = Image.new('RGB', (80, 48), (155, 97, 44))
    image.save(source)
    look = Look('portra160nc', 55)
    crop = CropRegion(image.size, (7, 8, 52, 32))
    original = {'method': 'Upscaling', 'models': {}, 'prompt': '', 'seed': None}
    resized, _ = restore(None, {}, source, root / 'output', 'PNG', None, '', None, lambda _: None,
                         lambda: False, original, method=UPSCALING, upscaler=LANCZOS,
                         size_choice=(DOUBLE_SIZE, 0), source_crop=crop, look=look)
    with Image.open(resized) as result, apply_look(image.crop(crop.box).resize((90, 48), Image.Resampling.LANCZOS), look) as expected:
        assert result.size == expected.size and result.tobytes() == expected.tobytes()
        assert not result.info
    parent = {'settings': original['settings']}
    record = {}
    saved, _ = export_look_variant(source, resized, crop, 0, root / 'output', 'PNG', None,
                                   Look('ilford_delta_100', 40) if 'ilford_delta_100' in catalog() else Look('provia100f', 40),
                                   parent, record, lambda: False)
    assert '_01_' in resized.name and '_02_' in saved.name
    with Image.open(saved) as variant:
        assert variant.size == (90, 48)
        assert len(record['luts']) == 2
    graph = {'4': {'inputs': {}}, '30': {'inputs': {}}, '7': {'inputs': {'reference': ['30', 0]}}}
    settings = {'original_size': image.size, 'second_rotation': 1, 'second_crop': (10, 12, 50, 52),
                'second_size': (32, 32)}
    edited = editor_graph(graph, settings)
    assert edited['96']['inputs']['image'] == ['95', 0]
    assert edited['94']['inputs']['image'] == ['96', 0]
    assert edited['7']['inputs']['reference'] == ['94', 0]


def test_metadata(root, exiftool):
    source = root / 'metadata.jpg'
    image = Image.new('RGB', (65, 45), (111, 155, 44))
    exif = image.getexif()
    exif[271] = 'RestoRenate test'
    image.save(source, exif=exif)
    subprocess.run([exiftool, '-overwrite_original', '-IPTC:Keywords=discard me',
                    '-XMP-dc:Title=discard me', source], check=True, capture_output=True)
    look = Look('portra160nc', 55)
    for fmt in ('JPEG 95 · 4:4:4', 'TIFF'):
        record = {}
        saved, _ = export_look_variant(source, source, None, 0, root / 'output', fmt, exiftool,
                                       look, {}, record, lambda: False)
        tags = json.loads(subprocess.check_output([exiftool, '-config', app.ROOT / '_internal/exiftool_restorenate.config'
                                                  if (app.ROOT / '_internal').exists() else app.ROOT / 'exiftool_restorenate.config',
                                                  '-j', '-Make', '-Orientation#', '-IPTC:Keywords', '-XMP-dc:Title',
                                                  '-XMP-restorenate:Settings', saved]))[0]
        assert tags['Make'] == 'RestoRenate test' and tags['Orientation'] == 1, tags
        assert 'Keywords' not in tags and 'Title' not in tags, tags
        assert json.loads(tags['Settings'])['luts'] == [look.record()], tags
        inherited = {}
        export_look_variant(source, saved, None, 0, root / 'output', fmt, exiftool,
                            look, {}, inherited, lambda: False)
        assert inherited['luts'] == [look.record(), look.record()], inherited


def test_numbered_exports(root):
    folder = root / 'numbered'
    labels = ('Microsoft', 'DDColor-ModelScope', 'RealESRGAN-Anime-4x')
    other = ('Microsoft', 'DeOldify-Stable', 'UltraSharp-V2-Lite')
    source = root / ('é' * 100 + '.png')
    legacy_stem, _ = numbered_stem(source.stem, LEGACY_RESULT_STEM_BYTES)
    with Image.new('RGB', (32, 24), (155, 97, 44)) as image:
        image.save(source)
        folder.mkdir()
        legacy = folder / f'{legacy_stem}_99_Microsoft_DDColor-Paper.png'
        image.save(legacy)
        assert result_labels(source, legacy) == ('Microsoft', 'DDColor-Paper')
        first, _ = save_result(image, source, folder, 'PNG', None, None, labels=labels)
        second, _ = save_result(image, source, folder, 'PNG', None, None, labels=other)
    assert first.stem.endswith('_100_' + '_'.join(labels))
    assert second.stem.endswith('_101_' + '_'.join(other))
    assert result_labels(source, first) == labels and len(first.name.encode('utf-8')) <= 255
    variant, _ = export_look_variant(source, first, None, 0, folder, 'PNG', None,
                                     Look('portra160nc', 55), {}, {}, lambda: False)
    assert variant.stem.endswith('_102_' + '_'.join(labels))


def test_microsoft_colorization_export(root):
    source = root / 'scan.png'
    folder = root / 'microsoft-output'
    size = (80, 48)
    Image.new('RGB', size, (60, 60, 60)).save(source)
    restored = (128, 128, 128)
    colored = (168, 118, 96)
    client = SimpleNamespace(root=root, image=lambda _: Image.new('RGB', size, restored))

    def colorize(image):
        assert image.size == size and image.getpixel((0, 0)) == restored
        return Image.new('RGB', image.size, colored)

    colorizer = Mock(process=Mock(side_effect=colorize))
    models = {'colorizer': 'ddcolor_paper.onnx'}
    record = {'method': 'Microsoft', 'models': models, 'prompt': '', 'seed': None}
    messages = []
    with patch('restoration.generate', return_value={'filename': 'preview.png'}) as generate:
        saved, warning = restore(client, models, source, folder, 'PNG', None, '', None, messages.append,
                                 lambda: False, record, method=MICROSOFT, faces=True, upscaler=LANCZOS,
                                 size_choice=(NO_RESCALE, 0), colorization=DDCOLOR_PAPER, colorizer=colorizer)
    assert not warning and list(folder.glob('*.png')) == [saved]
    assert 'Microsoft' in saved.name and 'DDColor-Paper' in saved.name
    with Image.open(saved) as image:
        assert image.size == size and image.getpixel((0, 0)) == colored
    graph = generate.call_args.args[1]
    assert graph['20']['inputs']['image'] == ['9', 0]
    assert record['settings']['colorization'] == DDCOLOR_PAPER
    assert record['settings']['models']['colorizer'] == 'ddcolor_paper.onnx'
    assert record['seconds_by_stage']['colorization'] >= 0
    assert app.translate('Bild wird koloriert …') in messages
    colorizer.process.assert_called_once()
    assert not list((root / 'work/input').glob('*.png'))


def check_microsoft_colorization_controls(gui):
    microsoft = app.translate(app.METHODS[MICROSOFT])
    gui.method.set(microsoft)
    gui.choose_method()
    gui.window.update()
    assert gui.microsoft_options.winfo_ismapped()
    assert gui.microsoft_colorizer_widget.instate(['disabled'])
    assert gui.microsoft_colorization() is None
    gui.microsoft_colorize_control.toggle()
    assert gui.microsoft_colorizer_widget.instate(['readonly'])
    gui.microsoft_colorizer.set(COLORIZATION_NAMES[DEOLDIFY_STABLE])
    gui.microsoft_colorizer_widget.event_generate('<<ComboboxSelected>>')
    assert gui.microsoft_colorization() == DEOLDIFY_STABLE
    assert app.read_settings()['microsoft_colorizer'] == DEOLDIFY_STABLE
    combined = {'method': MICROSOFT, **gui.microsoft_colorization_settings()}
    gui.method.set(app.translate(app.METHODS[DDCOLOR]))
    gui.choose_method()
    gui.window.update()
    assert not gui.microsoft_options.winfo_ismapped() and gui.microsoft_colorization() is None
    gui.processing_presets.update({'Legacy Microsoft': {'method': MICROSOFT}, 'Combined': combined})
    gui.load_processing_preset('Legacy Microsoft')
    assert gui.microsoft_colorization() is None and gui.microsoft_colorizer_widget.instate(['disabled'])
    gui.load_processing_preset('Combined')
    assert gui.microsoft_colorization() == DEOLDIFY_STABLE


def check_preload(window, root):
    def setup(_root, *, method, faces, upscaler, compute):
        files = [{'path': f'models/{method}/{upscaler}', 'size': 10}]
        if method == MICROSOFT and faces:
            files.append({'path': 'downloads/face_checkpoints.zip', 'size': 10})
        pending = {spec['path']: 10 for spec in files if not spec['path'].startswith('models/microsoft/')}
        return SimpleNamespace(
            models=files, comfy=False, remaining_downloads=lambda: pending,
            valid=lambda spec: spec['path'] not in pending,
        )

    with patch('preload_models.Setup', side_effect=setup):
        dialog = PreloadDialog(window, root, app.CPU, False)
    try:
        base = dialog.methods[MICROSOFT]
        assert base.get() and not dialog.faces.get()
        assert dialog.selection() == ((MICROSOFT, False, LANCZOS),)
        assert not dialog.quoted_downloads
        dialog.faces.set(True)
        dialog.select_faces()
        assert dialog.selection() == ((MICROSOFT, True, LANCZOS),)
        assert dialog.quoted_downloads == {'downloads/face_checkpoints.zip': 10}
        dialog.select_all(False)
        assert not base.get() and not dialog.faces.get() and not dialog.selection()
        assert dialog.submit.instate(['disabled'])
        dialog.faces.set(True)
        dialog.select_faces()
        assert base.get() and dialog.selection() == ((MICROSOFT, True, LANCZOS),)
        dialog.select_all(True)
        assert dialog.faces.get() and dialog.selection()
    finally:
        dialog.destroy()


def check_preload_verification(window, root, wait_for):
    root.mkdir()
    for name in ('download_manifest.json', 'method_downloads.json'):
        copy2(CODE / name, root / name)
    if UNIX_RUNTIME:
        copy2(CODE / COMFY_CONSTRAINTS, root / COMFY_CONSTRAINTS)
    (root / 'models').mkdir()
    original = b'model test contents'
    models = {}
    for method in (DDCOLOR, DDCOLOR_ARTISTIC, DDCOLOR_PAPER, DDCOLOR_TINY):
        path = f'models/{method}.onnx'
        content = original if method == DDCOLOR_ARTISTIC else original * 2
        models[method] = {'path': path, 'size': len(content), 'sha256': sha256(content).hexdigest()}
        file = root / path
        if method == DDCOLOR_TINY:
            file = file.with_suffix('.onnx.part')
        file.write_bytes(b'x' * len(content) if method == DDCOLOR_PAPER else content)

    allow_first = Event()
    allow_rest = Event()
    digest = app.Setup.digest

    def delayed_digest(setup, path, spec):
        gate = allow_first if spec == models[DDCOLOR_ARTISTIC] else allow_rest
        assert gate.wait(8)
        return digest(setup, path, spec)

    def create_setup(*args, **kwargs):
        setup = app.Setup(*args, **kwargs)
        method = kwargs.get('method')
        if method in models:
            setup.models = [models[method]]
        return setup

    with (patch('preload_models.Setup', side_effect=create_setup),
          patch.object(app.Setup, 'digest', delayed_digest),
          patch.object(app.Setup, 'stream', side_effect=AssertionError('Unexpected download')) as stream):
        dialog = PreloadDialog(window, root, app.CPU, False)
        try:
            assert dialog.verification_timer is not None
            assert all(not dialog.methods[method].get() for method in models)
            dialog.methods[DDCOLOR].set(True)
            dialog.methods[DDCOLOR].set(False)
            allow_first.set()
            wait_for(dialog.methods[DDCOLOR_ARTISTIC].get)
            assert dialog.verification_timer is not None
            allow_rest.set()
            wait_for(lambda: dialog.verification_timer is None)
            assert dialog.methods[DDCOLOR_ARTISTIC].get()
            assert all(not dialog.methods[method].get() for method in models if method != DDCOLOR_ARTISTIC)
            setup = app.Setup(root, compute=app.CPU)
            assert setup.valid(models[DDCOLOR]) and setup.valid(models[DDCOLOR_ARTISTIC])
            assert not setup.valid(models[DDCOLOR_PAPER]) and not setup.valid(models[DDCOLOR_TINY])
            assert (root / models[DDCOLOR_PAPER]['path']).read_bytes() == b'x' * models[DDCOLOR_PAPER]['size']
            stream.assert_not_called()
        finally:
            allow_first.set()
            allow_rest.set()
            dialog.destroy()


def check_background_preload(gui, wait_for):
    downloading, downloaded = Event(), Event()
    installing, installed = Event(), Event()
    other_request = (MICROSOFT, True, LANCZOS)
    pending = {'downloads/face_checkpoints.zip': 100}
    real_setup = app.Setup

    def fetch():
        downloading.set()
        assert downloaded.wait(8)

    def install():
        installing.set()
        assert installed.wait(8)

    setup = Mock(comfy=True, download_preload_files=Mock(side_effect=fetch),
                 ensure=Mock(side_effect=install))
    setup.ready.return_value = False

    def choose_setup(*args, **kwargs):
        return setup if kwargs.get('method') == MICROSOFT and 'transfer' in kwargs else real_setup(*args, **kwargs)

    with (patch('app.choose_preloads', return_value=((other_request,), pending)),
          patch('app.Setup', side_effect=choose_setup),
          patch.object(gui.backend, 'close') as close_backend):
        gui.preload_button.invoke()
        wait_for(downloading.is_set)
        progress = gui.preload_progress
        assert progress.grab_current() is None
        assert gui.action is None and gui.start_button.instate(['!disabled'])
        gui.start_worker('run', lambda: gui.events.put(('status', 'Processing test image')))
        wait_for(lambda: gui.status.get() == 'Processing test image')
        assert gui.preload_button.instate(['!disabled'])
        assert not gui.preload_cancelled.is_set()
        progress.dismiss()
        assert progress.state() == 'withdrawn'
        gui.preload_button.invoke()
        assert progress.state() == 'normal'
        downloaded.set()
        wait_for(lambda: gui.preload_to_install is not None)
        assert gui.action == 'run' and gui.status.get() == 'Processing test image'
        assert progress.progress.value == 100
        assert progress.status.cget('text') == app.translate(
            'Downloadphase abgeschlossen. Einrichtung startet nach der laufenden Bearbeitung.')
        assert not installing.is_set()
        close_backend.assert_not_called()

        gui.events.put(('idle', (False, None)))
        wait_for(installing.is_set)
        assert gui.action is None and gui.preload_installing
        assert gui.start_button.instate(['disabled'])
        close_backend.assert_called_once()
        installed.set()
        wait_for(lambda: gui.preload_cancelled is None)
        assert gui.start_button.instate(['!disabled']) and not progress.active
        progress.dismiss()
        assert gui.preload_progress is None

        waiting = Event()

        def cancel_test():
            waiting.set()
            assert gui.preload_cancelled.wait(8)
            raise app.SetupCancelled()

        setup.download_preload_files.side_effect = cancel_test
        gui.start_worker('run', lambda: None)
        gui.preload_button.invoke()
        wait_for(waiting.is_set)
        gui.preload_progress.cancel_button.invoke()
        wait_for(lambda: gui.preload_cancelled is None)
        assert gui.action == 'run' and not gui.cancelled.is_set()
        assert gui.start_button.instate(['!disabled'])
        close_backend.assert_called_once()
        gui.preload_progress.dismiss()
        gui.events.put(('idle', (False, None)))
        wait_for(lambda: gui.action is None)


def test_gui(root):
    window = tk.Tk()
    window.attributes('-alpha', 0)

    def wait_for(condition):
        deadline = time.monotonic() + 8
        while not condition() and time.monotonic() < deadline:
            window.update()
            time.sleep(.025)
        assert condition()

    try:
        app.SETTINGS = root / 'settings.json'
        app.JOBS_LOG = root / 'jobs.jsonl'
        source = root / 'scene.png'
        first_look, other_look, *_ = catalog()
        app.SETTINGS.write_text(json.dumps({'method': FIBO2_TURBO, 'lut': {'id': other_look, 'strength': 100}}),
                                encoding='utf-8')
        gui = app.Application(window)
        assert gui.look_controls.look().key == first_look
        assert window.title() == f'{app.APP_NAME} – {app.APP_VERSION}'
        window.update()
        check_preload(window, root)
        check_preload_verification(window, root / 'model-verification', wait_for)
        check_background_preload(gui, wait_for)
        assert gui.preview_switch.cget('text') == app.translate('Ergebnisse')
        assert gui.preview_switch.instate(['disabled'])
        assert not gui.result_counter.winfo_manager()
        if window.winfo_width() >= app.START_WINDOW_WIDTH:
            assert gui.preview_tools.grid_info()['row'] == 0
        assert window.winfo_height() >= window.minsize()[1]
        gui.pick_sources(source)
        assert gui.preview_switch.instate(['disabled'])
        for language in ('de', 'en'):
            gui.change_language(language)
            window.update()
            window.geometry(f'{window.minsize()[0]}x720')
            window.update()
            seed_font = font.Font(window, font=ttk.Style(window).lookup('Seed.TEntry', 'font'))
            required_seed_width = seed_font.measure(str(app.MAX_SEED)) + 4
            assert gui.seed_entry.winfo_width() >= required_seed_width, (
                language, gui.seed_entry.winfo_width(), required_seed_width,
            )
            assert gui.clear_seed_button.instate(['disabled'])
            gui.seed_value.set(str(app.MAX_SEED))
            assert gui.fixed_seed() == app.MAX_SEED and gui.clear_seed_button.instate(['!disabled'])
            gui.clear_seed_button.invoke()
            assert gui.fixed_seed() is None and gui.clear_seed_button.instate(['disabled'])
            right = gui.look_controls.save_button
            assert right.winfo_rootx() + right.winfo_width() < window.winfo_rootx() + window.winfo_width()
            assert gui.compare.winfo_height() > 380
            check_reference_controls(gui, source)
            pane = gui.settings_panel
            assert window.winfo_height() >= window.minsize()[1]
            assert pane.winfo_height() >= pane.winfo_reqheight()
            assert gui.setup_notice.winfo_width() >= gui.setup_notice.winfo_reqwidth()
            lut_row = gui.look_controls.frame
            assert gui.compare.winfo_rooty() + gui.compare.winfo_height() <= lut_row.winfo_rooty()
            assert lut_row.winfo_rooty() + lut_row.winfo_height() <= gui.result_navigation.winfo_rooty()
            for widget in (gui.prompt, gui.seed_entry, gui.start_button, gui.stop_button):
                assert widget.winfo_ismapped()
                assert widget.winfo_height() >= widget.winfo_reqheight()
                assert widget.winfo_rooty() + widget.winfo_height() <= pane.winfo_rooty() + pane.winfo_height()
        controls = gui.look_controls
        original = gui.compare.before_image
        assert controls.save_button.instate(['disabled'])
        assert controls.choose.instate(['disabled'])
        caption_geometry = gui.result_caption.winfo_rootx(), gui.result_caption.winfo_width()
        controls.check.toggle()
        window.update()
        assert controls.enabled.get() and gui.compare.look_basis is original
        assert (gui.result_caption.winfo_rootx(), gui.result_caption.winfo_width()) == caption_geometry
        assert abs(2 * gui.result_caption.winfo_rootx() + gui.result_caption.winfo_width()
                   - 2 * gui.compare.winfo_rootx() - gui.compare.winfo_width()) <= 1
        assert not controls.save_button.instate(['disabled'])
        controls.check.toggle()
        window.update()
        assert not controls.enabled.get() and gui.compare.look_basis is None
        assert gui.compare.after_image is None and controls.save_button.instate(['disabled'])
        assert not hasattr(controls, 'target')
        gui.create_lut_variant()
        assert gui.action is None and not gui.results

        # Invoke the toplevel hotkeys with focus on an unrelated button.
        widget = gui.start_button
        widget.focus_force()
        window.update()
        widget.event_generate('<KeyPress-c>')
        widget.event_generate('<KeyRelease-c>')
        time.sleep(.025)
        window.update()
        assert controls.enabled.get() and gui.compare.look_basis is original
        widget.event_generate('<KeyPress-c>')
        widget.event_generate('<KeyRelease-c>')
        time.sleep(.025)
        window.update()
        assert not controls.enabled.get() and gui.compare.look_basis is None
        key_before = controls.look().key
        for name in ('c', 'Right'):
            widget.event_generate(f'<KeyPress-{name}>')
            if name == 'Right':
                widget.event_generate('<KeyRelease-Right>')
        widget.event_generate('<KeyRelease-c>')
        time.sleep(.025)
        window.update()
        assert controls.enabled.get() and gui.compare.look_basis is original
        assert controls.look().key != key_before
        menu = controls.menu
        film, film_index = menu.choices[controls.look().key]
        cinema, cinema_index = menu.choices['classic_cinema']
        _, film_entry = menu.categories[film]
        _, cinema_entry = menu.categories[cinema]
        assert menu.entrycget(film_entry, 'image') == str(menu.check) and has_choice_mark(menu, film, film_index)
        assert menu.entrycget(cinema_entry, 'image') == str(menu.blank) and not has_choice_mark(menu, cinema, cinema_index)
        # Native menus differ in how they dispatch synthetic events while closed.
        with patch.object(cinema, 'index', return_value=0):
            controls.highlight(cinema, [('classic_cinema', catalog()['classic_cinema'])])
        assert controls.hover == 'classic_cinema'
        assert controls.look().key != 'classic_cinema' and menu.entrycget(film_entry, 'image') == str(menu.check)
        cinema.invoke(cinema_index)
        assert controls.look().key == 'classic_cinema' and controls.hover is None
        assert menu.entrycget(cinema_entry, 'image') == str(menu.check) and has_choice_mark(menu, cinema, cinema_index)
        assert menu.entrycget(film_entry, 'image') == str(menu.blank) and not has_choice_mark(menu, film, film_index)
        track = controls.slider._canvas
        x11 = window.tk.call('tk', 'windowingsystem') == 'x11'
        def wheel_down(state):
            if x11:
                track.event_generate('<Button-5>', state=state)
            else:
                track.event_generate('<MouseWheel>', delta=-120, state=state)
            window.update()
        for state in (0, 4):
            wheel_down(state)
            assert controls.look().strength == 100
        wheel_down(1)
        assert controls.look().strength == 95
        for click_time in (1000, 1150):
            track.event_generate('<ButtonPress-1>', x=10, y=8, time=click_time)
            track.event_generate('<ButtonRelease-1>', x=10, y=8, time=click_time + 10)
        window.update()
        assert controls.look().strength == 100
        wheel_down(1)
        assert controls.look().strength == 95
        entry = gui.seed_entry
        entry.focus_set()
        window.update()
        assert window.focus_get() is entry, window.focus_get()
        entry.event_generate('<KeyPress-c>')
        entry.event_generate('<KeyRelease-c>')
        time.sleep(.025)
        window.update()
        assert controls.enabled.get() and 'c' not in controls.held

        gui.play_ready_sound = lambda: None
        gui.create_lut_variant()
        wait_for(lambda: gui.action is None)
        assert gui.action is None and len(gui.results) == 1
        saved = gui.compare.after_image
        assert saved is not None and not controls.enabled.get() and gui.compare.look_basis is None
        controls.check.toggle()
        assert gui.compare.look_basis is saved
        controls.check.toggle()
        assert gui.compare.look_basis is None and gui.compare.after_image is saved
        assert gui.prev_button.instate(['disabled']) and gui.next_button.instate(['disabled'])
        gui.move(-1)
        assert gui.index == 0
        assert gui.preview_switch.cget('text') == app.translate('Eingabe')
        assert not gui.preview_switch.instate(['disabled'])
        assert gui.result_position.get() == app.translate('Ergebnis {0}/{1}', 1, 1)
        assert gui.result_counter.winfo_manager() == 'pack'
        gui.preview_switch.invoke()
        assert gui.index == -1 and gui.compare.after_image is None and not controls.enabled.get()
        assert gui.prev_button.instate(['disabled']) and gui.next_button.instate(['disabled'])
        assert gui.preview_switch.cget('text') == app.translate('Ergebnisse')
        assert not gui.result_counter.winfo_manager()
        gui.move(1)
        assert gui.index == -1
        controls.check.toggle()
        assert gui.compare.look_basis is gui.compare.before_image
        gui.preview_switch.invoke()
        assert gui.index == 0 and gui.compare.after_image is not None and not controls.enabled.get()
        assert controls.look().key != first_look and controls.look().strength == 95
        assert gui.second_button.cget('text') == app.translate('Bild …')

        controls.check.toggle()
        gui.create_lut_variant()
        wait_for(lambda: gui.action is None)
        assert gui.action is None and len(gui.results) == 2 and gui.index == 1
        assert gui.next_button.instate(['disabled'])
        gui.prev_button.invoke()
        assert gui.index == 0 and not gui.next_button.instate(['disabled'])
        gui.preview_switch.invoke()
        gui.preview_switch.invoke()
        assert gui.index == 0
        gui.next_button.invoke()
        gui.preview_switch.invoke()
        gui.preview_switch.invoke()
        assert gui.index == 1

        help_button = next(widget for widget, label in gui.labels.items() if label == 'F1 · Bedienhilfe')
        assert isinstance(help_button, ttk.Button) and help_button.cget('style') == 'Input.TButton'
        gui.change_language('de')
        help_button.invoke()
        help_dialog = gui.controls_help
        assert help_dialog.title() == 'Bedienhilfe'
        panels = next(child for child in help_dialog.winfo_children() if hasattr(child, 'panels'))
        def check_guide(columns, scrolling):
            window.update()
            assert panels.columns == columns
            assert bool(panels.scrollbar.winfo_ismapped()) == scrolling
            assert panels.panels[1].grid_info()['column'] == columns - 1
            for label, _ in panels.labels:
                assert label.winfo_ismapped()
                x = label.winfo_rootx() - panels.canvas.winfo_rootx()
                assert 0 <= x <= panels.canvas.winfo_width() - label.winfo_width()
                assert label.winfo_reqwidth() <= label.winfo_width()
                assert label.winfo_reqheight() <= label.winfo_height()
                if not scrolling:
                    y = label.winfo_rooty() - panels.canvas.winfo_rooty()
                    assert 0 <= y <= panels.canvas.winfo_height() - label.winfo_height()
            for key, action in (
                ('Umschalt + Mausrad', 'Bildbearbeitungsregler über Schiene oder Griff verstellen'),
                ('Doppelklick', 'Bildbearbeitungsregler auf Standardwert zurücksetzen'),
            ):
                matches = [description for shortcut, description in panels.rows
                           if shortcut.cget('text') == app.translate(key)]
                assert len(matches) == 1 and matches[0].cget('text') == app.translate(action)
            labels = {w.cget('text') for w, _ in panels.labels}
            for source in ('Ansicht und Ergebnisse', 'LUT', 'Ausschnitt', 'Bildbearbeitungsregler',
                           'Horizont und Perspektive', 'Mit der linken Maustaste im Rahmen ziehen',
                           'An einem Griff ziehen', '3 × 3 beim Beschneiden, 9 × 9 beim Ausrichten'):
                assert app.translate(source) in labels
            assert any(child.cget('text') == app.translate('Schließen') for child in help_dialog.winfo_children()
                       if isinstance(child, ttk.Button))

        for lang in ('de', 'en'):
            gui.change_language(lang)
            assert gui.controls_help is help_dialog and help_dialog.title() == app.translate('Bedienhilfe')
            help_dialog.geometry('976x680')
            check_guide(2, False)
            help_dialog.geometry('520x390')
            check_guide(1, True)
            panels.canvas.yview_moveto(0)
            shortcut = panels.rows[0][0]
            if window.tk.call('tk', 'windowingsystem') == 'x11':
                shortcut.event_generate('<Button-5>')
            else:
                shortcut.event_generate('<MouseWheel>', delta=-120)
            window.update()
            assert panels.canvas.yview()[0] > 0
            panels.canvas.yview_moveto(1)
            window.update()
            assert panels.canvas.yview()[1] == 1.0
            assert panels.canvas.yview()[0] > 0
        help_dialog.geometry('976x680')
        check_guide(2, False)
        help_dialog.destroy()

        gui.caption.set('Long file name ' * 40 + 'result.png · 80 × 48 px')
        window.update()
        visible = gui.result_caption.cget('text')
        assert '…' in visible and visible.endswith('result.png · 80 × 48 px'), visible
        assert gui.result_caption.font.measure(visible) <= gui.result_caption.winfo_width()
        window.geometry(f'{app.START_WINDOW_WIDTH}x750')
        window.update()
        assert gui.reuse_result_button.master is gui.browse_controls
        assert gui.reuse_result_button.winfo_rootx() > gui.next_button.winfo_rootx()
        assert controls.keep_check.winfo_rootx() > controls.check.winfo_rootx()
        assert controls.keep_check.winfo_rootx() < controls.choose.winfo_rootx()
        tool_labels = {'100 %', 'Ansicht einpassen', 'Verlauf löschen …'}
        assert len({widget.winfo_height() for widget, label in gui.labels.items() if label in tool_labels}) == 1

        probe = ttk.Menubutton(window, style=controls.choose.cget('style'))
        for language in ('de', 'en'):
            gui.change_language(language)
            window.update()
            assert gui.prev_button.cget('text') == app.translate('Zurück')
            assert gui.next_button.cget('text') == app.translate('Weiter')
            gui.result_position.set(app.translate('Ergebnis {0}/{1}', 100, 100))
            window.update()
            if window.winfo_width() >= app.START_WINDOW_WIDTH:
                assert gui.preview_tools.grid_info()['row'] == 0
            gui.result_position.set(app.translate('Ergebnis {0}/{1}', 2, 2))
            for width in (window.minsize()[0], app.START_WINDOW_WIDTH):
                window.geometry(f'{width}x750')
                window.update()
                bounds = controls.choose.winfo_width(), controls.save_button.grid_info()['row']
                picker = controls.choose.master
                sizes = (language, width, window.winfo_width(), window.minsize())
                unwrapped_width = controls.settings.winfo_reqwidth() + controls.save_button.winfo_reqwidth()
                assert controls.settings.winfo_width() >= controls.settings.winfo_reqwidth(), sizes
                assert bounds[1] == int(controls.frame.winfo_width() < unwrapped_width), sizes
                assert gui.browse_controls.winfo_width() >= gui.browse_controls.winfo_reqwidth(), sizes
                assert abs((controls.choose.winfo_width() - picker.winfo_reqwidth())
                           - (controls.slider.winfo_width() - controls.slider.winfo_reqwidth())) <= 1
                for key, entry in catalog().items():
                    controls.select(key)
                    probe.configure(text=controls.label(entry))
                    window.update_idletasks()
                    assert controls.choose.winfo_width() >= probe.winfo_reqwidth(), (sizes, probe.cget('text'))
                    assert controls.choose.cget('text') == probe.cget('text')
                    assert (controls.choose.winfo_width(), controls.save_button.grid_info()['row']) == bounds
        probe.destroy()

        controls.select(other_look)
        gui.pick_sources(source)
        assert gui.index >= 0 and controls.look().key == first_look
        new_source = root / 'new-image.png'
        Image.new('RGB', (80, 48)).save(new_source)
        controls.select(other_look)
        gui.pick_sources(new_source)
        assert gui.index == -1 and controls.look().key == first_look
        assert controls.look().strength == 95 and not controls.enabled.get()

        gui.pick_sources(source)
        gui.preview_switch.invoke()
        controls.check.toggle()
        controls.select(other_look)
        controls.set_strength(35)
        controls.keep_check.toggle()
        assert controls.kept_look == Look(other_look, 35)
        gui.preview_switch.invoke()
        assert controls.keep.get() and not controls.enabled.get() and gui.compare.look_basis is None
        controls.check.toggle()
        controls.select(first_look)
        controls.set_strength(80)
        assert controls.kept_look == Look(other_look, 35)
        gui.reuse_result_button.invoke()
        assert gui.index == -1 and controls.keep.get() and not controls.enabled.get()
        gui.pick_sources(new_source)
        assert controls.armed() == Look(other_look, 35)
        assert gui.compare.look_basis is gui.compare.before_image
        gui.rotate_source(1)
        assert controls.armed() == Look(other_look, 35)
        gui.rotate_source(None)
        assert controls.armed() == Look(other_look, 35)

        gui.seed_value.set('')
        with patch.object(app.simpledialog, 'askstring', return_value='Series look'):
            gui.save_processing_preset()
        assert gui.processing_presets['Series look']['lut'] == Look(other_look, 35).record()
        assert app.read_settings()['lut'] == {'strength': 35}
        controls.keep_check.toggle()
        gui.load_processing_preset('Standard')
        assert not controls.keep.get() and controls.armed() is None
        gui.load_processing_preset('Series look')
        assert controls.armed() == Look(other_look, 35) and not controls.keep.get()
        gui.pick_sources(source)
        assert gui.index >= 0 and controls.armed() is None and controls.look().key == first_look
        gui.load_processing_preset('Series look')
        assert gui.index == -1 and controls.armed() == Look(other_look, 35)
        assert gui.compare.look_basis is gui.compare.before_image

        batch = root / 'batch'
        batch.mkdir()
        for name, color in (('one.png', '#704924'), ('two.png', '#476429')):
            with Image.new('RGB', (32, 24), color) as image:
                image.save(batch / name)
        gui.pick_sources(batch)
        gui.load_processing_preset('Series look')
        gui.method.set(app.translate(app.METHODS[UPSCALING]))
        gui.choose_method()
        gui.size.set(app.translate(DOUBLE_SIZE))
        gui.upscaler.set(LANCZOS)
        gui.start_clicked()
        wait_for(lambda: gui.action is None)
        assert gui.action is None and len(gui.results) == 2 and not controls.enabled.get()
        for image_path, output, *_ in gui.results:
            with Image.open(image_path) as image, Image.open(output) as result:
                with image.resize(result.size, Image.Resampling.LANCZOS) as scaled:
                    with apply_look(scaled, Look(other_look, 35)) as expected:
                        assert result.size == (64, 48) and result.tobytes() == expected.tobytes()

        gui.action = 'run'
        gui.busy(True)
        gui.preview_switch.invoke()
        image_path, output, crop, rotation = gui.results[-1]
        gui.events.put(('result', (image_path, output, None, crop, rotation, {})))
        wait_for(lambda: len(gui.results) == 3)
        assert gui.index == -1 and gui.compare.after_image is None
        gui.preview_switch.invoke()
        assert gui.index == 1

        with patch.object(Path, 'replace', side_effect=PermissionError('settings denied')):
            gui.events.put(('idle', (False, None)))
            wait_for(lambda: gui.action is None)
            assert 'settings denied' in gui.status.get()
            gui.start_clicked()
            assert gui.action == 'run'
            wait_for(lambda: gui.action is None)
            assert len(gui.results) == 5
        gui.events.put(('status', 'event after settings error'))
        wait_for(lambda: gui.status.get() == 'event after settings error')
        check_microsoft_colorization_controls(gui)
    finally:
        window.destroy()


if __name__ == '__main__':
    for key, entry in catalog().items():
        table = app.ROOT / 'assets/luts' / entry['file']
        assert sha256(table.read_bytes()).hexdigest() == entry['sha256']
        with apply_look(Image.new('RGB', (2, 2)), Look(key, 25)):
            pass
    with TemporaryDirectory() as temp:
        directory = Path(temp)
        check_downloads(directory)
        test_export(directory)
        test_numbered_exports(directory)
        test_microsoft_colorization_export(directory)
        exiftool = os.environ.get('RESTORENATE_TEST_EXIFTOOL') or exiftool_executable(app.ROOT)
        test_metadata(directory, exiftool)
        test_gui(directory)
    print('All bundled LUTs, rotate/reference layout, LUT keyboard controls, native exports, ordered XMP and numbering passed.')
