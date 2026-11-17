"""Check the packaged Windows UI and model default with a local test image."""
import ctypes
from ctypes import wintypes
from pathlib import Path
from queue import Queue
import sys
from threading import Thread
from time import monotonic, sleep
import tkinter as tk
from tkinter import font, ttk

from PIL import Image, ImageChops, ImageGrab


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

import app
from methods import (DDCOLOR_TINY, LANCZOS, NOMOS2_HQ, SEEDVR2, ULTRASHARP_LITE, UPSCALE_MENU_SECTIONS,
                     UPSCALING, resolve_upscaler)
from field_focus import check_field_focus, field_focus_maps
from output_destination import check_output_destination
from reference_controls import check_reference_controls
from sizes import FULL_HD


def capture_popup(menu, destination, headings=()):
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    result = Queue()
    heading_centers = [(menu.yposition(index) + menu.yposition(index + 1)) // 2 for index in headings]
    user32.SetCursorPos(0, 0)

    def capture():
        try:
            deadline = monotonic() + 4
            while monotonic() < deadline:
                popup = user32.FindWindowW('#32768', None)
                if popup and user32.IsWindowVisible(popup):
                    sleep(0.25)  # Let Windows finish animating the native popup.
                    bounds = wintypes.RECT()
                    if user32.GetWindowRect(popup, ctypes.byref(bounds)):
                        box = bounds.left, bounds.top, bounds.right, bounds.bottom
                        with ImageGrab.grab(box) as screenshot:
                            screenshot.save(destination)
                            for y in heading_centers:
                                user32.SetCursorPos(bounds.left + screenshot.width // 2, bounds.top + y)
                                sleep(0.15)
                                with ImageGrab.grab(box) as hovered:
                                    assert not ImageChops.difference(screenshot, hovered).getbbox(), (destination, y)
                            result.put(screenshot.width)
                            return
                sleep(0.03)
            result.put(AssertionError('Native menu did not appear'))
        except Exception as error:
            result.put(error)
        finally:
            user32.keybd_event(0x1B, 0, 0, 0)  # Escape closes TrackPopupMenu.
            user32.keybd_event(0x1B, 0, 2, 0)

    Thread(target=capture, daemon=True).start()
    menu.post(32, 32)
    width = result.get(timeout=5)
    if isinstance(width, Exception):
        raise width
    return width


def check_native_menus(gui):
    window = gui.window
    controls = gui.look_controls
    controls.check.toggle()
    for language in ('de', 'en'):
        gui.change_language(language)
        window.update()
        window.focus_force()
        method_menu = gui.method_menu
        headings = [method_menu.index(app.translate(heading)) for heading in ('Bearbeiten', 'Kolorieren')]
        capture_popup(method_menu, root.parent / f'model-menu-{language}.png', headings)
        upscale_menu = gui.upscale_menu
        headings = [upscale_menu.index(app.translate(heading)) for heading, _ in UPSCALE_MENU_SECTIONS]
        capture_popup(upscale_menu, root.parent / f'upscaler-menu-{language}.png', headings)
        for name, menu in (('model-submenu', method_menu), ('lut-menu', controls.menu)):
            group_font = font.Font(window, font=menu.cget('font'))
            choices = [(group_font.measure(group.entrycget(index, 'label')), group, index)
                       for group, index in menu.choices.values() if group is not menu]
            text_width, group, index = max(choices, key=lambda option: option[0])
            group.invoke(index)
            width = capture_popup(group, root.parent / f'{name}-{language}.png')
            assert width >= text_width + 14, (language, name, width, text_width, group.entrycget(index, 'label'))
            print(f'{language} {name} has {width}px for a {text_width}px label and its checkmark.')


def check_closed_upscaler(gui):
    window, button = gui.window, gui.upscale_options
    previous_size, previous_upscaler = gui.size.get(), gui.upscaler.get()
    gui.size.set(app.translate(FULL_HD))
    gui.upscaler.set(NOMOS2_HQ)
    gui.update_size_controls()
    window.update()
    left, top = button.winfo_rootx(), button.winfo_rooty()
    box = (left, top, left + button.winfo_width(), top + button.winfo_height())
    with ImageGrab.grab(box) as labelled:
        button.configure(textvariable='', text='')
        window.update()
        with ImageGrab.grab(box) as blank:
            bounds = ImageChops.difference(labelled, blank).getbbox()
        labelled.save(root.parent / 'upscaler-field.png')
    gui.size.set(previous_size)
    gui.upscaler.set(previous_upscaler)
    gui.update_size_controls()
    style_font = ttk.Style(window).lookup(button.cget('style'), 'font') or 'TkDefaultFont'
    text_width = font.Font(window, font=style_font).measure(NOMOS2_HQ)
    assert bounds and bounds[2] - bounds[0] >= text_width - 6, (bounds, text_width)


assert resolve_upscaler(UPSCALING) == NOMOS2_HQ
assert resolve_upscaler(UPSCALING, ULTRASHARP_LITE) == ULTRASHARP_LITE
assert resolve_upscaler(DDCOLOR_TINY) == LANCZOS
assert app.BUILTIN_PROCESSING_PRESETS['Standard']['upscaler'] == NOMOS2_HQ
assert app.BUILTIN_PROCESSING_PRESETS['Detailrekonstruktion']['upscaler'] == SEEDVR2

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
    popup = str(window.tk.call('ttk::combobox::PopdownWindow', str(gui.size_widget)))
    assert window.tk.call(popup + '.f.sb', 'cget', '-style') == ''
    style = ttk.Style(window)
    assert style.lookup('Vertical.TScrollbar', 'background') == app.BORDER
    assert style.lookup('Vertical.TScrollbar', 'troughcolor') == app.SECONDARY_BG
    assert style.lookup('Vertical.TScrollbar', 'arrowcolor') == app.MUTED
    assert style.lookup('Vertical.TScrollbar', 'background', ('active',)) == app.HOVER_BG
    check_field_focus(gui, native_focus)
    check_closed_upscaler(gui)
    check_native_menus(gui)
finally:
    window.destroy()

print('Windows model default, field focus, reference controls and dropdown styles passed.')

check_output_destination()
