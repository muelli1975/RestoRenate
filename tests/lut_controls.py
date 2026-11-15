"""Exercise real LUT files, composition metadata and the Tk controls."""
import json
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

from PIL import Image

if len(sys.argv) > 1:
    sys.path.insert(0, str(Path(sys.argv[1]) / '_internal'))
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app
from crop import CropRegion
from export_metadata import editor_graph
from imaging import exiftool_executable
from looks import Look, apply_look, catalog
from methods import LANCZOS, UPSCALING
from restoration import export_look_variant, restore
from sizes import DOUBLE_SIZE
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


def test_gui(root):
    window = tk.Tk()
    window.attributes('-alpha', 0)
    try:
        app.SETTINGS = root / 'settings.json'
        app.JOBS_LOG = root / 'jobs.jsonl'
        source = root / 'scene.png'
        first_look, other_look, *_ = catalog()
        app.SETTINGS.write_text(json.dumps({'lut': {'id': other_look, 'strength': 100}}), encoding='utf-8')
        gui = app.Application(window)
        assert gui.look_controls.key == first_look
        window.update()
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
        key_before = controls.key
        for name in ('c', 'Right'):
            widget.event_generate(f'<KeyPress-{name}>')
            if name == 'Right':
                widget.event_generate('<KeyRelease-Right>')
        widget.event_generate('<KeyRelease-c>')
        time.sleep(.025)
        window.update()
        assert controls.enabled.get() and gui.compare.look_basis is original
        assert controls.key != key_before
        controls.step(-5)
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
        deadline = time.monotonic() + 8
        while gui.action and time.monotonic() < deadline:
            window.update()
            time.sleep(.025)
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
        assert gui.result_position.get() == '1/1' and gui.result_counter.winfo_manager() == 'pack'
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
        assert controls.key != first_look and controls.look().strength == 95
        assert gui.second_button.cget('text') == app.translate('Bild …')

        controls.check.toggle()
        gui.create_lut_variant()
        deadline = time.monotonic() + 8
        while gui.action and time.monotonic() < deadline:
            window.update()
            time.sleep(.025)
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
        help_button.invoke()
        assert gui.controls_help.winfo_exists()
        gui.controls_help.destroy()

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

        probe = ttk.Menubutton(window, style=controls.choose.cget('style'))
        for language in ('de', 'en'):
            gui.change_language(language)
            window.update()
            assert gui.prev_button.cget('text') == app.translate('Zurück')
            assert gui.next_button.cget('text') == app.translate('Weiter')
            gui.result_position.set('100/100')
            window.update()
            if window.winfo_width() >= app.START_WINDOW_WIDTH:
                assert gui.preview_tools.grid_info()['row'] == 0
            gui.result_position.set('2/2')
            for width in (window.minsize()[0], 1600):
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
                    # Builds may run with a small desktop or different font scaling.
                    # The picker and slider split the space left after the fixed controls.
                    name_extra = max(0, probe.winfo_reqwidth() - picker.winfo_reqwidth())
                    free = controls.settings.winfo_width() - controls.settings.winfo_reqwidth()
                    if free >= 2 * name_extra:
                        assert controls.choose.winfo_width() >= probe.winfo_reqwidth()
                    assert controls.choose.cget('text') == probe.cget('text')
                    assert (controls.choose.winfo_width(), controls.save_button.grid_info()['row']) == bounds
        probe.destroy()

        controls.select(other_look)
        gui.pick_sources(source)
        assert gui.index >= 0 and controls.key == first_look
        new_source = root / 'new-image.png'
        Image.new('RGB', (80, 48)).save(new_source)
        controls.select(other_look)
        gui.pick_sources(new_source)
        assert gui.index == -1 and controls.key == first_look
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
        assert gui.index >= 0 and controls.armed() is None and controls.key == first_look
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
        deadline = time.monotonic() + 8
        while gui.action and time.monotonic() < deadline:
            window.update()
            time.sleep(.025)
        assert gui.action is None and len(gui.results) == 2 and not controls.enabled.get()
        for image_path, output, *_ in gui.results:
            with Image.open(image_path) as image, Image.open(output) as result:
                with image.resize(result.size, Image.Resampling.LANCZOS) as scaled:
                    with apply_look(scaled, Look(other_look, 35)) as expected:
                        assert result.size == (64, 48) and result.tobytes() == expected.tobytes()
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
        exiftool = os.environ.get('RESTORENATE_TEST_EXIFTOOL') or exiftool_executable(app.ROOT)
        test_metadata(directory, exiftool)
        test_gui(directory)
    print('All bundled LUTs, rotate/reference layout, LUT keyboard controls, native exports, ordered XMP and numbering passed.')
