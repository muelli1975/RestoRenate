"""Stereo-Tools colors and TransCora widget states for the photo app."""
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageTk

APP_BG = '#111111'
SECONDARY_BG = '#181818'
PANEL_BG = '#202020'
HOVER_BG = '#282828'
BORDER = '#333333'
TEXT = '#f2f2f2'
MUTED = '#b8b8b8'
DISABLED = '#727272'
GOLD = '#9c7c38'
GOLD_LIGHT = '#c6a95e'
DANGER = '#7f3939'
DANGER_HOVER = '#944545'
DANGER_TEXT = '#ed8585'
PREVIEW_BG = '#000000'


def checkbox(parent, text, variable, command=None):
    return ctk.CTkCheckBox(parent, text=text, variable=variable, command=command,
                           bg_color=PANEL_BG, fg_color=GOLD, hover_color=GOLD_LIGHT,
                           border_color=BORDER, checkmark_color=TEXT, text_color=TEXT,
                           text_color_disabled=DISABLED, corner_radius=4, font=('Segoe UI', 13))


def remove_icon(master, mask, color):
    with Image.new('RGBA', mask.size, color) as image:
        image.putalpha(mask)
        return ImageTk.PhotoImage(image, master=master)


def set_control_state(widget, state):
    if isinstance(widget, ctk.CTkCheckBox):
        widget.configure(state=state, fg_color=DISABLED if state == 'disabled' else GOLD,
                         hover_color=DISABLED if state == 'disabled' else GOLD_LIGHT)
    else:
        widget.configure(state=state)


def style_method_scrollbar(combobox):
    if combobox.tk.call('tk', 'windowingsystem') == 'aqua':
        return
    # Tk uses a native menu on macOS and a separate scrollbar elsewhere.
    popup = combobox.tk.call('ttk::combobox::PopdownWindow', str(combobox))
    scrollbar = next((path for path in (f'{popup}.f.sb', f'{popup}.sb')
                      if combobox.tk.getboolean(combobox.tk.call('winfo', 'exists', path))), None)
    if scrollbar is None:
        return
    style_name = 'Method.Vertical.TScrollbar'
    style = ttk.Style(combobox)
    style.layout(style_name, [
        ('Vertical.Scrollbar.trough', {'sticky': 'ns', 'children': [
            ('Vertical.Scrollbar.thumb', {'sticky': 'nswe'}),
        ]}),
    ])
    style.configure(style_name, troughcolor=PANEL_BG, bordercolor=PANEL_BG,
                    background='#666666', lightcolor='#666666', darkcolor='#666666',
                    arrowsize=11)
    thumb_colors = [('pressed', '#929292'), ('active', '#7c7c7c')]
    style.map(style_name, background=thumb_colors, lightcolor=thumb_colors, darkcolor=thumb_colors)

    combobox.tk.call(scrollbar, 'configure', '-style', style_name)


def apply_theme(window):
    ctk.set_appearance_mode('dark')
    style = ttk.Style(window)
    style.theme_use('clam')
    style.configure('.', background=APP_BG, foreground=TEXT, font=('Segoe UI', 10),
                    bordercolor=BORDER, darkcolor=BORDER, lightcolor=BORDER, focuscolor=GOLD_LIGHT)
    style.configure('TButton', background=SECONDARY_BG, foreground=TEXT, padding=(9, 5), focusthickness=1)
    style.map('TButton', background=[('disabled', SECONDARY_BG), ('active', HOVER_BG)],
              foreground=[('disabled', DISABLED)], bordercolor=[('disabled', BORDER), ('active', GOLD)],
              darkcolor=[('disabled', BORDER), ('active', GOLD)], lightcolor=[('disabled', BORDER), ('active', GOLD)])
    style.configure('Primary.TButton', background=SECONDARY_BG, foreground=GOLD_LIGHT,
                    bordercolor=GOLD, darkcolor=GOLD, lightcolor=GOLD)
    style.map('Primary.TButton', background=[('disabled', SECONDARY_BG), ('active', GOLD_LIGHT)],
              foreground=[('disabled', DISABLED), ('active', APP_BG)],
              bordercolor=[('disabled', BORDER), ('active', GOLD_LIGHT)],
              darkcolor=[('disabled', BORDER), ('active', GOLD_LIGHT)],
              lightcolor=[('disabled', BORDER), ('active', GOLD_LIGHT)])
    style.configure('TMenubutton', background=SECONDARY_BG, foreground=TEXT, padding=(9, 5), arrowcolor=GOLD_LIGHT)
    style.map('TMenubutton', background=[('active', HOVER_BG)], foreground=[('disabled', DISABLED)],
              arrowcolor=[('disabled', DISABLED)])
    for input_style in ('Input.TButton', 'Input.Primary.TButton', 'Input.TMenubutton'):
        style.configure(input_style, padding=(5, 2))
    style.layout('RemoveReference.TButton', [
        ('Button.border', {'sticky': 'nswe', 'children': [
            ('Button.focus', {'sticky': 'nswe', 'children': [
                ('Button.label', {'sticky': 'nswe'}),
            ]}),
        ]}),
    ])
    style.configure('RemoveReference.TButton', anchor='center', width=0, relief='flat',
                    background=SECONDARY_BG, bordercolor=SECONDARY_BG,
                    lightcolor=SECONDARY_BG, darkcolor=SECONDARY_BG)
    icon_border = [('disabled', SECONDARY_BG), ('active', BORDER), ('!active', SECONDARY_BG)]
    style.map('RemoveReference.TButton', bordercolor=icon_border, relief=[('!disabled', 'flat')],
              lightcolor=icon_border, darkcolor=icon_border)
    flat_menu_layout = [
        ('Menubutton.border', {'sticky': 'nswe', 'children': [
            ('Menubutton.padding', {'sticky': 'nswe', 'children': [
                ('Menubutton.label', {'sticky': 'nswe'}),
            ]}),
        ]}),
    ]
    style.layout('Prompt.TMenubutton', flat_menu_layout)
    style.layout('Reference.TMenubutton', flat_menu_layout)
    style.configure('Reference.TMenubutton', borderwidth=1, relief='raised', padding=(5, 2))
    style.configure('Prompt.TMenubutton', borderwidth=1, relief='raised', padding=(9, 2))
    style.map('Prompt.TMenubutton', bordercolor=[('active', GOLD), ('focus', GOLD_LIGHT)],
              darkcolor=[('active', GOLD), ('focus', GOLD_LIGHT)],
              lightcolor=[('active', GOLD), ('focus', GOLD_LIGHT)])
    style.configure('TEntry', fieldbackground=SECONDARY_BG, foreground=TEXT, insertcolor=TEXT)
    style.map('TEntry', fieldbackground=[('disabled', SECONDARY_BG), ('readonly', SECONDARY_BG)],
              foreground=[('disabled', DISABLED), ('readonly', TEXT)])
    # Clam leaves the four corner pixels open and uses the widget background there.
    style.configure('Path.TEntry', background=PANEL_BG)
    style.map('Path.TEntry', background=[('readonly', PANEL_BG), ('disabled', PANEL_BG)])
    style.configure('TSpinbox', fieldbackground=SECONDARY_BG, background=HOVER_BG,
                    foreground=TEXT, insertcolor=TEXT, arrowcolor=GOLD_LIGHT)
    style.map('TSpinbox', fieldbackground=[('disabled', SECONDARY_BG)],
              foreground=[('disabled', DISABLED)], arrowcolor=[('disabled', DISABLED)])
    style.configure('TCombobox', fieldbackground=PANEL_BG, background=HOVER_BG, arrowcolor=GOLD_LIGHT)
    style.map('TCombobox', fieldbackground=[('disabled', PANEL_BG), ('readonly', PANEL_BG)],
              foreground=[('disabled', DISABLED), ('readonly', TEXT)], arrowcolor=[('disabled', DISABLED)],
              background=[('disabled', HOVER_BG), ('active', BORDER)],
              selectbackground=[('disabled', PANEL_BG), ('readonly', PANEL_BG)],
              selectforeground=[('disabled', DISABLED), ('readonly', TEXT)])
    field_border = [('disabled', BORDER), ('focus', GOLD_LIGHT), ('!focus', BORDER)]
    for field_style in ('TEntry', 'TSpinbox', 'TCombobox'):
        style.map(field_style, bordercolor=field_border, lightcolor=field_border, darkcolor=field_border)
    window.option_add('*TCombobox*Listbox.background', SECONDARY_BG)
    window.option_add('*TCombobox*Listbox.foreground', TEXT)
    window.option_add('*TCombobox*Listbox.selectBackground', HOVER_BG)
    window.option_add('*TCombobox*Listbox.selectForeground', TEXT)
