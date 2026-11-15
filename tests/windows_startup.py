"""Verify the released Python/Tk runtime shows the main window at full size."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
from unittest.mock import patch


root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / '_internal'))

import app


user32 = ctypes.WinDLL('user32', winmode=0x00000800)
user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
user32.GetAncestor.restype = wintypes.HWND
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
user32.GetClientRect.restype = wintypes.BOOL


def hwnd(window):
    return user32.GetAncestor(window.winfo_id(), 2)


def native_size(window):
    rect = wintypes.RECT()
    assert user32.GetClientRect(hwnd(window), ctypes.byref(rect))
    return rect.right, rect.bottom


visible_sizes = []
final_sizes = []
transition_events = []
validation_errors = []
create_window = app.create_window
Application = app.Application
set_transitions = app.set_window_transitions_disabled
transition_supported = False


def create_observed_window():
    window = create_window()
    assert not user32.IsWindowVisible(hwnd(window)), 'The icon exposed an unconfigured window'
    return window


def build_observed_application(window):
    gui = Application(window)
    assert not user32.IsWindowVisible(hwnd(window)), 'The window became visible during layout'

    def observe(event):
        if event.widget is window and user32.IsWindowVisible(hwnd(window)):
            visible_sizes.append(native_size(window))

    map_binding = window.bind('<Map>', observe, add='+')
    configure_binding = window.bind('<Configure>', observe, add='+')

    def finish():
        try:
            final_sizes.append(native_size(window))
            assert final_sizes[-1][1] >= window.minsize()[1], final_sizes
            window.unbind('<Map>', map_binding)
            window.unbind('<Configure>', configure_binding)
            method = next(method for method in gui.method_ids.values() if method in app.TWO_IMAGE_METHODS)
            for language in ('de', 'en'):
                gui.change_language(language)
                gui.method.set(app.translate(app.METHODS[app.UPSCALING]))
                gui.choose_method()
                window.geometry('950x720')
                window.update()
                gui.method.set(app.translate(app.METHODS[method]))
                gui.choose_method()
                window.update()
                assert native_size(window)[1] >= window.minsize()[1]
                settings = gui.settings_panel
                assert settings.winfo_height() >= settings.winfo_reqheight()
                settings_bottom = settings.winfo_rooty() + settings.winfo_height()
                for widget in (gui.prompt, gui.seed_entry, gui.start_button, gui.stop_button):
                    assert widget.winfo_ismapped()
                    assert widget.winfo_height() >= widget.winfo_reqheight()
                    assert widget.winfo_rooty() + widget.winfo_height() <= settings_bottom
        except Exception as exc:
            validation_errors.append(exc)
        finally:
            gui.destroy_window()

    window.after(350, finish)
    return gui


def observe_transitions(window, disabled):
    transition_events.append((disabled, bool(user32.IsWindowVisible(hwnd(window)))))
    global transition_supported
    supported = set_transitions(window, disabled)
    if disabled:
        transition_supported = supported
    return supported


with (patch.object(app, 'create_window', create_observed_window),
      patch.object(app, 'Application', build_observed_application),
      patch.object(app, 'set_window_transitions_disabled', observe_transitions)):
    app.run_gui()

if validation_errors:
    raise validation_errors[0]
assert len(final_sizes) == 1 and min(final_sizes[0]) >= 700, final_sizes
# Windows can fit the requested size to the available desktop.
assert visible_sizes and set(visible_sizes) == set(final_sizes), (visible_sizes, final_sizes)
assert transition_events[0] == (True, False), transition_events
if transition_supported:
    assert transition_events == [(True, False), (False, True)], transition_events
print(f'Windows startup: first visible size {visible_sizes[0]}, transition events {transition_events}.')
