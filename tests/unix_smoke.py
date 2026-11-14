"""Exercise packaged Unix setup, graphics controls and real exports."""
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from xml.etree import ElementTree

from PIL import Image


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

import app
from imaging import exiftool_executable, save_result
from local_backend import Backend
from methods import DDCOLOR_TINY, LANCZOS, NOMOS2_HQ, ULTRASHARP_LITE, UPSCALING, resolve_upscaler
from photo_colors import Colorizer
from portable_setup import CPU, MACOS, MPS, UNIX_RUNTIME, Setup
from preload_models import PreloadDialog
from restoration import Client, restore, select_models
from sizes import DOUBLE_SIZE, NO_RESCALE
from theme import BORDER, GOLD_LIGHT
from output_destination import check_output_destination


def record(method, models):
    return {'method': method, 'models': models, 'prompt': '', 'seed': None}


def test_gui(source):
    window = tk.Tk()
    try:
        gui = app.Application(window)
        window.geometry('950x720')
        style = ttk.Style(window)
        for field in ('TEntry', 'Path.TEntry', 'TSpinbox', 'TCombobox'):
            assert style.lookup(field, 'bordercolor', ('focus',)) == GOLD_LIGHT, field
            assert style.lookup(field, 'bordercolor', ('focus', 'disabled')) == BORDER, field
            assert style.lookup(field, 'bordercolor') == BORDER, field
        gui.pick_sources(source)
        gui.set_second_image(source)
        gui.second_rotation_menu.invoke(1)
        window.update()
        assert gui.second_rotation == 1
        assert gui.second_thumbnail.height() > gui.second_thumbnail.width()
        assert gui.remove_second_button.winfo_width() >= gui.remove_second_button.winfo_reqwidth()
        gui.remove_second_button.invoke()
        assert gui.second_image is None
        dialog = PreloadDialog(window, root, CPU, gui.current_method, LANCZOS, False, False)
        assert dialog.runtime_status.get()
        assert dialog.lightning
        dialog.destroy()
    finally:
        window.destroy()


def test_colorization(source, folder):
    setup = Setup(root, method=DDCOLOR_TINY, compute=CPU)
    assert setup.color_runtime_path is None and setup.runtime is None
    assert setup.ensure() is None and setup.ready()
    colorizer = Colorizer(setup.colorizer_path, method=DDCOLOR_TINY)
    models = {'colorizer': colorizer.model_name}
    output, warning = restore(None, models, source, folder, 'PNG', None, '', None, print, lambda: False,
                              record(DDCOLOR_TINY, models), method=DDCOLOR_TINY, upscaler=LANCZOS,
                              size_choice=(NO_RESCALE, 0), colorizer=colorizer)
    assert not warning
    with Image.open(output) as result:
        assert result.size == (64, 40) and result.mode == 'RGB'


def test_upscaling(source, folder):
    compute = MPS if MACOS else CPU
    setup = Setup(root, method=UPSCALING, compute=compute)
    paths = setup.ensure()
    assert setup.runtime_ready() and setup.ready()
    assert setup.ensure() == paths
    backend = Backend(root, compute=compute)
    try:
        client = Client(backend.start(paths, method=UPSCALING), root)
        device = client.json('/system_stats')['devices'][0]
        assert device['type'] == compute, device
        definitions = client.json('/object_info')
        models = select_models(definitions, UPSCALING)
        assert models['upscale'] == '4xNomos2_hq_mosr.safetensors', models
        output, warning = restore(client, models, source, folder, 'PNG', None, '', None, print, lambda: False,
                                  record(UPSCALING, models), method=UPSCALING,
                                  size_choice=(DOUBLE_SIZE, 0), definitions=definitions)
        assert not warning
        with Image.open(output) as result:
            assert result.size == (128, 80) and 'workflow' in result.info
    finally:
        backend.close()


def test_metadata(source, folder):
    exiftool = exiftool_executable(root)
    assert exiftool == root / 'tools/exiftool/exiftool'
    settings = {'method': 'unix-smoke-test', 'seed': 17}
    with Image.open(source) as image:
        jpg, _ = save_result(image, source, folder, 'JPEG 95 · 4:4:4', None, exiftool, settings=settings)
        tif, _ = save_result(image, source, folder, 'TIFF', None, exiftool)
    for result in (jpg, tif):
        tags = json.loads(subprocess.check_output([exiftool, '-j', '-Make', '-Orientation#', result]))[0]
        assert tags['Make'] == 'RestoRenate test' and tags['Orientation'] == 1, tags
    packet = subprocess.check_output([exiftool, '-b', '-XMP', jpg])
    document = ElementTree.fromstring(packet)
    tag = '{urn:uuid:c36b8290-0ca0-42fd-9c7b-60831da61924}Settings'
    for node in document.iter():
        if entry := (node.text if node.tag == tag else node.get(tag)):
            assert json.loads(entry) == settings
            break
    else:
        raise AssertionError('Missing RestoRenate XMP settings')


if __name__ == '__main__':
    assert UNIX_RUNTIME and app.ROOT == root
    assert Path(sys.executable).is_relative_to(root / 'runtime/python')
    assert (root / 'vendor/ComfyUI/main.py').is_file()
    assert resolve_upscaler(UPSCALING) == NOMOS2_HQ
    assert resolve_upscaler(UPSCALING, ULTRASHARP_LITE) == ULTRASHARP_LITE
    assert resolve_upscaler(DDCOLOR_TINY) == LANCZOS
    folder = root / 'work/smoke'
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / 'portrait.jpg'
    with Image.linear_gradient('L').resize((64, 40)).convert('RGB') as image:
        exif = image.getexif()
        exif[271] = 'RestoRenate test'
        image.save(source, exif=exif)
    test_gui(source)
    check_output_destination()
    test_metadata(source, folder / 'output')
    test_colorization(source, folder / 'output')
    test_upscaling(source, folder / 'output')
    print(f'GUI, real ExifTool JPEG/TIFF export, DDColor Tiny and Nomos2 HQ MoSR on {MPS if MACOS else CPU} passed.')
