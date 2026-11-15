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
        assert window.winfo_height() >= window.minsize()[1]
        window.geometry('950x720')
        gui.pick_sources(source)
        for language in ('de', 'en'):
            gui.change_language(language)
            window.update()
            right = gui.look_controls.save_button
            assert right.winfo_rootx() + right.winfo_width() < window.winfo_rootx() + window.winfo_width()
            assert gui.compare.winfo_height() > 380
            check_reference_controls(gui, source)
            pane = gui.settings_panel
            assert window.winfo_height() >= window.minsize()[1]
            assert pane.winfo_height() >= pane.winfo_reqheight()
            assert gui.setup_notice.winfo_width() >= gui.setup_notice.winfo_reqwidth()
            assert gui.compare.winfo_rooty() + gui.compare.winfo_height() <= gui.result_actions.winfo_rooty()
            assert gui.result_actions.winfo_rooty() + gui.result_actions.winfo_height() <= gui.result_navigation.winfo_rooty()
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
        gui.input_view_button.invoke()
        assert gui.index == -1 and gui.compare.after_image is None and not controls.enabled.get()
        assert gui.prev_button.instate(['disabled']) and gui.next_button.instate(['disabled'])
        gui.move(1)
        assert gui.index == -1
        controls.check.toggle()
        assert gui.compare.look_basis is gui.compare.before_image
        gui.result_view_button.invoke()
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
        gui.input_view_button.invoke()
        gui.result_view_button.invoke()
        assert gui.index == 0
        gui.next_button.invoke()
        gui.input_view_button.invoke()
        gui.result_view_button.invoke()
        assert gui.index == 1

        style = ttk.Style(window)
        assert style.lookup('Input.Help.TButton', 'foreground') == app.GOLD_LIGHT
        assert style.lookup('Input.Help.TButton', 'focuscolor') == app.GOLD_LIGHT

        gui.caption.set('Long file name ' * 40 + 'result.png · 80 × 48 px')
        window.update()
        visible = gui.result_caption.cget('text')
        assert '…' in visible and visible.endswith('result.png · 80 × 48 px'), visible
        assert gui.result_caption.font.measure(visible) <= gui.result_caption.winfo_width()
        window.geometry('1130x750')
        window.update()
        available = gui.result_actions.winfo_width()
        needed = controls.frame.winfo_reqwidth() + gui.reuse_result_button.winfo_reqwidth() + 8
        assert gui.reuse_result_button.grid_info()['row'] == int(available < needed)
        if available >= needed:
            assert controls.save_button.winfo_rootx() < gui.reuse_result_button.winfo_rootx()
        else:
            assert controls.save_button.winfo_rooty() < gui.reuse_result_button.winfo_rooty()

        probe = ttk.Menubutton(window, style=controls.choose.cget('style'))
        for language in ('de', 'en'):
            gui.change_language(language)
            for width in (950, 1600):
                window.geometry(f'{width}x750')
                window.update()
                bounds = (controls.choose.winfo_width(), gui.reuse_result_button.grid_info()['row'])
                picker = controls.choose.master
                assert abs((controls.choose.winfo_width() - picker.winfo_reqwidth())
                           - (controls.slider.winfo_width() - controls.slider.winfo_reqwidth())) <= 1
                for key, entry in catalog().items():
                    controls.select(key)
                    probe.configure(text=controls.label(entry))
                    window.update_idletasks()
                    # Builds may run with a small desktop or different font scaling.
                    # The picker and slider split the space left after the fixed controls.
                    name_extra = max(0, probe.winfo_reqwidth() - picker.winfo_reqwidth())
                    free = controls.frame.winfo_width() - controls.frame.winfo_reqwidth()
                    if free >= 2 * name_extra:
                        assert controls.choose.winfo_width() >= probe.winfo_reqwidth()
                    assert controls.choose.cget('text') == probe.cget('text')
                    assert (controls.choose.winfo_width(), gui.reuse_result_button.grid_info()['row']) == bounds
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
