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
from theme import BORDER, DANGER_TEXT, GOLD_LIGHT
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
    gui = app.Application(window)
    window.geometry('950x720')
    gui.pick_sources(image_path)
    check_reference_controls(gui, image_path)
    gui.set_second_image(image_path)
    window.lift()
    window.update()
    row = gui.second_row
    left, top = row.winfo_rootx(), row.winfo_rooty()
    with ImageGrab.grab((left, top, left + row.winfo_width(), top + row.winfo_height())) as screenshot:
        screenshot.save(root.parent / 'reference-controls.png')
        remove = gui.remove_second_button
        x, y = remove.winfo_rootx() - left, remove.winfo_rooty() - top
        width, height = remove.winfo_width(), remove.winfo_height()
        red = tuple(bytes.fromhex(DANGER_TEXT[1:]))
        pixels = [(dx, dy) for dy in range(height) for dx in range(width)
                  if screenshot.getpixel((x + dx, y + dy))[:3] == red]
        assert pixels, 'The rendered button has no red cross.'
        center_x = (min(dx for dx, _ in pixels) + max(dx for dx, _ in pixels)) / 2
        center_y = (min(dy for _, dy in pixels) + max(dy for _, dy in pixels)) / 2
        assert abs(center_x - (width - 1) / 2) <= 1
        assert abs(center_y - (height - 1) / 2) <= 1
    style = ttk.Style(window)
    for field in ('TEntry', 'Path.TEntry', 'TSpinbox', 'TCombobox'):
        for states, color in [((), BORDER), (('focus',), GOLD_LIGHT), (('disabled', 'focus'), BORDER)]:
            assert style.lookup(field, 'bordercolor', states) == color, (field, states)
finally:
    window.destroy()

print('Windows model default, field focus and red remove control passed.')

check_output_destination()
