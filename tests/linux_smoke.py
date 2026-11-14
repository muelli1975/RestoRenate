"""Exercise packaged Linux setup, graphics controls and real CPU exports."""
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from xml.etree import ElementTree

from PIL import Image


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

import app
from imaging import exiftool_executable, save_result
from local_backend import Backend
from methods import DDCOLOR_TINY, LANCZOS, NOMOS2_HQ, UPSCALING
from photo_colors import Colorizer
from portable_setup import CPU, LINUX, Setup
from preload_models import PreloadDialog
from restoration import Client, restore, select_models
from sizes import DOUBLE_SIZE, NO_RESCALE


def record(method, models):
    return {'method': method, 'models': models, 'prompt': '', 'seed': None}


def test_gui(source):
    window = tk.Tk()
    try:
        gui = app.Application(window)
        window.geometry('950x720')
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


def test_cpu(source, folder):
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

    setup = Setup(root, method=UPSCALING, upscaler=NOMOS2_HQ, compute=CPU)
    paths = setup.ensure()
    assert setup.runtime_ready() and setup.ready()
    assert setup.ensure() == paths
    backend = Backend(root, compute=CPU)
    try:
        client = Client(backend.start(paths, method=UPSCALING), root)
        assert client.device() == 'CPU'
        definitions = client.json('/object_info')
        models = select_models(definitions, UPSCALING, NOMOS2_HQ)
        output, warning = restore(client, models, source, folder, 'PNG', None, '', None, print, lambda: False,
                                  record(UPSCALING, models), method=UPSCALING, upscaler=NOMOS2_HQ,
                                  size_choice=(DOUBLE_SIZE, 0), definitions=definitions)
        assert not warning
        with Image.open(output) as result:
            assert result.size == (128, 80) and 'workflow' in result.info
    finally:
        backend.close()


def test_metadata(source, folder):
    exiftool = exiftool_executable(root)
    settings = {'method': 'linux-smoke-test', 'seed': 17}
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
    assert LINUX and app.ROOT == root
    folder = root / 'work/smoke'
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / 'portrait.jpg'
    with Image.linear_gradient('L').resize((64, 40)).convert('RGB') as image:
        exif = image.getexif()
        exif[271] = 'RestoRenate test'
        image.save(source, exif=exif)
    test_gui(source)
    test_metadata(source, folder / 'output')
    test_cpu(source, folder / 'output')
    print('Linux GUI, real ExifTool JPEG/TIFF export, DDColor Tiny and Nomos2 CPU upscaling passed.')
