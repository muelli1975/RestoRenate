"""Portable desktop front end for RestoRenate."""
from __future__ import annotations

import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from queue import Empty, Queue
import secrets
import sys
from threading import Event, Thread
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import traceback

from PIL import Image, ImageTk

from portable_paths import ROOT

from language import LANGUAGE_LABELS, configure_language, translate
from comparison import Comparison
from crop import CropRegion
from crop_dialog import edit_crops
from export_metadata import APP_NAME, APP_VERSION, MAX_SEED, parse_seed, seed_from_metadata
from imaging import EXTENSIONS, FORMATS, collect, exiftool_executable, open_photo, photo_size
from local_backend import Backend, BackendStartError
from portable_setup import (AMD, COMPUTE_DEVICES, CPU, DEFAULT_COMPUTE, GPU_HINTS, LINUX, NVIDIA, ComputeUnavailable, Setup,
                            SetupCancelled, compute_label)
from nunchaku_setup import NUNCHAKU_CAPABILITIES, NUNCHAKU_GPU_REQUIRED
from preload_models import choose_preloads, format_download_size, preload_label
from methods import (COLORIZATION_METHODS, CPU_METHODS, DEFAULT_METHOD, LANCZOS, LICENSES,
                     METHODS, MICROSOFT, NATIVE_METHODS, NO_PROMPT, QWEN2509_NUNCHAKU,
                     TWO_IMAGE_METHODS, UPSCALE_LICENSES, UPSCALERS, UPSCALING,
                     available_methods, resolve_upscaler, uses_comfy)
from sizes import (CUSTOM_SIZES, MAX_SIDE, NO_RESCALE, SIZE_CHOICES, ULTRA_HD, method_size,
                   needs_enlargement, output_size, restoration_size, size_choices)
from photo_colors import Colorizer
from progress_track import ProgressTrack
from prompt_menu import PromptMenu
from theme import (APP_BG as BG, PANEL_BG as PANEL, SECONDARY_BG, HOVER_BG, BORDER,
                   TEXT as INK, MUTED, DISABLED, GOLD, GOLD_LIGHT, apply_theme, checkbox,
                   set_control_state, style_method_scrollbar)
from restoration import Client, restore, select_models
from technical_logs import TechnicalLog, prepare_technical_logs
from titlebar import install_tk_titlebars

DEFAULT_PROMPT_NAME = 'Allround'
# The two original workflows share this wording.
COLORIZE_START = 'restore and colorize this photo, remove the stains, dust spots, noise, scratches and stripes from the image, '
REPAIR_SECTIONS = 'ripped or torn sections, turning it into a high quality photograph'
EXAMPLE_PROMPTS = {
    'Restaurieren und kolorieren 1': (
        f'{COLORIZE_START}fill in any gaps, {REPAIR_SECTIONS}, reversal film photography, '
        'remove stains and crease marks, repair gaps and fold or bends'
    ),
    'Restaurieren und kolorieren 2': f'{COLORIZE_START}fill in any {REPAIR_SECTIONS}',
}
PRESETS = {
    DEFAULT_PROMPT_NAME: (
        'Restore this photo. Improve clarity and bring back natural colors where needed. '
        'Preserve faces and natural texture.'
    ),
    **EXAMPLE_PROMPTS,
    'Restaurieren und kolorieren · Kurz': 'Colorize and restore this image.',
    'FLUX.2 [klein] 4B · Reparieren und kolorieren': (
        'repair and colorize the image. fix the cracks and fill in the missing areas.'
    ),
    'Porträt im Abendlicht': (
        'A photorealistic golden-hour portrait of the subject, shot on an 85mm f/1.4 lens, '
        'soft rim lighting from camera-left, shallow depth of field with creamy bokeh, warm amber tones, '
        'natural ultra-detailed skin texture with visible pores, editorial magazine style, 4k, aspect ratio 4:5.'
    ),
    'Schwarzweiß-Studioporträt': (
        'A classic black-and-white studio portrait of the subject, shot on a 105mm portrait lens, '
        'soft directional light from a large window, deep but detailed shadows, a plain charcoal-gray backdrop, '
        'fine 35mm film grain, crisp eyes, and natural skin texture. '
        'Preserve the subject’s facial features, expression, and pose.'
    ),
    'Analoger Farbfilm': (
        'Give this photo the look of a 1970s color negative scan. Use muted reds and greens, '
        'gently warm highlights, soft contrast, and fine visible film grain. '
        'Keep the original lighting direction, faces, and framing. Preserve detail in bright areas and deep shadows.'
    ),
}
MAX_VARIANTS = 100
VARIANT_COUNTS = {str(count): count for count in range(1, MAX_VARIANTS + 1)}
BUILTIN_PROCESSING_PRESETS = {
    'Standard': {
        'method': DEFAULT_METHOD, 'preset': DEFAULT_PROMPT_NAME, 'prompt': PRESETS[DEFAULT_PROMPT_NAME], 'variants': 1,
        'size': ULTRA_HD, 'upscaler': resolve_upscaler(DEFAULT_METHOD),
    },
}
SETTINGS = ROOT / 'settings' / 'settings.json'
JOBS_LOG = ROOT / 'logs' / 'jobs.jsonl'
FILE_TYPES = [('Bilddateien', ' '.join('*' + ext for ext in sorted(EXTENSIONS))), ('Alle Dateien', '*')]
ROTATION_CHOICES = (('90° links', -1), ('90° rechts', 1), ('180°', 2), ('Drehung zurücksetzen', None))
REFERENCE_PREVIEW_SIZE = (144, 82)


def read_settings():
    try:
        loaded = json.loads(SETTINGS.read_text(encoding='utf-8'))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        return {}


def nvidia_driver_available():
    try:
        driver = ctypes.CDLL('libcuda.so.1') if LINUX else ctypes.WinDLL('nvcuda.dll', winmode=0x00000800)
        count = ctypes.c_int()
        return (driver.cuInit(0) == 0 and
                driver.cuDeviceGetCount(ctypes.byref(count)) == 0 and count.value > 0)
    except (OSError, AttributeError):
        return False


def nvidia_nunchaku_available():
    if not nvidia_driver_available():
        return False
    try:
        driver = ctypes.WinDLL('nvcuda.dll', winmode=0x00000800)
        device = ctypes.c_int()
        major, minor = ctypes.c_int(), ctypes.c_int()
        # CUDA driver API attributes 75 and 76 are compute capability major and minor.
        return (driver.cuDeviceGet(ctypes.byref(device), 0) == 0
                and driver.cuDeviceGetAttribute(ctypes.byref(major), 75, device) == 0
                and driver.cuDeviceGetAttribute(ctypes.byref(minor), 76, device) == 0
                and (major.value, minor.value) in NUNCHAKU_CAPABILITIES)
    except (OSError, AttributeError):
        return False


def read_processing_presets(saved):
    if not isinstance(saved, dict):
        return {}
    return {name: preset for name, preset in saved.items()
            if isinstance(name, str) and name.strip() and name not in BUILTIN_PROCESSING_PRESETS
            and isinstance(preset, dict) and isinstance(preset.get('method'), str)
            and preset['method'] in METHODS}


class LocalizedText(tk.StringVar):
    def __init__(self):
        super().__init__()
        self.messages = ()

    def set(self, value):
        self.messages = ()
        super().set(value)

    def set_message(self, message, *values):
        self.set_messages((message, *values))

    def set_messages(self, *messages):
        self.messages = messages
        self.refresh()

    def refresh(self):
        if self.messages:
            super().set(''.join(translate(*message) for message in self.messages))


class Application:
    def __init__(self, window):
        self.window = window
        self.config = read_settings()
        self.language = configure_language(self.config.get('language'))
        self.window.title(f'{APP_NAME} - {APP_VERSION}')
        self.window.geometry('1130x750')
        self.window.minsize(950, 720)
        self.window.configure(bg=BG)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        install_tk_titlebars(window)
        saved_compute = self.config.get('compute')
        selected_compute = saved_compute if isinstance(saved_compute, str) and saved_compute in COMPUTE_DEVICES else DEFAULT_COMPUTE
        self.startup_compute = self.active_compute = selected_compute
        self.verified_compute = None
        self.compute = tk.StringVar(value=selected_compute)
        previous_method = self.config.get('method')
        self.method_ids = self.available_method_ids()
        self.current_method = previous_method if previous_method in self.method_ids.values() else DEFAULT_METHOD
        self.method = tk.StringVar(value=translate(METHODS[self.current_method]))
        self.scratches = tk.BooleanVar(value=bool(self.config.get('scratches', True)))
        self.faces = tk.BooleanVar(value=bool(self.config.get('faces', False)))
        self.variant_count = VARIANT_COUNTS.get(str(self.config.get('variants')), 1)
        self.variants = tk.StringVar(value=str(self.variant_count))
        self.custom = self.read_custom_presets(self.config.get('presets'))
        draft = self.config.get('prompt_draft')
        self.draft = draft if isinstance(draft, dict) and isinstance(draft.get('prompt'), str) else {}
        self.processing_presets = read_processing_presets(self.config.get('processing_presets'))
        self.seed = parse_seed(self.config.get('seed'))
        self.seed_value = tk.StringVar(value='')
        self.events = Queue()
        self.cancelled, self.stop_after = Event(), Event()
        self.backend = Backend(ROOT, compute=self.active_compute)
        self.action = None
        self.closing = False
        self.sources = []
        self.crops = {}
        self.rotations = {}
        self.second_image = None
        self.second_rotation = 0
        self.second_thumbnail = None
        self.results = []
        self.index = -1
        self.status = LocalizedText()
        self.status.set_message('Bereit')
        self.setup_status = tk.StringVar()
        self.input_value = tk.StringVar()
        self.output = tk.StringVar(value=str(self.config.get('output') or ''))
        fmt = self.config.get('format')
        if not isinstance(fmt, str) or fmt not in FORMATS:
            fmt = 'PNG'
        self.output_format = tk.StringVar(value=fmt)
        saved_scales = self.config.get('scaling')
        self.scaling = {}
        if isinstance(saved_scales, dict):
            self.scaling = {key: saved_scales[key] for key in ('restoration', 'colorization', UPSCALING)
                            if isinstance(saved_scales.get(key), dict)}
        self.size_ids = {translate(choice): choice for choice in SIZE_CHOICES}
        self.size, self.side_pixels, self.upscaler = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.inactive_upscaler = tk.StringVar(value=translate('Aus'))
        self.dimensions = tk.StringVar()
        self.preview_source = None
        self.preview_size = None
        self.load_scaling()
        self.preset = tk.StringVar(value=translate(DEFAULT_PROMPT_NAME))
        self.elapsed = LocalizedText()
        self.device = LocalizedText()
        self.image_started = None
        self.caption = LocalizedText()
        self.caption.set_message('Wähle ein Bild oder einen Ordner.')
        self.result_position = tk.StringVar(value='0/0')
        self.controls = []
        self.labels = {}
        self.build()
        self.navigation()
        self.variants.trace_add('write', self.variant_changed)
        self.size.trace_add('write', self.update_dimensions)
        self.side_pixels.trace_add('write', self.update_dimensions)
        self.update_size_controls()
        self.load_method_prompt()
        self.prompt.bind('<<Modified>>', self.prompt_changed)
        self.window.bind('<Button-1>', self.leave_editor_on_click, add='+')
        self.window.bind('<Escape>', self.compare.leave_zoom)
        self.window.bind('<Control-Key-0>', self.compare.fit)
        self.window.bind('<Control-Key-1>', lambda event: self.compare.full_size())
        self.window.bind('<Prior>', lambda event: self.browse_results(event, -1))
        self.window.bind('<Next>', lambda event: self.browse_results(event, 1))
        self.check_ready()
        self.window.after(75, self.poll)

    def labelled(self, widget, parent, text, **options):
        control = widget(parent, text=translate(text), **options)
        self.labels[control] = text
        return control

    def build(self):
        apply_theme(self.window)
        header = tk.Frame(self.window, bg=BG, padx=18, pady=10)
        header.pack(fill='x')
        tk.Label(header, text=APP_NAME, bg=BG, fg=GOLD_LIGHT, font=('Segoe UI', 18, 'bold')).pack(side='left')
        self.labelled(tk.Label, header, 'Bildrestaurierung und -bearbeitung', bg=BG, fg=MUTED, padx=12).pack(
            side='left', pady=(6, 0),
        )
        menu_colors = dict(tearoff=False, background=SECONDARY_BG, foreground=INK,
                           activebackground=HOVER_BG, activeforeground=INK, disabledforeground=DISABLED)
        self.language_button = ttk.Menubutton(header, text=LANGUAGE_LABELS[self.language])
        languages = tk.Menu(self.language_button, **menu_colors)
        for code, label in LANGUAGE_LABELS.items():
            languages.add_command(label=label, command=lambda code=code: self.change_language(code))
        self.language_button.configure(menu=languages)
        self.language_button.pack(side='right', padx=(0, 4))
        self.processing_button = ttk.Menubutton(header, text='Presets')
        self.processing_menu = tk.Menu(self.processing_button, **menu_colors)
        self.processing_delete_menu = tk.Menu(self.processing_menu, **menu_colors)
        self.processing_button.configure(menu=self.processing_menu)
        self.processing_button.pack(side='right', padx=(0, 4))
        self.compute_button = ttk.Menubutton(header)
        self.update_compute_label()
        compute_menu = self.compute_menu = tk.Menu(self.compute_button, **menu_colors)
        for compute in COMPUTE_DEVICES:
            compute_menu.add_radiobutton(label=compute_label(compute), variable=self.compute, value=compute,
                                         command=self.choose_compute)
        self.compute_button.configure(menu=compute_menu)
        self.compute_button.pack(side='right', padx=(0, 4))
        tk.Label(header, textvariable=self.setup_status, bg=BG, fg=MUTED, padx=10).pack(side='right')
        self.controls.extend((self.language_button, self.processing_button, self.compute_button))
        self.refresh_processing_menu()

        body = tk.Frame(self.window, bg=BG, padx=14)
        body.pack(fill='both', expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=PANEL, padx=12, pady=10, width=366)
        left.grid(row=0, column=0, sticky='ns', padx=(0, 10))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(11, weight=1)

        def label(text, row, pad=(6, 2)):
            self.labelled(tk.Label, left, text, bg=PANEL, fg=INK, anchor='w', font=('Segoe UI', 10, 'bold')).grid(
                row=row, column=0, sticky='w', pady=pad,
            )

        def button(parent, title, command, **options):
            options.setdefault('style', 'Input.TButton')
            control = self.labelled(ttk.Button, parent, title, command=command, **options)
            self.controls.append(control)
            return control

        label('Eingabe', 0, (0, 2))
        entry = ttk.Entry(left, textvariable=self.input_value, state='readonly', style='Path.TEntry')
        entry.grid(row=1, column=0, sticky='ew')
        input_actions = tk.Frame(left, bg=PANEL)
        input_actions.grid(row=2, column=0, sticky='ew', pady=(4, 0))
        paths = tk.Frame(input_actions, bg=PANEL)
        paths.pack(fill='x')
        button(paths, 'Bild …', self.choose_photo, width=-1).pack(side='left')
        button(paths, 'Ordner …', self.choose_folder, width=-1).pack(side='left', padx=4)
        self.crop_button = button(paths, 'Beschnitt …', self.edit_crop, state='disabled', width=-1)
        self.crop_button.pack(side='left')
        self.rotate_button = self.labelled(ttk.Menubutton, paths, 'Drehen', width=-1, style='Input.TMenubutton')
        self.rotate_button.pack(side='left', padx=(4, 0))
        rotations = self.rotation_menu = tk.Menu(self.rotate_button, **menu_colors)
        for caption, turn in ROTATION_CHOICES:
            rotations.add_command(label=translate(caption), command=lambda turn=turn: self.rotate_source(turn))
        self.rotate_button.configure(menu=rotations)
        self.build_second_image(input_actions, menu_colors)

        label('Ausgabeordner', 3)
        destination = tk.Frame(left, bg=PANEL)
        destination.grid(row=4, column=0, sticky='ew')
        out_entry = ttk.Entry(destination, textvariable=self.output, style='Path.TEntry')
        out_entry.pack(side='left', fill='x', expand=True, padx=(0, 4))
        self.controls.append(out_entry)
        button(destination, 'Auswählen …', self.choose_output).pack(side='right')
        self.format_widget = ttk.Combobox(left, textvariable=self.output_format, values=list(FORMATS),
                                          state='readonly', height=4)
        self.format_widget.grid(row=5, column=0, sticky='ew', pady=(4, 0))
        scaling = tk.Frame(left, bg=PANEL)
        scaling.grid(row=6, column=0, sticky='ew', pady=(5, 0))
        scaling.columnconfigure(0, weight=9, uniform='scaling')
        scaling.columnconfigure(1, weight=10, uniform='scaling')
        tk.Label(scaling, text='Upscaler', bg=PANEL, fg=INK, anchor='w').grid(
            row=0, column=0, sticky='ew', padx=(0, 5))
        self.labelled(tk.Label, scaling, 'Zielgröße', bg=PANEL, fg=INK, anchor='w').grid(row=0, column=1, sticky='ew')
        self.upscale_options = ttk.Combobox(scaling, textvariable=self.upscaler, values=UPSCALERS,
                                            state='readonly', width=1)
        self.upscale_options.grid(row=1, column=0, sticky='ew', padx=(0, 5))
        size_row = tk.Frame(scaling, bg=PANEL)
        size_row.grid(row=1, column=1, sticky='ew')
        self.size_widget = ttk.Combobox(size_row, textvariable=self.size, state='readonly', width=1)
        self.size_widget.pack(side='left', fill='x', expand=True)
        self.side_entry = ttk.Entry(size_row, textvariable=self.side_pixels, width=6)
        self.upscale_options.bind('<<ComboboxSelected>>', self.scaling_changed)
        self.size_widget.bind('<<ComboboxSelected>>', self.scaling_changed)
        self.side_entry.bind('<FocusOut>', self.scaling_changed)
        self.side_entry.bind('<Return>', self.scaling_changed)
        self.controls.append(self.side_entry)
        tk.Label(left, textvariable=self.dimensions, bg=PANEL, fg=MUTED, anchor='w',
                 justify='left', wraplength=336).grid(row=7, column=0, sticky='ew', pady=(2, 0))
        label('Verfahren', 8)
        button(left, 'Modelle vorab laden …', self.preload_clicked).grid(row=8, column=0, sticky='e', pady=(6, 2))
        self.method_widget = ttk.Combobox(left, textvariable=self.method, values=list(self.method_ids), state='readonly')
        self.method_widget.grid(row=9, column=0, sticky='ew')
        style_method_scrollbar(self.method_widget)
        self.method_widget.bind('<<ComboboxSelected>>', self.choose_method)
        self.prompt_heading = tk.StringVar(value='Prompt')
        self.prompt_heading_widget = tk.Label(left, textvariable=self.prompt_heading, bg=PANEL, fg=INK, anchor='w',
                                              font=('Segoe UI', 10, 'bold'))
        self.prompt_heading_widget.grid(row=10, column=0, sticky='ew', pady=(6, 2))
        prompt_frame = tk.Frame(left, bg=PANEL)
        prompt_frame.grid(row=11, column=0, sticky='nsew')
        prompt_frame.grid_columnconfigure(0, weight=1)
        prompt_frame.grid_rowconfigure(1, weight=1)
        self.preset_widget = ttk.Combobox(prompt_frame, textvariable=self.preset, state='readonly',
                                          values=self.preset_names())
        self.preset_widget.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self.preset_widget.bind('<<ComboboxSelected>>', self.choose_preset)
        self.prompt = tk.Text(prompt_frame, height=3, wrap='word', bg=SECONDARY_BG, fg=INK, insertbackground=INK,
                              selectbackground=HOVER_BG, selectforeground=INK, relief='flat', highlightthickness=1,
                              highlightbackground=BORDER, highlightcolor=GOLD_LIGHT,
                              padx=7, pady=6, font=('Segoe UI', 10), undo=True)
        self.prompt.grid(row=1, column=0, sticky='nsew')
        self.prompt_actions = tk.Frame(left, bg=PANEL)
        self.prompt_actions.grid(row=12, column=0, sticky='ew', pady=(5, 0))
        self.snippets_button = self.labelled(
            ttk.Menubutton, self.prompt_actions, 'Satzbausteine', direction='above', style='Prompt.TMenubutton',
        )
        self.snippets_button.pack(side='left', padx=(0, 6))
        self.prompt_menu = PromptMenu(self.prompt, self.snippets_button, menu_colors, self.language)
        self.save_prompt_button = self.labelled(
            ttk.Button, self.prompt_actions, 'Prompt speichern …', command=self.save_preset, style='Input.TButton',
        )
        self.save_prompt_button.pack(side='left')
        self.microsoft_options = tk.Frame(prompt_frame, bg=PANEL)
        self.microsoft_options.grid(row=0, column=0, rowspan=2, sticky='new')
        scratches = self.labelled(checkbox, self.microsoft_options, 'Kratzer reparieren', variable=self.scratches)
        scratches.pack(anchor='w', pady=(0, 4))
        faces = self.labelled(checkbox, self.microsoft_options, 'Gesichter verbessern',
                              variable=self.faces, command=self.check_ready)
        faces.pack(anchor='w')
        self.controls.extend((scratches, faces))
        self.labelled(tk.Label, self.microsoft_options, 'Klassische Restaurierung ohne Prompt', bg=PANEL,
                 fg=MUTED, anchor='w').pack(fill='x', pady=(5, 0))
        self.microsoft_options.grid_remove()
        self.variant_row = tk.Frame(left, bg=PANEL)
        self.variant_row.grid(row=13, column=0, sticky='ew', pady=(5, 0))
        self.labelled(tk.Label, self.variant_row, 'Varianten pro Bild', bg=PANEL, fg=INK).pack(side='left')
        validate_variants = self.window.register(lambda value: not value or value in VARIANT_COUNTS)
        self.variant_widget = ttk.Spinbox(
            self.variant_row, from_=1, to=MAX_VARIANTS, textvariable=self.variants, width=4,
            validate='key', validatecommand=(validate_variants, '%P'),
        )
        self.variant_widget.pack(side='left', padx=(8, 0))
        self.variant_widget.bind('<FocusOut>', self.finish_variant_edit)
        self.variant_widget.bind('<Return>', self.finish_variant_edit)
        tk.Label(self.variant_row, text=f'1–{MAX_VARIANTS}', bg=PANEL, fg=MUTED).pack(side='left', padx=(6, 0))
        self.controls.append(self.variant_widget)
        self.seed_row = tk.Frame(left, bg=PANEL)
        self.seed_row.grid(row=14, column=0, sticky='ew', pady=(4, 0))
        self.labelled(tk.Label, self.seed_row, 'Seed (leer = Zufall)', bg=PANEL, fg=INK).pack(side='left')
        self.seed_entry = ttk.Entry(self.seed_row, textvariable=self.seed_value, width=21)
        self.seed_entry.pack(side='left', fill='x', expand=True, padx=(8, 0))
        self.seed_actions = tk.Frame(left, bg=PANEL)
        self.seed_actions.grid(row=15, column=0, sticky='ew', pady=(4, 0))
        self.last_seed_button = self.labelled(ttk.Button, self.seed_actions, 'Letzten übernehmen',
                                             command=lambda: self.seed_value.set(str(self.seed)), style='Input.TButton')
        self.last_seed_button.pack(side='left')
        self.png_seed_button = self.labelled(ttk.Button, self.seed_actions, 'Aus PNG übernehmen …',
                                            command=self.import_seed, style='Input.TButton')
        self.png_seed_button.pack(side='left', padx=(6, 0))
        buttons = tk.Frame(left, bg=PANEL)
        buttons.grid(row=16, column=0, sticky='ew', pady=(5, 0))
        self.start_button = ttk.Button(buttons, text='Start', command=self.start_clicked, style='Input.Primary.TButton')
        self.start_button.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.stop_button = ttk.Button(buttons, text=self.stop_label(), command=self.stop, state='disabled',
                                      style='Input.TButton')
        self.stop_button.pack(side='right')
        self.update_seed()

        right = tk.Frame(body, bg=PANEL, padx=9, pady=8)
        right.grid(row=0, column=1, sticky='nsew')
        top = tk.Frame(right, bg=PANEL)
        top.pack(fill='x', pady=(0, 6))
        self.labelled(tk.Label, top, 'Vorher', fg=MUTED, bg=PANEL).pack(side='left')
        self.labelled(tk.Label, top, 'Nachher', fg=INK, bg=PANEL).pack(side='right')
        self.compare = Comparison(right)
        self.compare.pack(fill='both', expand=True)
        navigation = tk.Frame(right, bg=PANEL)
        navigation.pack(fill='x', pady=(6, 0))
        self.labelled(ttk.Button, navigation, 'Ansicht einpassen', command=self.compare.fit).pack(side='right')
        self.labelled(ttk.Button, navigation, '100 %', command=self.compare.full_size,
                      width=-1, style='Input.TButton').pack(side='right', padx=(0, 4))
        self.labelled(tk.Label, navigation, 'Ergebnisse', fg=INK, bg=PANEL).pack(side='left', padx=(0, 7))
        self.prev_button = self.labelled(ttk.Button, navigation, 'Zurück', command=lambda: self.move(-1),
                                        state='disabled', width=-1, style='Input.TButton')
        self.prev_button.pack(side='left')
        self.next_button = self.labelled(ttk.Button, navigation, 'Weiter', command=lambda: self.move(1),
                                        state='disabled', width=-1, style='Input.TButton')
        self.next_button.pack(side='left', padx=(4, 8))
        tk.Label(navigation, textvariable=self.result_position, fg=MUTED, bg=PANEL).pack(side='left')
        self.labelled(tk.Label, navigation, 'Mausrad zum Zoomen', fg=MUTED, bg=PANEL).pack(side='right', padx=(0, 5))
        result_info = tk.Frame(right, bg=PANEL)
        result_info.pack(fill='x', pady=(5, 0))
        self.clear_history_button = self.labelled(
            ttk.Button, result_info, 'Verlauf löschen …', command=self.clear_history, state='disabled',
        )
        self.clear_history_button.pack(side='right', padx=(8, 0))
        self.reuse_result_button = self.labelled(ttk.Button, result_info, 'Ergebnis weiterbearbeiten',
                                              command=self.reuse_result, state='disabled')
        self.reuse_result_button.pack(side='right', padx=(8, 0))
        tk.Label(result_info, textvariable=self.caption, fg=MUTED, bg=PANEL, anchor='w').pack(side='left', fill='x', expand=True)

        footer = tk.Frame(self.window, bg=PANEL, padx=12, pady=7)
        footer.pack(fill='x', padx=14, pady=(9, 8))
        job_info = tk.Frame(footer, bg=PANEL)
        job_info.pack(fill='x')
        tk.Label(job_info, textvariable=self.elapsed, fg=MUTED, bg=PANEL, anchor='e').pack(side='right')
        tk.Label(job_info, textvariable=self.device, fg=MUTED, bg=PANEL).pack(side='right', padx=(10, 13))
        tk.Label(job_info, textvariable=self.status, fg=INK, bg=PANEL, anchor='w').pack(
            side='left', fill='x', expand=True,
        )
        self.progress_bar = ProgressTrack(footer, PANEL, GOLD, BORDER)
        self.progress_bar.pack(fill='x', pady=(4, 0))

    def build_second_image(self, parent, menu_colors):
        width, height = REFERENCE_PREVIEW_SIZE
        self.second_row = tk.Frame(parent, bg=SECONDARY_BG, height=height + 8)
        self.second_row.pack_propagate(False)
        self.second_preview = tk.Canvas(self.second_row, width=width, height=height, bg=BG,
                                        highlightthickness=1, highlightbackground=BORDER)
        self.second_preview.pack(side='left', padx=6)
        self.second_preview_item = self.second_preview.create_image(width / 2 + 1, height / 2 + 1)
        details = tk.Frame(self.second_row, bg=SECONDARY_BG)
        details.pack(side='left', fill='both', expand=True, pady=4, padx=(0, 6))
        self.labelled(tk.Label, details, 'Zweites Bild', bg=SECONDARY_BG, fg=INK, anchor='w').pack(fill='x')
        self.second_name = tk.Label(details, bg=SECONDARY_BG, fg=MUTED, anchor='w', width=1)
        self.second_name.pack(fill='x', expand=True)
        actions = tk.Frame(details, bg=SECONDARY_BG)
        actions.pack(fill='x')
        actions.columnconfigure(2, weight=1)
        self.second_button = ttk.Button(actions, command=self.choose_second_image, width=-1, style='Input.TButton')
        self.second_button.grid(row=0, column=0, sticky='w')
        self.second_rotate_button = self.labelled(ttk.Menubutton, actions, 'Drehen ▾', width=-1,
                                                  style='Reference.TMenubutton')
        self.second_rotate_button.grid(row=0, column=1, padx=(4, 0), sticky='w')
        self.second_rotation_menu = tk.Menu(self.second_rotate_button, **menu_colors)
        for label, turns in ROTATION_CHOICES:
            self.second_rotation_menu.add_command(label=translate(label),
                                                  command=lambda turns=turns: self.rotate_second_image(turns))
        self.second_rotate_button.configure(menu=self.second_rotation_menu)
        self.remove_second_button = ttk.Button(actions, text='×', command=self.clear_second_image,
                                               width=-1, style='RemoveReference.TButton')
        self.remove_second_button.grid(row=0, column=3, padx=(4, 0), sticky='e')

    def variant_changed(self, *_):
        self.variant_count = VARIANT_COUNTS.get(self.variants.get(), self.variant_count)
        self.update_seed()

    def finish_variant_edit(self, event=None):
        if not self.variants.get():
            self.variants.set(str(self.variant_count))

    def update_seed(self):
        self.seed_entry.configure(state='normal' if self.action is None else 'disabled')
        self.png_seed_button.configure(state='normal' if self.action is None else 'disabled')
        self.last_seed_button.configure(state='normal' if self.seed is not None and self.action is None else 'disabled')
        if self.action is None:
            self.stop_button.configure(text=self.stop_label())

    def import_seed(self):
        title = translate('Aus PNG übernehmen …')
        path = filedialog.askopenfilename(parent=self.window, title=title, filetypes=[('PNG', '*.png')])
        if not path:
            return
        try:
            with Image.open(path) as image:
                if image.format != 'PNG':
                    raise ValueError(translate('Bitte eine PNG-Datei wählen.'))
                seed = seed_from_metadata(image.info)
                if seed is None:
                    raise ValueError(translate('In dieser PNG-Datei wurde kein eindeutiger Seed gefunden.'))
        except (OSError, ValueError, SyntaxError) as exc:
            messagebox.showinfo(title, str(exc), parent=self.window)
        else:
            self.seed_value.set(str(seed))

    def fixed_seed(self):
        value = self.seed_value.get().strip()
        seed = parse_seed(value)
        if value and seed is None:
            raise ValueError(translate('Der Seed muss eine ganze Zahl von 0 bis {0} sein.', MAX_SEED))
        return seed

    def scaling_changed(self, event=None):
        if not self.action:
            self.update_size_controls()
            self.check_ready()
            self.save_settings()

    def effective_upscaler(self, *, all_sources=False):
        method = self.current_method
        if self.size_choice() == NO_RESCALE:
            return LANCZOS
        upscaler = resolve_upscaler(method, self.upscaler.get())
        if upscaler == LANCZOS or not self.sources:
            return upscaler
        if not all_sources and len(self.sources) > 1:
            return upscaler
        try:
            size_choice = self.selected_size()
        except ValueError:
            return upscaler
        for source in self.sources:
            try:
                original = self.source_size(source)
                target = output_size(original, *size_choice, method=method)
            except (OSError, ValueError, SyntaxError):
                continue
            if needs_enlargement(restoration_size(original, method), target):
                return upscaler
        return LANCZOS

    def check_ready(self):
        upscaler = self.effective_upscaler()
        setup = Setup(ROOT, method=self.current_method, faces=self.faces.get(),
                      upscaler=upscaler, compute=self.active_compute)
        self.setup_status_key = setup.setup_status()
        self.ready = self.setup_status_key == 'Verfahren bereit'
        self.update_setup_status()

    def update_setup_status(self):
        status = translate(self.setup_status_key)
        if self.active_compute == CPU and self.current_method not in NO_PROMPT:
            status += ' · ' + translate('Hoher CPU-Aufwand')
        self.setup_status.set(status)

    def choose_compute(self):
        selection = self.compute.get()
        self.save_settings()
        self.update_compute_label()
        if selection != self.startup_compute:
            messagebox.showinfo(translate('Berechnung'),
                                translate(
                                    '{0} wird nach einem Neustart von {1} verwendet.',
                                    compute_label(selection), APP_NAME,
                                ),
                                parent=self.window)

    def update_compute_label(self):
        pending = self.compute.get() != self.startup_compute
        label = compute_label(self.active_compute)
        self.compute_button.configure(text=translate('Berechnung · {0}', label) + (' ↻' if pending else ''))

    def supports_nunchaku(self):
        return not LINUX and self.active_compute == NVIDIA and nvidia_nunchaku_available()

    def available_method_ids(self):
        methods = available_methods(self.supports_nunchaku(), cpu=self.active_compute == CPU)
        return {translate(METHODS[method]): method for method in methods}

    def offer_cpu_fallback(self, reason):
        self.status.set(reason.splitlines()[0])
        if self.current_method not in CPU_METHODS:
            messagebox.showerror(translate('Berechnung'), reason + '\n\n' +
                                 translate('Dieses Verfahren benötigt eine GPU. '
                                           'Im CPU-Modus stehen Edit-Modelle mit vier Schritten zur Wahl.'),
                                 parent=self.window)
            return False
        if not messagebox.askyesno(
                translate('Berechnung'),
                translate(
                    '{0}\n\nFür diese Sitzung auf CPU wechseln? Die Verarbeitung kann deutlich länger dauern.',
                    reason,
                ),
                parent=self.window):
            return False
        self.backend.close()
        self.backend.compute = CPU
        self.active_compute = CPU
        self.update_compute_label()
        self.method_ids = self.available_method_ids()
        self.method_widget.configure(values=list(self.method_ids))
        self.refresh_processing_menu()
        self.status.set_message('CPU für diese Sitzung aktiv')
        return True

    def setup_for_job(self, upscaler):
        options = dict(method=self.current_method, faces=self.faces.get(), upscaler=upscaler)
        setup = Setup(ROOT, **options, compute=self.active_compute)
        missing_nvidia = (setup.comfy and self.active_compute == NVIDIA and (os.name == 'nt' or LINUX)
                          and not nvidia_driver_available())
        if self.current_method == QWEN2509_NUNCHAKU:
            if self.active_compute != NVIDIA or missing_nvidia:
                messagebox.showerror(translate('Berechnung'), translate(NUNCHAKU_GPU_REQUIRED), parent=self.window)
                return None
        elif setup.comfy and missing_nvidia:
            if not self.offer_cpu_fallback(translate(GPU_HINTS[NVIDIA])):
                return None
            setup = Setup(ROOT, **options, compute=self.active_compute)
        return setup

    def approve_setup(self, setup, upscaler):
        method = self.current_method
        download_bytes = setup.remaining_download_bytes()
        transfer = (translate('Noch etwa {0} Download.', format_download_size(download_bytes)) if download_bytes
                    else translate('Vorhandene Dateien werden geprüft.'))
        if LINUX and setup.comfy and not setup.runtime_ready():
            transfer = translate('ComfyUI und Python-Pakete werden eingerichtet.') + (' ' + transfer if download_bytes else '')
        upscaler_names = ''
        if upscaler in UPSCALE_LICENSES:
            upscaler_names = f'{upscaler}: {UPSCALE_LICENSES[upscaler]}.\n'
        backend_license = 'ComfyUI: GPL-3.0.\n' if setup.comfy else ''
        device = compute_label(setup.compute) if setup.comfy else 'CPU'
        if method in COLORIZATION_METHODS and setup.comfy and setup.compute != CPU:
            device = translate('CPU (Kolorierung) · {0} (Upscaler)', device)
        backend_device = translate('Berechnung: {0}.\n', device)
        if setup.compute == CPU and method not in NO_PROMPT:
            backend_device += translate('Dieses Verfahren kann auf der CPU viel Zeit und Arbeitsspeicher benötigen.\n')
        face_license = translate('Gesichtspunkte (iBUG 300-W): nichtkommerziell.\n') if method == MICROSOFT and self.faces.get() else ''
        return messagebox.askyesno(
            translate('Modelle einrichten'),
            translate(
                '{0}\n\n{1}{2} Lizenz für das Verfahren: {3}.\n{4}{5}{6}\nJetzt einrichten?',
                translate(METHODS[method]), backend_device, transfer, translate(LICENSES[method]),
                face_license, upscaler_names, backend_license,
            ),
            parent=self.window,
        )

    def preload_clicked(self):
        if self.action or self.closing:
            return
        requests = choose_preloads(self.window, ROOT, self.active_compute, self.current_method,
                                   self.effective_upscaler(), self.faces.get(), self.supports_nunchaku())
        if requests:
            self.start_worker('preload', self.preload, requests, self.active_compute)

    def preload(self, requests, compute):
        completed = 0
        failures = []
        backend_closed = False
        try:
            for method, faces, upscaler in requests:
                if self.cancelled.is_set():
                    raise SetupCancelled(translate('Einrichtung abgebrochen.'))
                label = preload_label(method, upscaler)
                try:
                    setup = Setup(ROOT, notify=self.notify_setup, transfer=self.show_transfer,
                                  cancelled=self.cancelled.is_set, method=method, faces=faces,
                                  upscaler=upscaler, compute=compute)
                    self.notify_setup(label)
                    if setup.comfy and not backend_closed and not setup.ready():
                        self.backend.close()
                        backend_closed = True
                    setup.ensure()
                    completed += 1
                except SetupCancelled:
                    raise
                except (OSError, RuntimeError, ValueError) as exc:
                    TechnicalLog(ROOT / 'logs/application.log').write(traceback.format_exc() + '\n')
                    failures.append(f'{label} · {exc}')
            if self.cancelled.is_set():
                raise SetupCancelled(translate('Einrichtung abgebrochen.'))
            if failures:
                summary = translate('{0} eingerichtet · {1} fehlgeschlagen', completed, len(failures))
                self.events.put(('error', summary + '\n\n' + '\n\n'.join(failures)))
            else:
                self.events.put(('done', (('Einrichtung abgeschlossen.',),)))
        except SetupCancelled as exc:
            self.events.put(('done', str(exc)))
        except Exception as exc:
            TechnicalLog(ROOT / 'logs/application.log').write(traceback.format_exc() + '\n')
            self.events.put(('error', str(exc)))
        finally:
            self.events.put(('idle', (False, None)))

    def pick_sources(self, selected):
        if not selected:
            return
        path = Path(selected).resolve()
        try:
            sources = collect(path)
            if not sources:
                raise ValueError(translate('Der Ordner enthält keine unterstützten Bilder.'))
        except (OSError, ValueError) as exc:
            messagebox.showerror(translate('Eingabe'), str(exc), parent=self.window)
            return
        source = sources[0]
        before = None
        try:
            before, _ = open_photo(source)
        except (OSError, ValueError) as exc:
            if path.is_file():
                messagebox.showerror(translate('Eingabe'), str(exc), parent=self.window)
                return
            self.status.set_message('Vorschau für {0}: {1}', source.name, exc)
        self.sources = sources
        self.crops = {}
        self.rotations = {}
        self.clear_second_image()
        self.preview_source = source
        self.preview_size = before.size if before else None
        self.update_dimensions()
        self.input_value.set(str(path))
        self.results = self.saved_results(sources)
        self.index = len(self.results) - 1
        if self.index >= 0:
            if before is not None:
                before.close()
            self.show_result(reset_divider=True)
        else:
            self.show_input(before)
        if not self.output.get():
            self.output.set(str((path if path.is_dir() else path.parent) / 'Restauriert'))
        self.check_ready()

    def show_input(self, before):
        self.compare.show(before, reset_divider=True)
        path = Path(self.input_value.get())
        if path.is_dir():
            count = len(self.sources)
            if count == 1:
                self.caption.set_message('1 Bild · {0}', self.preview_source.name)
            else:
                self.caption.set_message('{0} Bilder · {1}', count, self.preview_source.name)
        else:
            self.caption.set(path.name)
        self.navigation()

    def edit_crop(self):
        if self.action or not self.sources:
            return
        selected = self.results[self.index][0] if self.index >= 0 else self.preview_source
        result = edit_crops(self.window, self.sources, self.crops, selected, rotations=self.rotations)
        if result is None:
            return
        source, crops = result
        changed = crops != self.crops
        if not changed and source == self.preview_source and self.index < 0:
            return
        self.crops = crops
        self.preview_source = source
        if self.refresh_input_preview() and changed:
            self.status.set_message('Beschnitt übernommen.' if crops else 'Beschnitt zurückgesetzt.')
        self.check_ready()

    def rotate_source(self, turns):
        if self.action or not self.sources:
            return
        source = self.results[self.index][0] if self.index >= 0 else self.preview_source
        previous = self.rotations.get(source, 0)
        rotation = 0 if turns is None else (previous + turns) % 4
        if rotation == previous:
            return
        if rotation:
            self.rotations[source] = rotation
        else:
            self.rotations.pop(source, None)
        if source in self.crops:
            self.crops[source] = self.crops[source].rotated(rotation - previous)
        self.preview_source = source
        if self.refresh_input_preview():
            self.status.set_message('Drehung übernommen.' if rotation else 'Drehung zurückgesetzt.')
        self.check_ready()

    def choose_second_image(self):
        title = translate('Zweites Bild auswählen')
        name = filedialog.askopenfilename(parent=self.window, title=title,
                                         filetypes=[(translate(label), pattern) for label, pattern in FILE_TYPES])
        if not name:
            return
        try:
            self.set_second_image(Path(name).resolve())
        except (OSError, ValueError, SyntaxError) as exc:
            messagebox.showerror(title, str(exc), parent=self.window)

    def set_second_image(self, path, *, rotation=0):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            raise ValueError(translate('Bitte ein unterstütztes Bild auswählen.'))
        image, _ = open_photo(path, rotation=rotation)
        with image:
            scale = min(width / edge for width, edge in zip(REFERENCE_PREVIEW_SIZE, image.size))
            size = tuple(max(1, round(edge * scale)) for edge in image.size)
            with image.resize(size, Image.Resampling.LANCZOS) as preview:
                thumbnail = ImageTk.PhotoImage(preview, master=self.window)
        self.second_image = path
        self.second_rotation = rotation
        self.second_thumbnail = thumbnail
        self.update_second_image()

    def clear_second_image(self):
        self.second_image = None
        self.second_rotation = 0
        self.second_thumbnail = None
        self.update_second_image()

    def rotate_second_image(self, turns):
        if self.action or self.second_image is None:
            return
        rotation = 0 if turns is None else (self.second_rotation + turns) % 4
        if rotation == self.second_rotation:
            return
        try:
            self.set_second_image(self.second_image, rotation=rotation)
        except (OSError, ValueError, SyntaxError) as exc:
            messagebox.showerror(translate('Drehen'), str(exc), parent=self.window)

    def update_second_image(self):
        if self.current_method not in TWO_IMAGE_METHODS:
            self.second_row.pack_forget()
            return
        self.second_row.pack(fill='x', pady=(4, 0))
        path = self.second_image
        self.second_button.configure(text=translate('Ersetzen …' if path else 'Hinzufügen …'),
                                     state='normal' if self.sources and not self.action else 'disabled')
        self.second_name.configure(text=path.name if path else translate('Kein Bild ausgewählt'))
        self.second_preview.itemconfigure(self.second_preview_item, image=self.second_thumbnail or '')
        self.second_rotate_button.configure(state='normal' if path and not self.action else 'disabled')
        self.remove_second_button.configure(state='normal' if path and not self.action else 'disabled')

    def refresh_input_preview(self):
        self.index = -1
        source = self.preview_source
        try:
            before, _ = open_photo(source, crop=self.crops.get(source), rotation=self.rotations.get(source, 0))
        except (OSError, ValueError, SyntaxError) as exc:
            before = None
            self.status.set_message('Vorschau für {0}: {1}', source.name, exc)
        self.preview_size = before.size if before is not None else None
        self.update_dimensions()
        self.show_input(before)
        return before is not None

    def source_size(self, source):
        crop = self.crops.get(source)
        if crop is not None:
            return crop.size
        if source == self.preview_source and self.preview_size is not None:
            return self.preview_size
        return photo_size(source, rotation=self.rotations.get(source, 0))

    def clear_history(self):
        if self.action or self.closing:
            return
        title = translate('Auftragsverlauf löschen')
        if not messagebox.askyesno(
            title,
            translate(
                'Den gesamten Auftragsverlauf löschen?\n\n'
                'Die Zuordnung bisheriger Ergebnisse und ihre gespeicherten Beschnitte gehen verloren. '
                'Die exportierten Bilder bleiben auf der Festplatte.'
            ),
            default=messagebox.NO,
            parent=self.window,
        ):
            return
        try:
            JOBS_LOG.unlink(missing_ok=True)
        except OSError as exc:
            messagebox.showerror(title, translate('Der Auftragsverlauf konnte nicht gelöscht werden.\n\n{0}', exc),
                                 parent=self.window)
            return
        self.results.clear()
        if self.sources and self.index >= 0:
            self.refresh_input_preview()
        else:
            self.index = -1
            self.navigation()
        self.status.set_message('Auftragsverlauf gelöscht.')

    def saved_results(self, sources):
        source_set = set(sources)
        recorded = {}
        try:
            with JOBS_LOG.open(encoding='utf-8', errors='replace') as log:
                for line in log:
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(entry, dict) or entry.get('status') != 'ok':
                        continue
                    source = entry.get('source')
                    output = entry.get('output')
                    if not isinstance(source, str) or not isinstance(output, str):
                        continue
                    output = Path(output)
                    recorded.pop(output, None)
                    turn = entry.get('source_rotation', 0)
                    if type(turn) is not int or not 0 <= turn <= 3:
                        turn = 0
                    recorded[output] = Path(source), CropRegion.from_record(entry), turn
        except OSError:
            pass
        results = []
        for output, (source, crop, turn) in recorded.items():
            if source not in source_set or not output.is_absolute():
                continue
            try:
                if output.is_file():
                    results.append((source, output, crop, turn))
            except OSError:
                continue
        return results

    def choose_photo(self):
        filetypes = [(translate(label), pattern) for label, pattern in FILE_TYPES]
        self.pick_sources(filedialog.askopenfilename(parent=self.window, title=translate('Bild auswählen'),
                                                     filetypes=filetypes))

    def choose_folder(self):
        self.pick_sources(filedialog.askdirectory(parent=self.window, title=translate('Eingabeordner auswählen')))

    def choose_output(self):
        path = filedialog.askdirectory(parent=self.window, title=translate('Ausgabeordner auswählen'))
        if path:
            self.output.set(path)

    @property
    def presets(self):
        return {**PRESETS, **self.custom}

    def preset_names(self):
        self.preset_labels = {name: translate(name) for name in PRESETS}
        reserved = {*self.preset_labels.values(), translate('Eigener Text')}
        for name in self.custom:
            label = name
            if label in reserved:
                label = translate('{0} (eigener Prompt)', name)
                number = 2
                while label in reserved or label in self.custom:
                    label = translate('{0} (eigener Prompt {1})', name, number)
                    number += 1
            self.preset_labels[name] = label
            reserved.add(label)
        self.preset_ids = {label: name for name, label in self.preset_labels.items()}
        return list(self.preset_ids)

    def preset_key(self):
        return self.preset_ids.get(self.preset.get(), 'Eigener Text')

    def reserved_preset(self, name):
        return name in PRESETS

    def read_custom_presets(self, saved):
        if not isinstance(saved, dict):
            return {}
        return {name: prompt for name, prompt in saved.items()
                if isinstance(name, str) and name.strip() and isinstance(prompt, str)
                and not self.reserved_preset(name)}

    def remember_prompt(self):
        if self.current_method not in NO_PROMPT:
            prompt = self.prompt.get('1.0', 'end-1c')
            if self.draft or prompt != PRESETS[DEFAULT_PROMPT_NAME]:
                self.draft = {'prompt': prompt, 'preset': self.preset_key()}

    def scaling_group(self):
        method = self.current_method
        if method in COLORIZATION_METHODS:
            return 'colorization'
        return UPSCALING if method == UPSCALING else 'restoration'

    def remember_scaling(self):
        self.scaling[self.scaling_group()] = dict(
            size=self.size_choice(), side_pixels=self.side_pixels.get(), upscaler=self.upscaler.get(),
        )

    def load_scaling(self, preset=None):
        method = self.current_method
        values = self.scaling.get(self.scaling_group(), {}) if preset is None else preset
        self.size.set(translate(method_size(method, values.get('size'))))
        self.side_pixels.set(str(values.get('side_pixels') or 2160))
        self.upscaler.set(resolve_upscaler(method, values.get('upscaler')))

    def size_choice(self):
        return method_size(self.current_method, self.size_ids.get(self.size.get()))

    def selected_size(self):
        choice = self.size_choice()
        return choice, int(self.side_pixels.get()) if choice in CUSTOM_SIZES else 2160

    def update_dimensions(self, *args):
        choice = self.size_choice()
        if choice in CUSTOM_SIZES:
            self.side_entry.pack(side='left', padx=(5, 0))
        else:
            self.side_entry.pack_forget()
        if self.preview_size is None:
            self.dimensions.set('')
            return
        input_width, input_height = self.preview_size
        try:
            width, height = output_size(self.preview_size, *self.selected_size(), method=self.current_method)
        except ValueError:
            output = translate('Zielgröße ungültig')
        else:
            output = translate('Ausgabe {0} × {1} px', width, height)
        photo = ''
        if len(self.sources) > 1:
            photo = ' · ' + translate('Bild {0}/{1}', self.sources.index(self.preview_source) + 1, len(self.sources))
        self.dimensions.set(translate('Eingabe {0} × {1} px · {2}{3}', input_width, input_height, output, photo))

    def update_size_controls(self):
        self.size_widget.configure(values=tuple(map(translate, size_choices(self.current_method))))
        rescale = self.size_choice() != NO_RESCALE
        self.upscale_options.configure(
            textvariable=self.upscaler if rescale else self.inactive_upscaler,
            state='disabled' if self.action or not rescale else 'readonly',
        )
        self.update_dimensions()

    def load_method_prompt(self):
        method = self.current_method
        self.update_second_image()
        self.stop_button.configure(text=self.stop_label())
        self.microsoft_options.grid_remove()
        self.prompt_heading.set(translate('Restaurierung') if method == MICROSOFT else 'Prompt')
        if method in NATIVE_METHODS:
            self.prompt_heading_widget.grid_remove()
        else:
            self.prompt_heading_widget.grid()
        if method in NO_PROMPT:
            if method == MICROSOFT:
                self.microsoft_options.grid()
            for widget in (self.preset_widget, self.prompt, self.variant_row, self.seed_row, self.seed_actions):
                widget.grid_remove()
            self.prompt_actions.grid_remove()
            return
        for widget in (self.preset_widget, self.prompt, self.variant_row, self.seed_row, self.seed_actions):
            widget.grid()
        self.prompt_actions.grid()
        self.preset_widget.configure(values=self.preset_names())
        saved_prompt = self.draft.get('prompt')
        saved_preset = self.draft.get('preset')
        if isinstance(saved_prompt, str):
            presets = self.presets
            current = saved_preset if isinstance(saved_preset, str) and presets.get(saved_preset) == saved_prompt else None
            if current is None:
                current = next((name for name, text in presets.items() if text == saved_prompt), 'Eigener Text')
        else:
            current = DEFAULT_PROMPT_NAME
            saved_prompt = PRESETS[current]
        self.preset.set(self.preset_labels.get(current, translate(current)))
        self.prompt.delete('1.0', 'end')
        self.prompt.insert('1.0', saved_prompt)
        self.prompt.edit_modified(False)

    def choose_method(self, event=None):
        self.remember_prompt()
        self.remember_scaling()
        self.current_method = self.method_ids[self.method.get()]
        self.load_scaling()
        self.update_size_controls()
        self.load_method_prompt()
        self.check_ready()
        self.save_settings()

    def choose_preset(self, event=None):
        value = self.presets.get(self.preset_key())
        if value is not None:
            self.prompt.delete('1.0', 'end')
            self.prompt.insert('1.0', value)
            self.prompt.edit_modified(False)
            self.draft = {'prompt': value, 'preset': self.preset_key()}
            self.save_settings()

    def prompt_changed(self, event):
        if self.prompt.edit_modified():
            self.prompt.edit_modified(False)
            selected = self.presets.get(self.preset_key())
            if selected != self.prompt.get('1.0', 'end-1c'):
                self.preset.set(translate('Eigener Text'))

    def leave_editor_on_click(self, event):
        focused = self.window.focus_get()
        if focused is self.prompt and event.widget not in (self.prompt, self.snippets_button):
            self.window.focus_set()
        elif focused in (self.variant_widget, self.seed_entry) and event.widget is not focused:
            self.window.focus_set()

    def save_preset(self):
        value = self.prompt.get('1.0', 'end-1c').strip()
        if not value:
            return
        title = translate('Prompt speichern')
        name = simpledialog.askstring(title, translate('Name für den Prompt'), parent=self.window)
        if not name or not name.strip():
            return
        name = name.strip()
        if self.reserved_preset(name):
            messagebox.showinfo(title, translate('Bitte einen eigenen Namen verwenden.'), parent=self.window)
            return
        if name in self.custom and not messagebox.askyesno(title, translate('„{0}“ ersetzen?', name), parent=self.window):
            return
        self.custom[name] = value
        self.preset_widget.configure(values=self.preset_names())
        self.preset.set(self.preset_labels[name])
        self.draft = {'prompt': value, 'preset': name}
        self.save_settings()
        if self.action is None:
            self.status.set_message('Prompt „{0}“ gespeichert.', name)

    def refresh_processing_menu(self):
        self.processing_menu.delete(0, 'end')
        self.processing_delete_menu.delete(0, 'end')
        available = set(self.method_ids.values())
        for name, preset in {**BUILTIN_PROCESSING_PRESETS, **self.processing_presets}.items():
            self.processing_menu.add_command(
                label=translate(name) if name in BUILTIN_PROCESSING_PRESETS else name,
                command=lambda key=name: self.load_processing_preset(key),
                state='normal' if preset['method'] in available else 'disabled',
            )
        self.processing_menu.add_separator()
        self.processing_menu.add_command(label=translate('Aktuelle Einstellungen speichern …'), command=self.save_processing_preset)
        if self.processing_presets:
            for name in self.processing_presets:
                self.processing_delete_menu.add_command(label=name, command=lambda key=name: self.delete_processing_preset(key))
            self.processing_menu.add_cascade(label=translate('Eigenes Preset löschen'), menu=self.processing_delete_menu)

    def save_processing_preset(self):
        if self.action:
            return
        method = self.current_method
        preset = {'method': method, 'format': self.output_format.get()}
        if method not in NO_PROMPT:
            prompt = self.prompt.get('1.0', 'end-1c')
            if not prompt.strip():
                messagebox.showinfo('Preset', translate('Bitte einen Prompt eingeben.'), parent=self.window)
                return
            self.finish_variant_edit()
            preset.update(prompt=prompt, preset=self.preset_key(), variants=self.variant_count)
            try:
                seed = self.fixed_seed()
            except ValueError as exc:
                messagebox.showinfo('Seed', str(exc), parent=self.window)
                return
            if seed is not None:
                preset['seed'] = seed
        try:
            size, side_pixels = self.selected_size()
            if not 1 <= side_pixels <= MAX_SIDE:
                raise ValueError
        except ValueError:
            messagebox.showinfo('Preset', translate(
                                                          'Bitte eine Seitenlänge zwischen 1 und {0} px eingeben.',
                                                          MAX_SIDE,
                                                      ),
                                parent=self.window)
            return
        preset.update(size=size, side_pixels=side_pixels, upscaler=self.upscaler.get())
        if method == MICROSOFT:
            preset.update(scratches=self.scratches.get(), faces=self.faces.get())

        name = simpledialog.askstring('Preset', translate('Name für das Preset'), parent=self.window)
        name = name.strip() if name else ''
        if not name:
            return
        if name in BUILTIN_PROCESSING_PRESETS:
            messagebox.showinfo('Preset', translate('Bitte einen eigenen Namen verwenden.'), parent=self.window)
            return
        if name in self.processing_presets and not messagebox.askyesno(
            'Preset', translate('„{0}“ ersetzen?', name), parent=self.window,
        ):
            return
        self.processing_presets[name] = preset
        self.save_settings()
        self.refresh_processing_menu()
        self.status.set_message('Preset „{0}“ gespeichert.', name)

    def load_processing_preset(self, name):
        if self.action:
            return
        preset = BUILTIN_PROCESSING_PRESETS.get(name) or self.processing_presets.get(name)
        if preset is None or preset['method'] not in self.method_ids.values():
            return
        self.remember_prompt()
        self.remember_scaling()
        method = preset['method']
        self.current_method = method
        self.method.set(translate(METHODS[method]))
        fmt = preset.get('format')
        if isinstance(fmt, str) and fmt in FORMATS:
            self.output_format.set(fmt)
        self.load_scaling(preset)
        if method == MICROSOFT:
            self.scratches.set(preset.get('scratches', True) is True)
            self.faces.set(preset.get('faces') is True)
        if method not in NO_PROMPT:
            self.variants.set(str(VARIANT_COUNTS.get(str(preset.get('variants')), 1)))
            prompt = preset.get('prompt')
            if isinstance(prompt, str) and prompt.strip():
                self.draft = {'prompt': prompt, 'preset': preset.get('preset')}
            seed = parse_seed(preset.get('seed'))
            self.seed_value.set('' if seed is None else str(seed))
        self.update_seed()
        self.update_size_controls()
        self.load_method_prompt()
        self.check_ready()
        self.save_settings()
        self.status.set_message('Preset „{0}“ geladen.', name)

    def delete_processing_preset(self, name):
        if self.action or name not in self.processing_presets:
            return
        if messagebox.askyesno('Preset', translate('„{0}“ löschen?', name), parent=self.window):
            del self.processing_presets[name]
            self.save_settings()
            self.refresh_processing_menu()

    def save_settings(self):
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        self.remember_prompt()
        self.remember_scaling()
        data = dict(output=self.output.get(), format=self.output_format.get(), seed=self.seed, compute=self.compute.get(),
                    method=self.current_method, prompt_draft=self.draft, presets=self.custom,
                    language=self.language,
                    processing_presets=self.processing_presets,
                    variants=str(self.variant_count), scaling=self.scaling,
                    scratches=self.scratches.get(), faces=self.faces.get())
        stage = SETTINGS.with_suffix('.tmp')
        stage.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        stage.replace(SETTINGS)

    def start_clicked(self):
        if self.action:
            self.cancelled.set()
            self.start_button.configure(state='disabled')
            self.stop_button.configure(state='disabled')
            self.status.set_message('Abbruch läuft …')
            return
        if not self.sources:
            messagebox.showinfo(translate('Eingabe'), translate('Bitte ein Bild oder einen Ordner auswählen.'), parent=self.window)
            return
        self.finish_variant_edit()
        output_text = self.output.get().strip()
        no_prompt = self.current_method in NO_PROMPT
        prompt = '' if no_prompt else self.prompt.get('1.0', 'end-1c').strip()
        if not output_text or (not prompt and not no_prompt):
            message = translate('Bitte einen Ausgabeordner auswählen.') if not output_text else translate('Bitte einen Prompt eingeben.')
            messagebox.showinfo('Start', message, parent=self.window)
            return
        folder = Path(output_text).expanduser().resolve()
        if folder == Path(self.input_value.get()).resolve():
            messagebox.showinfo(translate('Ausgabeordner'), translate('Bitte einen separaten Ausgabeordner wählen.'), parent=self.window)
            return
        try:
            first_size = self.source_size(self.sources[0])
        except (OSError, ValueError, SyntaxError):
            first_size = (1, 1)
        try:
            size_choice = self.selected_size()
            output_size(first_size, *size_choice, method=self.current_method)
        except ValueError as exc:
            messagebox.showinfo(translate('Zielgröße'), str(exc), parent=self.window)
            return
        try:
            seed = None if no_prompt else self.fixed_seed()
        except ValueError as exc:
            messagebox.showinfo('Seed', str(exc), parent=self.window)
            return
        upscaler = self.effective_upscaler(all_sources=True)
        setup = self.setup_for_job(upscaler)
        if setup is None:
            return
        ready = setup.ready()
        if not ready and not self.approve_setup(setup, upscaler):
            return
        variants = 1 if no_prompt else self.variant_count
        second_image = self.second_image if self.current_method in TWO_IMAGE_METHODS else None
        second_rotation = self.second_rotation if second_image is not None else 0
        job = (tuple(self.sources), folder, self.output_format.get(), prompt, seed, variants,
               self.scratches.get(), size_choice, self.crops.copy(), self.rotations.copy(), second_image, second_rotation)
        self.save_settings()
        self.launch('run' if ready else 'run_setup', job, upscaler=upscaler)

    def launch(self, action, job, *, upscaler):
        self.start_worker(action, self.work, self.current_method, self.faces.get(), job, upscaler)

    def start_worker(self, action, target, *args):
        self.action = action
        self.cancelled.clear()
        self.stop_after.clear()
        self.progress_bar.set(None)
        self.elapsed.set('')
        self.device.set('')
        self.status.set_message('Modelldateien werden geprüft …')
        self.busy(True)
        Thread(target=target, args=args, daemon=True).start()

    def busy(self, value):
        for control in self.controls:
            set_control_state(control, 'disabled' if value else 'normal')
        for control in (self.method_widget, self.size_widget):
            control.configure(state='disabled' if value else 'readonly')
        self.upscale_options.configure(state='disabled' if value or self.size_choice() == NO_RESCALE else 'readonly')
        self.format_widget.configure(state='disabled' if value else 'readonly')
        self.start_button.configure(
            text=translate('Abbrechen') if value else 'Start',
            state='disabled' if value and self.cancelled.is_set() else 'normal',
        )
        self.stop_button.configure(
            text=self.stop_label(),
            state='normal' if value and self.action == 'run' else 'disabled',
        )
        self.update_seed()
        self.navigation()

    def stop_label(self):
        return translate('Nach Variante stoppen') if self.current_method not in NO_PROMPT and self.variant_count > 1 else translate('Nach Bild stoppen')

    def stop(self):
        self.stop_after.set()
        self.stop_button.configure(text=translate('Stopp vorgemerkt'), state='disabled')

    def notify_setup(self, text):
        self.events.put(('progress', None))
        self.events.put(('status', text))

    def show_transfer(self, name, current, total, phase):
        self.events.put(('transfer', (name, current, total, phase)))

    def work(self, method, faces, job, upscaler=None):
        upscaler = resolve_upscaler(method, upscaler)
        finished = False
        retry_on_cpu = None

        def status(text):
            self.events.put(('status', text))

        try:
            setup = Setup(ROOT, notify=self.notify_setup, transfer=self.show_transfer,
                          cancelled=self.cancelled.is_set, method=method, faces=faces,
                          upscaler=upscaler, compute=self.active_compute)
            paths = setup.ensure()
            if self.cancelled.is_set():
                raise SetupCancelled(translate('Bearbeitung abgebrochen.'))
            if paths is not None and self.verified_compute != setup.compute:
                setup.verify_compute(paths[0])
                self.verified_compute = setup.compute
            self.events.put(('begin', None))
            if self.stop_after.is_set() or self.cancelled.is_set():
                self.events.put(('done', (('Vor dem ersten Bild beendet.',),)))
                return
            (sources, folder, output_format, prompt, fixed_seed, variants, scratches, size_choice,
             crops, rotations, second_image, second_rotation) = job
            exiftool = None if output_format == 'PNG' else exiftool_executable(ROOT)
            client, definitions, models, device, colorizer = None, {}, {}, 'CPU', None
            if uses_comfy(method, upscaler):
                client = Client(self.backend.start(paths, status, self.cancelled.is_set, method=method), ROOT)
                device = client.device() or COMPUTE_DEVICES[self.active_compute]
                if self.active_compute == AMD and device.startswith('CUDA '):
                    device = device.replace('CUDA ', 'ROCm ', 1)
                definitions = client.json('/object_info')
                models = select_models(definitions, method, upscaler)
            if method in COLORIZATION_METHODS:
                status(translate('Modell wird geladen …'))
                if setup.color_runtime_path is not None and str(setup.color_runtime_path) not in sys.path:
                    sys.path.insert(0, str(setup.color_runtime_path))
                colorizer = Colorizer(setup.colorizer_path, method=method)
                models['colorizer'] = colorizer.model_name
            device_label = ('{0}', device)
            if method in COLORIZATION_METHODS and device != 'CPU':
                device_label = ('CPU (Kolorierung) · {0} (Upscaler)', device)
            self.events.put(('device', device_label))
            device = translate(*device_label)
            completed, errors, warnings = 0, 0, 0
            random_source = secrets.SystemRandom()
            for index, source in enumerate(sources, 1):
                crop = crops.get(source)
                rotation = rotations.get(source, 0)
                if self.stop_after.is_set() or self.cancelled.is_set():
                    break
                if method in NO_PROMPT:
                    seeds = [None]
                elif fixed_seed is not None:
                    seeds = ((fixed_seed + offset) % (MAX_SEED + 1) for offset in range(variants))
                else:
                    seeds = random_source.sample(range(2**63 - 1), variants)
                staged_id = secrets.token_hex(16)
                for variant, seed in enumerate(seeds, 1):
                    if self.stop_after.is_set() or self.cancelled.is_set():
                        break
                    prefix = translate('Bild {0}/{1}', index, len(sources))
                    if variants > 1:
                        prefix += translate(' · Variante {0}/{1}', variant, variants)
                    started = time.monotonic()
                    self.events.put(('image_started', started))
                    record = dict(source=str(source), seed=seed, method=METHODS[method], models=models, prompt=prompt,
                                  device=device, variant=variant, variants=variants,
                                  format=output_format, utc=datetime.now(timezone.utc).isoformat(), workflow=method)
                    try:
                        output, warning = restore(
                            client, models, source, folder, output_format, exiftool, prompt, seed,
                            lambda text: status(f'{prefix} · {text}'),
                            self.cancelled.is_set, record,
                            progress=lambda value: self.events.put(('progress', value)),
                            method=method, scratches=scratches, faces=faces,
                            staged_id=staged_id,
                            size_choice=size_choice, upscaler=upscaler, definitions=definitions, colorizer=colorizer,
                            source_crop=crop, source_rotation=rotation, second_image=second_image,
                            second_rotation=second_rotation,
                        )
                        record.update(status='ok', output=str(output), metadata_warnings=warning or '')
                        completed += 1
                        warnings += int(bool(warning))
                        self.events.put(('result', (source, output, seed, crop, rotation)))
                    except SetupCancelled:
                        record.update(status='cancelled')
                        raise
                    except Exception as exc:
                        errors += 1
                        record.update(status='error', error=str(exc))
                        self.events.put(('file_error', f'{source.name} · {prefix} · {exc}'))
                    finally:
                        record['seconds'] = round(time.monotonic() - started, 2)
                        with JOBS_LOG.open('a', encoding='utf-8') as log:
                            log.write(json.dumps(record, ensure_ascii=False) + '\n')
            summary = [('1 Ergebnis gespeichert',)] if completed == 1 else [('{0} Ergebnisse gespeichert', completed)]
            if errors:
                summary.append((' · {0} fehlgeschlagen', errors))
            if warnings:
                summary.append((' · {0} mit Metadatenhinweisen', warnings))
            if self.cancelled.is_set():
                summary.append((' · abgebrochen',))
            elif self.stop_after.is_set():
                summary.append((' · gestoppt',))
            finished = completed > 0 and errors == 0 and not self.stop_after.is_set() and not self.cancelled.is_set()
            self.events.put(('done', summary))
        except SetupCancelled as exc:
            self.events.put(('done', str(exc)))
        except Exception as exc:
            TechnicalLog(ROOT / 'logs/application.log').write(traceback.format_exc() + '\n')
            if (method != QWEN2509_NUNCHAKU and self.active_compute == NVIDIA
                    and isinstance(exc, (ComputeUnavailable, BackendStartError))):
                retry_on_cpu = (str(exc), job, upscaler)
            else:
                self.events.put(('error', str(exc)))
        finally:
            try:
                if self.cancelled.is_set():
                    self.backend.close()
            finally:
                self.events.put(('idle', (finished, retry_on_cpu)))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'status' and not self.cancelled.is_set():
                    self.status.set(value)
                elif kind == 'transfer' and not self.cancelled.is_set():
                    name, current, total, phase = value
                    self.progress_bar.set(100 * current / total)
                    self.status.set(f'{phase} · {current / 1e9:.2f} / {total / 1e9:.2f} GB · {name}')
                elif kind == 'begin':
                    self.action = 'run'
                    self.progress_bar.set(None)
                    if not self.cancelled.is_set() and not self.stop_after.is_set():
                        self.stop_button.configure(text=self.stop_label(), state='normal')
                elif kind == 'progress':
                    self.progress_bar.set(value)
                elif kind == 'device':
                    self.device.set_message(*value)
                elif kind == 'image_started':
                    self.image_started = value
                elif kind == 'result':
                    self.progress_bar.set(100)
                    self.update_elapsed()
                    self.image_started = None
                    source, output, seed, crop, rotation = value
                    if seed is not None:
                        self.seed = seed
                    follow_latest = self.index < 0 or self.index == len(self.results) - 1
                    self.results.append((source, output, crop, rotation))
                    if follow_latest:
                        self.index = len(self.results) - 1
                        self.show_result()
                    else:
                        self.navigation()
                    self.update_seed()
                elif kind in ('error', 'file_error', 'done'):
                    self.update_elapsed()
                    self.image_started = None
                    if self.progress_bar.value is None or kind in ('error', 'file_error'):
                        self.progress_bar.set(0)
                    if kind == 'done' and not isinstance(value, str):
                        self.status.set_messages(*value)
                        value = self.status.get()
                    else:
                        self.status.set(value)
                    if kind == 'file_error':
                        self.last_file_error = value
                    elif kind == 'error' and not self.closing:
                        messagebox.showerror(APP_NAME, value, parent=self.window)
                    elif kind == 'done' and getattr(self, 'last_file_error', None) and not self.closing:
                        messagebox.showwarning(translate('Bearbeitung mit Fehlern'),
                                               value + '\n\n' + self.last_file_error + translate('\n\nDetails in logs/jobs.jsonl.'),
                                               parent=self.window)
                elif kind == 'idle':
                    finished, retry_on_cpu = value
                    self.action = None
                    self.last_file_error = None
                    self.check_ready()
                    self.busy(False)
                    self.save_settings()
                    if self.closing:
                        self.finish_close()
                        return
                    if retry_on_cpu and not self.cancelled.is_set() and not self.stop_after.is_set():
                        reason, job, upscaler = retry_on_cpu
                        if self.offer_cpu_fallback(reason):
                            self.check_ready()
                            action = 'run' if self.ready else 'run_setup'
                            self.launch(action, job, upscaler=upscaler)
                    if finished and not self.cancelled.is_set():
                        self.play_ready_sound()
        except Empty:
            pass
        self.update_elapsed()
        self.window.after(75, self.poll)

    def play_ready_sound(self):
        if sys.platform == 'win32':
            try:
                import winsound
                winsound.PlaySound(
                    str(ROOT / 'assets' / 'ready.wav'),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                return
            except (ImportError, OSError, RuntimeError):
                pass
        self.window.bell()

    def update_elapsed(self):
        if self.image_started is not None:
            minutes, seconds = divmod(int(time.monotonic() - self.image_started), 60)
            self.elapsed.set_message('Laufzeit {0:02d}:{1:02d}', minutes, seconds)

    def browse_results(self, event, step):
        if isinstance(event.widget, (tk.Text, tk.Entry, ttk.Entry, ttk.Combobox, tk.Spinbox, ttk.Spinbox)):
            return
        self.move(step)
        return 'break'

    def move(self, step):
        next_index = self.index + step
        if 0 <= next_index < len(self.results):
            self.index = next_index
            self.show_result()

    def reuse_result(self):
        if self.action is None and 0 <= self.index < len(self.results):
            self.pick_sources(self.results[self.index][1])

    def show_result(self, *, reset_divider=False):
        source, output, crop, rotation = self.results[self.index]
        before = None
        after = None
        try:
            before, _ = open_photo(source, crop=crop, rotation=rotation)
            after, _ = open_photo(output)
        except (OSError, ValueError) as exc:
            self.caption.set_message('{0} · Vorschau nicht verfügbar', output.name)
            self.status.set_message('Vorschau: {0}', exc)
        else:
            self.caption.set(f'{output.name} · {after.width} × {after.height} px')
        view_key = (source, crop, rotation) if before is not None and after is not None else None
        self.compare.show(before, after, reset_divider=reset_divider, view_key=view_key)
        self.navigation()

    def navigation(self):
        self.result_position.set(f'{self.index + 1}/{len(self.results)}')
        self.prev_button.configure(state='normal' if self.index > 0 else 'disabled')
        self.next_button.configure(state='normal' if self.index + 1 < len(self.results) else 'disabled')
        can_reuse = self.action is None and 0 <= self.index < len(self.results)
        self.reuse_result_button.configure(state='normal' if can_reuse else 'disabled')
        self.clear_history_button.configure(state='normal' if not self.action and JOBS_LOG.is_file() else 'disabled')
        self.crop_button.configure(
            state='normal' if self.sources and not self.action else 'disabled',
            style='Input.Primary.TButton' if self.crops else 'Input.TButton',
        )
        self.rotate_button.configure(state='normal' if self.sources and not self.action else 'disabled')
        self.update_second_image()

    def change_language(self, language):
        if language == self.language or self.action or self.closing:
            return
        preset, size = self.preset_key(), self.size_choice()
        self.language = configure_language(language)
        self.language_button.configure(text=LANGUAGE_LABELS[self.language])
        for widget, label in self.labels.items():
            widget.configure(text=translate(label))
        for index, compute in enumerate(COMPUTE_DEVICES):
            self.compute_menu.entryconfigure(index, label=compute_label(compute))
        for index, (label, _) in enumerate(ROTATION_CHOICES):
            self.rotation_menu.entryconfigure(index, label=translate(label))
            self.second_rotation_menu.entryconfigure(index, label=translate(label))
        self.prompt_menu.set_language(self.language)
        self.update_compute_label()
        self.update_setup_status()
        self.method_ids = self.available_method_ids()
        self.method_widget.configure(values=list(self.method_ids))
        self.method.set(translate(METHODS[self.current_method]))
        self.refresh_processing_menu()
        self.prompt_heading.set(translate('Restaurierung') if self.current_method == MICROSOFT else 'Prompt')
        self.preset_widget.configure(values=self.preset_names())
        self.preset.set(self.preset_labels.get(preset, translate(preset)))
        self.size_ids = {translate(choice): choice for choice in SIZE_CHOICES}
        self.size.set(translate(size))
        self.inactive_upscaler.set(translate('Aus'))
        self.update_size_controls()
        self.update_seed()
        self.update_second_image()
        for label in (self.status, self.caption, self.elapsed, self.device):
            label.refresh()
        self.compare.schedule()
        try:
            self.save_settings()
        except OSError as exc:
            self.status.set_message('Einstellungen konnten nicht gespeichert werden: {0}', exc)

    def close(self):
        if self.closing:
            return
        if self.action:
            if not messagebox.askyesno(APP_NAME, translate('Laufenden Auftrag beenden und das Fenster schließen?'),
                                       parent=self.window):
                return
            self.closing = True
            self.cancelled.set()
            self.status.set_message('Programm wird beendet …')
            return
        self.finish_close()

    def finish_close(self):
        try:
            self.save_settings()
        finally:
            self.backend.close()
            self.destroy_window()

    def destroy_window(self):
        # Cancel Tcl timers and let each widget dispose of its own callbacks.
        for job in self.window.tk.splitlist(self.window.tk.call('after', 'info')):
            self.window.tk.call('after', 'cancel', job)
        self.window.destroy()


def create_window():
    window = tk.Tk()
    if sys.platform == 'win32':
        try:
            icon_path = str(ROOT / 'assets/restorenate.ico')
            window.iconbitmap(default=icon_path)
            window.iconbitmap(icon_path)
        except tk.TclError as exc:
            TechnicalLog(ROOT / 'logs/application.log').write(f'Programmsymbol konnte nicht geladen werden: {exc}\n')
    return window


def run_gui():
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f'{APP_NAME}.Desktop')
    (ROOT / 'logs').mkdir(exist_ok=True)
    with (ROOT / 'logs/application.lock').open('a+b') as lock:
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            configure_language(read_settings().get('language'))
            window = create_window()
            window.withdraw()
            messagebox.showinfo(APP_NAME, translate('Dieses portable Programmfenster läuft bereits.'), parent=window)
            window.destroy()
            return
        prepare_technical_logs(ROOT / 'logs')
        window = create_window()
        Application(window)
        window.mainloop()


if __name__ == '__main__':
    run_gui()
