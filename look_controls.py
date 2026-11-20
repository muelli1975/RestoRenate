"""Transient LUT preview and output controls for the comparison pane."""
import tkinter as tk
from tkinter import font, ttk

import customtkinter as ctk

from language import translate
from looks import Look, catalog
from selection_menu import SelectionMenu
from slider_gestures import bind_slider_wheel, bind_slider_reset
from theme import BORDER, DISABLED, GOLD, GOLD_LIGHT, PANEL_BG, SECONDARY_BG, TEXT, attach_tooltip, checkbox, set_control_state

SECTIONS = {
    'film': 'Farbfilm & Kameralooks', 'monochrome': 'Schwarzweiß & Tonung',
    'cinema': 'Kino-Looks', 'night': 'Nacht & Effekte',
    'retro': 'Retro & Labor', 'mood': 'Licht & Stimmung',
}


class LookControls:
    def __init__(self, app, parent, menu_colors):
        self.app = app
        self.view = app.compare
        self.enabled = tk.BooleanVar(master=parent, value=False)
        self.keep = tk.BooleanVar(master=parent, value=False)
        self.kept_look = None
        pref = app.config.get('lut')
        pref = pref if isinstance(pref, dict) else {}
        self.first_key = next(iter(catalog()))
        self.key = tk.StringVar(master=parent, value=self.first_key)
        amount = pref.get('strength')
        self.strength = tk.DoubleVar(master=parent, value=amount if type(amount) is int and 0 <= amount <= 100 else 100)
        self.hover = None
        self.hover_menu = None
        self.held = set()
        self.release_jobs = {}
        self.used_c = False
        self.result = False
        self.available = False
        frame = self.frame = tk.Frame(parent, bg=PANEL_BG)
        frame.columnconfigure(0, weight=1)
        row = self.settings = tk.Frame(frame, bg=PANEL_BG)
        row.grid(row=0, column=0, sticky='ew')
        row.columnconfigure(2, weight=1)
        row.columnconfigure(3, weight=1)
        self.check = app.labelled(checkbox, row, 'LUT anwenden', variable=self.enabled, command=self.toggle_changed)
        self.check.grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.keep_check = app.labelled(checkbox, row, 'Beibehalten', variable=self.keep, command=self.toggle_keep)
        self.keep_check.grid(row=0, column=1, sticky='w', padx=(0, 5))
        attach_tooltip(self.keep_check, lambda: translate('LUT und Stärke für weitere Bilder übernehmen.'))
        self.menu_colors = menu_colors
        # Keep the field's minimum size independent of the selected preset.
        self.picker = tk.Frame(row, bg=PANEL_BG)
        self.picker.grid(row=0, column=2, sticky='ew', padx=(0, 6))
        self.picker.pack_propagate(False)
        self.choose = ttk.Menubutton(self.picker, style='Input.TMenubutton')
        self.choose.pack(fill='both', expand=True)
        self.menu = None
        # Use StereoFine's LUT slider widget, range and colour treatment.
        self.slider = ctk.CTkSlider(row, from_=0, to=100, width=68, number_of_steps=100,
                                    variable=self.strength, command=self.set_strength, bg_color=PANEL_BG,
                                    fg_color=BORDER, progress_color=GOLD,
                                    button_color=GOLD_LIGHT, button_hover_color=GOLD_LIGHT)
        self.slider.grid(row=0, column=3, sticky='ew')
        self.value = ctk.CTkLabel(row, width=36, height=20, fg_color=PANEL_BG, anchor='e',
                                  text_color=TEXT, font=('Segoe UI', 13))
        self.value.grid(row=0, column=4, padx=(2, 6))
        self.save_button = app.labelled(ttk.Button, frame, 'Variante mit LUT erstellen',
                                       command=app.create_lut_variant, style='Input.TButton')
        self.save_button.grid(row=0, column=1, sticky='e')
        frame.bind('<Configure>', self.fit_actions)
        bind_slider_wheel(self.slider, self.can_edit_strength, lambda ticks: self.step(5 * ticks))
        bind_slider_reset(self.slider, self.can_edit_strength, lambda: self.set_strength(100))
        app.window.bind('<KeyPress>', self.key_press, add='+')
        app.window.bind('<KeyRelease>', self.key_release, add='+')
        app.window.bind('<FocusOut>', self.check_focus, add='+')
        self.localize()

    def localize(self):
        previous = self.menu
        self.menu = SelectionMenu(self.choose, self.key, **self.menu_colors, postcommand=self.begin_menu)
        self.menu.bind('<Unmap>', self.end_menu)
        groups = {}
        section = 'film'
        for key, entry in catalog().items():
            section = entry.get('section', section)
            groups.setdefault(section, []).append((key, entry))
        for section, options in groups.items():
            group = tk.Menu(self.menu, **self.menu_colors)
            for key, entry in options:
                self.menu.add_choice(self.label(entry), key, lambda k=key: self.select(k), menu=group)
            group.bind('<<MenuSelect>>', lambda event, g=group, opts=options: self.highlight(g, opts))
            group.bind('<Unmap>', lambda event, g=group: self.end_menu(event, g))
            self.menu.add_category(translate(SECTIONS[section]), group)
        self.menu.update_marks()
        self.choose.configure(menu=self.menu)
        if previous is not None:
            previous.destroy()
        picker_font = font.Font(self.choose, font=ttk.Style(self.choose).lookup(self.choose.cget('style'), 'font'))
        longest = max((self.label(entry) for entry in catalog().values()), key=picker_font.measure)
        self.choose.configure(text=longest)
        self.picker.configure(width=self.choose.winfo_reqwidth(), height=self.choose.winfo_reqheight())
        self.refresh()
        self.frame.after_idle(self.fit_actions)

    def fit_actions(self, _event=None):
        needed = self.settings.winfo_reqwidth() + self.save_button.winfo_reqwidth()
        compact = self.frame.winfo_width() < needed
        if self.save_button.grid_info()['row'] != int(compact):
            self.save_button.grid_configure(row=int(compact), column=0 if compact else 1,
                                            columnspan=2 if compact else 1, pady=(4 if compact else 0, 0))

    def label(self, entry):
        return entry.get('name_en', entry['name']) if self.app.language == 'en' else entry['name']

    def look(self):
        return Look(self.key.get(), round(self.strength.get()))

    def armed(self):
        return self.look() if self.enabled.get() and round(self.strength.get()) else None

    def update_image(self, has_input, has_result, *, showing_result, busy):
        self.result = has_result
        self.available = has_input and not busy and (has_result or not showing_result)
        self.refresh()

    def clear(self, *, reset_armed=True):
        self.hover = self.hover_menu = None
        self.cancel_keys()
        if reset_armed:
            self.enabled.set(False)

    def load_input(self, *, use_kept):
        self.key.set(self.first_key)
        self.set_look(self.kept_look if use_kept else None)

    def set_look(self, look):
        self.clear()
        if look is not None:
            self.key.set(look.key)
            self.strength.set(look.strength)
            self.enabled.set(True)

    def toggle_keep(self):
        self.kept_look = self.look() if self.keep.get() else None

    def update_kept_look(self):
        if self.keep.get() and not self.result:
            self.kept_look = self.look()

    def toggle_changed(self):
        self.hover = self.hover_menu = None
        self.refresh()

    def begin_menu(self):
        self.hover = self.hover_menu = None

    def highlight(self, group, options):
        active = group.index('active')
        self.hover_menu = group
        self.hover = options[active][0] if active is not None else None
        self.refresh()

    def end_menu(self, _event, group=None):
        if group is None or self.hover_menu is group:
            self.hover = self.hover_menu = None
            self.refresh()

    def select(self, key):
        if key != self.key.get():
            self.key.set(key)
        self.hover = self.hover_menu = None
        self.update_kept_look()
        self.refresh()

    def set_strength(self, value):
        if self.can_edit_strength():
            self.strength.set(round(float(value)))
            self.update_kept_look()
            self.refresh()

    def step(self, amount):
        self.set_strength(max(0, min(100, round(self.strength.get()) + amount)))

    def can_edit_strength(self):
        return self.available and self.enabled.get()

    @staticmethod
    def is_text_input(widget):
        return isinstance(widget, (tk.Text, tk.Entry, ttk.Entry, ttk.Combobox, ttk.Spinbox, tk.Spinbox))

    def check_focus(self, _event=None):
        if self.held:
            self.view.after_idle(self.cancel_keys_if_unfocused)

    def cancel_keys_if_unfocused(self):
        focus = self.app.window.focus_get()
        if focus is None or focus.winfo_toplevel() is not self.app.window or self.is_text_input(focus):
            self.cancel_keys()

    def key_press(self, event):
        widget = event.widget
        if self.is_text_input(widget) or isinstance(widget, tk.Menu):
            return None
        key = event.keysym.lower()
        if pending := self.release_jobs.pop(key, None):
            self.view.after_cancel(pending)
        if event.state & 0x0c:  # Ctrl / Alt combinations belong to the application.
            return None
        if key == 'z' and self.view.before_image is not None:
            if key not in self.held:
                self.held.add(key)
                self.view.hold_detail()
            return 'break'
        if self.available and key == 'c':
            if key not in self.held:
                self.held.add(key)
                self.used_c = False
            return 'break'
        if self.available and 'c' in self.held and key in ('left', 'right', 'up', 'down'):
            self.used_c = True
            if not self.enabled.get():
                self.enabled.set(True)
            if key in ('left', 'right'):
                order = list(catalog())
                index = order.index(self.key.get()) + (1 if key == 'right' else -1)
                self.select(order[index % len(order)])
            else:
                self.step(5 if key == 'up' else -5)
            return 'break'
        if widget is self.view and key in ('left', 'right'):
            return self.view.nudge(-0.025 if key == 'left' else 0.025)
        return None

    def key_release(self, event):
        key = event.keysym.lower()
        if key not in self.held:
            return None
        if key not in self.release_jobs:
            # X11 can emit adjacent synthetic release/press events for a held key.
            self.release_jobs[key] = self.view.after(15, self.finish_release, key)
        return 'break'

    def finish_release(self, key):
        self.release_jobs.pop(key, None)
        self.held.discard(key)
        if key == 'z':
            self.view.release_detail()
        elif not self.used_c and self.available:
            self.enabled.set(not self.enabled.get())
            self.toggle_changed()

    def cancel_keys(self, _event=None):
        for job in self.release_jobs.values():
            self.view.after_cancel(job)
        self.release_jobs.clear()
        self.held.clear()
        self.view.release_detail()

    def refresh(self):
        active = self.available and self.enabled.get()
        state = 'normal' if active else 'disabled'
        set_control_state(self.check, 'normal' if self.available else 'disabled')
        set_control_state(self.keep_check, 'normal' if self.available else 'disabled')
        self.choose.configure(state=state, text=self.label(catalog()[self.key.get()]))
        self.slider.configure(state=state, progress_color=GOLD if active else BORDER,
                              button_color=GOLD_LIGHT if active else DISABLED,
                              button_hover_color=GOLD_LIGHT if active else DISABLED)
        self.value.configure(text=f'{round(self.strength.get())} %', text_color=TEXT if active else DISABLED)
        self.save_button.configure(state='normal' if active and round(self.strength.get()) else 'disabled')
        look = Look(self.hover or self.key.get(), round(self.strength.get())) if active else None
        basis = self.view.after_image if self.result else self.view.before_image
        self.view.preview_look(basis if look is not None else None, look)
        self.app.after_heading.configure(text=translate('LUT-Vorschau' if active else 'Nachher'),
                                         fg=GOLD_LIGHT if active else TEXT)


def open_controls(app):
    current = getattr(app, 'controls_help', None)
    if current is not None and current.winfo_exists():
        current.destroy()
        return 'break'
    app.controls_help = controls_dialog(app.window)
    return 'break'


# Sections stay together when the two panels stack on a narrow screen.
GUIDE_COLUMNS = (
    (
        ('Ansicht und Ergebnisse', (
            ('Trennlinie mit der linken Maustaste ziehen', 'Vorher und Nachher vergleichen'),
            ('← / →', 'Nach einem Klick ins Vorschaubild die Trennlinie verschieben'),
            ('Mausrad', 'Ansichtszoom'),
            ('Mitteltaste + Ziehen', 'Vergrößerte Ansicht verschieben'),
            ('Strg + 1', '100-%-Ansicht'),
            ('Z halten', 'Temporäre 100-%-Ansicht'),
            ('Strg + 0 / Doppelklick / Esc', 'Ansicht einpassen'),
            ('Bild auf / Bild ab', 'Vorheriges / nächstes Ergebnis'),
            ('F1', 'Bedienhilfe öffnen oder schließen'),
        )),
        ('LUT', (
            ('C', 'LUT ein-/ausschalten'),
            ('C halten + ← / →', 'Durch Looks blättern'),
            ('C halten + ↑ / ↓', 'LUT-Stärke um 5 Prozentpunkte ändern'),
            ('Beibehalten', 'LUT und Stärke für das nächste Eingabebild übernehmen'),
        )),
        ('Bildbearbeitungsregler', (
            ('Umschalt + Mausrad', 'Bildbearbeitungsregler über Schiene oder Griff verstellen'),
            ('Doppelklick', 'Bildbearbeitungsregler auf Standardwert zurücksetzen'),
        )),
    ),
    (
        ('Ausschnitt', (
            ('Original (Standard)', 'Seitenverhältnis des Eingabebildes beibehalten'),
            ('Mit der linken Maustaste im Rahmen ziehen', 'Ausschnitt verschieben'),
            ('An einem Griff ziehen', 'Größe des Ausschnitts ändern'),
            ('Pfeiltasten', 'Ausschnitt um 1 px verschieben'),
            ('Strg + Pfeiltasten', 'Ausschnitt um 5 px verschieben'),
            ('Ränder einpassen', 'Leere Bildränder aus dem Ausschnitt nehmen'),
            ('Enter / Esc', 'Im Bild: übernehmen / verwerfen'),
        )),
        ('Horizont und Perspektive', (
            ('Umschalt + ← / →', 'Horizont um 0,1° nach links / rechts drehen'),
            ('Umschalt + ↑ / ↓', 'Obere / untere Bildkante verbreitern'),
            ('Zahlenfeld + Enter', 'Eingegebenen Wert anwenden'),
            ('Raster', '3 × 3 beim Beschneiden, 9 × 9 beim Ausrichten'),
        )),
    ),
)


class GuidePanels(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=PANEL_BG)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=PANEL_BG, highlightthickness=0, width=1, height=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.body = tk.Frame(self.canvas, bg=PANEL_BG)
        self.window_item = self.canvas.create_window(0, 0, anchor='nw', window=self.body)
        self.bold = font.nametofont('TkDefaultFont').copy()
        self.bold.configure(weight='bold')
        self.unit = self.bold.measure('0')
        self.panels = []
        self.labels = []
        self.rows = []
        self.columns = 0
        self.pending_scroll = None
        for sections in GUIDE_COLUMNS:
            panel = tk.Frame(self.body, bg=SECONDARY_BG, padx=10, pady=6)
            panel.columnconfigure(1, weight=1)
            self.panels.append(panel)
            row = 0
            for heading, entries in sections:
                if row:
                    tk.Frame(panel, bg=BORDER, height=1).grid(row=row, column=0, columnspan=2,
                                                               sticky='ew', pady=(7, 6))
                    row += 1
                title = tk.Label(panel, bg=SECONDARY_BG, fg=TEXT, font=self.bold)
                title.grid(row=row, column=0, columnspan=2, sticky='w', pady=(1, 4))
                self.labels.append((title, heading))
                row += 1
                for key, action in entries:
                    shortcut = tk.Label(panel, bg=SECONDARY_BG, fg=GOLD_LIGHT, font=self.bold, justify='right',
                                        padx=0, borderwidth=0, highlightthickness=0)
                    shortcut.grid(row=row, column=0, sticky='ne', padx=(0, 9))
                    description = tk.Label(panel, bg=SECONDARY_BG, fg=TEXT, justify='left',
                                           padx=0, borderwidth=0, highlightthickness=0)
                    description.grid(row=row, column=1, sticky='nw')
                    self.labels.extend(((shortcut, key), (description, action)))
                    self.rows.append((shortcut, description))
                    row += 1
                if heading == 'Ausschnitt':
                    note = tk.Label(panel, bg=SECONDARY_BG, fg=TEXT, justify='left',
                                    padx=0, borderwidth=0, highlightthickness=0)
                    note.grid(row=row, column=0, columnspan=2, sticky='w', pady=(4, 0))
                    self.labels.append((note, 'Pfeiltasten wirken, wenn das Beschnittbild den Fokus hat.'))
                    self.focus_note = note
                    row += 1
        self.canvas.bind('<Configure>', lambda event: self.arrange(event.width, self.winfo_width()))
        self.body.bind('<Configure>', self.schedule_scroll)
        parent.bind('<MouseWheel>', self.scroll)
        parent.bind('<Button-4>', lambda event: self.scroll(event, -1))
        parent.bind('<Button-5>', lambda event: self.scroll(event, 1))

    def arrange(self, canvas_width, viewport_width):
        # Use the full viewport to keep the breakpoint stable when the scrollbar appears.
        columns = 2 if viewport_width >= max(760, 84 * self.unit) else 1
        if self.columns != columns:
            self.columns = columns
            for index, panel in enumerate(self.panels):
                panel.grid(row=index // columns, column=index % columns, sticky='nsew',
                           padx=((4, 0) if index else (0, 4)) if columns == 2 else 0,
                           pady=(8 if index and columns == 1 else 0, 0))
            for col in range(2):
                self.body.columnconfigure(col, weight=int(col < columns),
                                          uniform='guide' if col < columns else '')
        width = max(60, (canvas_width - 8 * (columns - 1)) // columns - 20)
        keys = min(19 * self.unit, int(width * .40))
        self.focus_note.configure(wraplength=width - 4)
        for key, action in self.rows:
            key.configure(wraplength=max(24, keys - 12))
            action.configure(wraplength=max(30, width - keys - 5))
        self.canvas.itemconfigure(self.window_item, width=canvas_width)
        self.schedule_scroll()

    def schedule_scroll(self, _event=None):
        if self.pending_scroll is None:
            self.pending_scroll = self.after_idle(self.update_scroll)

    def update_scroll(self):
        self.pending_scroll = None
        self.canvas.configure(scrollregion=self.canvas.bbox(self.window_item))
        needed = self.body.winfo_reqheight() > self.canvas.winfo_height()
        if needed and not self.scrollbar.winfo_manager():
            self.scrollbar.grid(row=0, column=1, sticky='ns')
        elif not needed and self.scrollbar.winfo_manager():
            self.scrollbar.grid_remove()
            self.canvas.yview_moveto(0)

    def scroll(self, event, steps=None):
        if not self.scrollbar.winfo_ismapped():
            return
        if steps is None:
            steps = (event.delta < 0) - (event.delta > 0)
        self.canvas.yview_scroll(steps, 'units')
        return 'break'


def controls_dialog(parent):
    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.transient(parent)
    dialog.configure(bg=PANEL_BG)
    heading_font = font.nametofont('TkDefaultFont').copy()
    heading_font.configure(size=17, weight='bold')
    dialog.heading_font = heading_font
    heading = tk.Label(dialog, fg=GOLD_LIGHT, bg=PANEL_BG, font=heading_font)
    heading.pack(anchor='w', padx=16, pady=(10, 6))
    close_button = ttk.Button(dialog, command=dialog.destroy)
    close_button.pack(side='bottom', pady=(6, 10))
    panels = GuidePanels(dialog)
    panels.pack(fill='both', expand=True, padx=12)

    def localize(_event=None):
        title = translate('Bedienhilfe')
        dialog.title(title)
        heading.configure(text=title)
        for label, text in panels.labels:
            label.configure(text=translate(text))
        close_button.configure(text=translate('Schließen'))

    dialog.bind('<<LanguageChanged>>', localize)
    dialog.bind('<Escape>', lambda _event: dialog.destroy())
    dialog.bind('<F1>', lambda _event: dialog.destroy())
    localize()
    width = min(max(900, 110 * panels.unit), dialog.winfo_screenwidth() - 48)
    height_limit = max(220, dialog.winfo_screenheight() - 88)
    dialog.minsize(min(400, width), min(250, height_limit))
    dialog.geometry(f'{width}x{height_limit}')
    dialog.update_idletasks()
    # A withdrawn toplevel may not have laid out its canvas yet.
    panels.arrange(width - 24, width - 24)
    dialog.update_idletasks()
    height = min(height_limit, panels.body.winfo_reqheight() + heading.winfo_reqheight()
                 + close_button.winfo_reqheight() + 38)
    x = max(0, min(dialog.winfo_screenwidth() - width, parent.winfo_rootx() + (parent.winfo_width() - width) // 2))
    y = max(0, min(dialog.winfo_screenheight() - height - 48, parent.winfo_rooty() + (parent.winfo_height() - height) // 2))
    dialog.geometry(f'{width}x{height}+{x}+{y}')
    dialog.deiconify()
    dialog.focus_set()
    return dialog
