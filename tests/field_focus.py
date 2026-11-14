"""Compare field focus to the platform's Clam theme, as used by TransCora."""
from tkinter import ttk

from theme import BORDER, GOLD_LIGHT


FIELD_STYLES = ('TEntry', 'TSpinbox', 'TCombobox')
BORDER_OPTIONS = ('bordercolor', 'lightcolor', 'darkcolor')


def field_focus_maps(window):
    style = ttk.Style(window)
    return {field: {option: style.map(field, option) for option in BORDER_OPTIONS}
            for field in FIELD_STYLES}


def check_field_focus(gui, native_maps):
    window = gui.window
    assert field_focus_maps(window) == native_maps
    style = ttk.Style(window)
    for field in ('TEntry', 'Path.TEntry', 'TSpinbox', 'TCombobox', 'Prompt.TMenubutton'):
        assert all(style.lookup(field, option, ('focus',)) != GOLD_LIGHT for option in BORDER_OPTIONS), field

    assert gui.prompt.cget('highlightcolor') == GOLD_LIGHT
    assert gui.prompt.cget('highlightbackground') == BORDER
