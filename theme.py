"""Stereo-Tools colors and TransCora widget states for the photo app."""
from tkinter import ttk

import customtkinter as ctk

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
PREVIEW_BG = '#000000'


def checkbox(parent, text, variable, command=None):
    return ctk.CTkCheckBox(parent, text=text, variable=variable, command=command,
                           bg_color=PANEL_BG, fg_color=GOLD, hover_color=GOLD_LIGHT,
                           border_color=BORDER, checkmark_color=TEXT, text_color=TEXT,
                           text_color_disabled=DISABLED, corner_radius=4, font=('Segoe UI', 13))


def set_control_state(widget, state):
    if isinstance(widget, ctk.CTkCheckBox):
        widget.configure(state=state, fg_color=DISABLED if state == 'disabled' else GOLD,
                         hover_color=DISABLED if state == 'disabled' else GOLD_LIGHT)
    else:
        widget.configure(state=state)


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
    style.configure('Method.TMenubutton', background=PANEL_BG, padding=(6, 2), anchor='w')
    style.layout('Prompt.TMenubutton', [
        ('Menubutton.border', {'sticky': 'nswe', 'children': [
            ('Menubutton.padding', {'sticky': 'nswe', 'children': [
                ('Menubutton.label', {'sticky': 'nswe'}),
            ]}),
        ]}),
    ])
    style.configure('Prompt.TMenubutton', borderwidth=1, relief='raised')
    style.map('Prompt.TMenubutton', bordercolor=[('active', GOLD), ('focus', GOLD_LIGHT)],
              darkcolor=[('active', GOLD), ('focus', GOLD_LIGHT)],
              lightcolor=[('active', GOLD), ('focus', GOLD_LIGHT)])
    style.configure('TEntry', fieldbackground=SECONDARY_BG, foreground=TEXT, insertcolor=TEXT)
    style.map('TEntry', fieldbackground=[('disabled', SECONDARY_BG), ('readonly', SECONDARY_BG)],
              foreground=[('disabled', DISABLED), ('readonly', TEXT)])
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
    window.option_add('*TCombobox*Listbox.background', SECONDARY_BG)
    window.option_add('*TCombobox*Listbox.foreground', TEXT)
    window.option_add('*TCombobox*Listbox.selectBackground', HOVER_BG)
    window.option_add('*TCombobox*Listbox.selectForeground', TEXT)
