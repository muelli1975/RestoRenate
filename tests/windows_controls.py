"""Check the packaged Windows UI and model default with a local test image."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageGrab


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

import app
from methods import DDCOLOR_TINY, LANCZOS, NOMOS2_HQ, ULTRASHARP_LITE, UPSCALING, resolve_upscaler
from field_focus import check_field_focus, field_focus_maps
from output_destination import check_output_destination
from reference_controls import check_reference_controls


assert resolve_upscaler(UPSCALING) == NOMOS2_HQ
assert resolve_upscaler(UPSCALING, ULTRASHARP_LITE) == ULTRASHARP_LITE
assert resolve_upscaler(DDCOLOR_TINY) == LANCZOS
assert app.BUILTIN_PROCESSING_PRESETS['Standard']['upscaler'] == NOMOS2_HQ

image_path = root.parent / 'reference.png'
with Image.new('RGB', (48, 32), '#303030') as image:
    image.save(image_path)

window = tk.Tk()
try:
    ttk.Style(window).theme_use('clam')
    native_focus = field_focus_maps(window)
    gui = app.Application(window)
    window.geometry('950x720')
    gui.pick_sources(image_path)
    check_reference_controls(gui, image_path)
    gui.set_second_image(image_path)
    window.lift()
    window.update()
    gui.update_window_minimum()
    row = gui.second_row
    left, top = row.winfo_rootx(), row.winfo_rooty()
    with ImageGrab.grab((left, top, left + row.winfo_width(), top + row.winfo_height())) as screenshot:
        screenshot.save(root.parent / 'reference-controls.png')
    popup = str(window.tk.call('ttk::combobox::PopdownWindow', str(gui.upscale_options)))
    assert window.tk.call(popup + '.f.sb', 'cget', '-style') == ''
    style = ttk.Style(window)
    assert style.lookup('Vertical.TScrollbar', 'background') == app.BORDER
    assert style.lookup('Vertical.TScrollbar', 'troughcolor') == app.SECONDARY_BG
    assert style.lookup('Vertical.TScrollbar', 'arrowcolor') == app.MUTED
    assert style.lookup('Vertical.TScrollbar', 'background', ('active',)) == app.HOVER_BG
    check_field_focus(gui, native_focus)
finally:
    window.destroy()

print('Windows model default, field focus, reference controls and dropdown styles passed.')

check_output_destination()
