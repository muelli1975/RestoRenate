"""Check the packaged Windows UI and model default with a local test image."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

from PIL import Image


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

import app
from methods import DDCOLOR_TINY, LANCZOS, NOMOS2_HQ, ULTRASHARP_LITE, UPSCALING, resolve_upscaler
from theme import BORDER, DANGER_TEXT, GOLD_LIGHT
from output_destination import check_output_destination


assert resolve_upscaler(UPSCALING) == ULTRASHARP_LITE
assert resolve_upscaler(UPSCALING, NOMOS2_HQ) == NOMOS2_HQ
assert resolve_upscaler(DDCOLOR_TINY) == LANCZOS
assert app.BUILTIN_PROCESSING_PRESETS['Standard']['upscaler'] == ULTRASHARP_LITE

image_path = root.parent / 'reference.png'
with Image.new('RGB', (48, 32), '#303030') as image:
    image.save(image_path)

window = tk.Tk()
try:
    gui = app.Application(window)
    window.geometry('950x720')
    gui.pick_sources(image_path)
    gui.set_second_image(image_path)
    window.update()
    remove = gui.remove_second_button
    style = ttk.Style(window)
    assert remove.winfo_viewable() and not remove.instate(['disabled'])
    assert remove.cget('text') == '\u00d7'
    assert style.lookup(remove.cget('style'), 'foreground') == DANGER_TEXT
    assert remove.winfo_width() >= remove.winfo_reqwidth()
    remove.invoke()
    assert gui.second_image is None
    for field in ('TEntry', 'Path.TEntry', 'TSpinbox', 'TCombobox'):
        for states, color in [((), BORDER), (('focus',), GOLD_LIGHT), (('disabled', 'focus'), BORDER)]:
            assert style.lookup(field, 'bordercolor', states) == color, (field, states)
finally:
    window.destroy()

print('Windows model default, field focus and red remove control passed.')

check_output_destination()
