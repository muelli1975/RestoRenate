"""Transient LUT preview and output controls for the comparison pane."""
import tkinter as tk
from tkinter import font, ttk

import customtkinter as ctk

from language import translate
from looks import Look, catalog
from selection_menu import SelectionMenu
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
        self.wheel_remainder = 0
        self.resetting_slider = False
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
        self.slider.bind('<Double-Button-1>', self.begin_slider_reset)
        self.slider.bind('<ButtonRelease-1>', self.finish_slider_reset)
        self.slider.bind('<MouseWheel>', self.wheel)
        self.slider.bind('<Button-4>', lambda event: self.wheel(event, 1))
        self.slider.bind('<Button-5>', lambda event: self.wheel(event, -1))
        self.slider.bind('<Leave>', self.clear_wheel, add='+')
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
        if self.available and self.enabled.get():
            self.strength.set(round(float(value)))
            self.update_kept_look()
            self.refresh()

    def step(self, amount):
        self.set_strength(max(0, min(100, round(self.strength.get()) + amount)))

    def begin_slider_reset(self, _event):
        self.resetting_slider = self.available and self.enabled.get()
        if self.resetting_slider:
            return 'break'

    def finish_slider_reset(self, _event):
        if self.resetting_slider:
            self.resetting_slider = False
            self.set_strength(100)
            return 'break'

    def clear_wheel(self, _event=None):
        self.wheel_remainder = 0

    def wheel(self, event, ticks=None):
        if not event.state & 0x0001 or not self.available or not self.enabled.get():
            self.clear_wheel()
            return None
        if ticks is None:
            delta = event.delta
            if self.slider.tk.call('tk', 'windowingsystem') == 'win32':
                delta += self.wheel_remainder
                ticks = int(delta / 120)
                self.wheel_remainder = delta - 120 * ticks
            else:
                ticks = (delta > 0) - (delta < 0)
        if ticks:
            self.step(5 * ticks)
        return 'break'

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
    dialog = app.controls_help = tk.Toplevel(app.window)
    dialog.transient(app.window)
    dialog.configure(bg=PANEL_BG)
    dialog.resizable(False, False)
    body = tk.Frame(dialog, bg=SECONDARY_BG, padx=16, pady=12, highlightthickness=1, highlightbackground=BORDER)
    body.pack(padx=12, pady=12)
    shortcuts = (
        ('C', '', 'LUT ein / aus'),
        ('C halten', ' + ← / →', 'Look zurück / vor'),
        ('C halten', ' + ↑ / ↓', 'LUT-Stärke ändern'),
        ('Umschalt + Mausrad', '', 'LUT-Stärke ändern'),
        ('Doppelklick auf den Regler', '', 'Auf 100 % zurücksetzen'),
        ('Z halten', '', '100-%-Ansicht halten'),
        ('Bild↑ / Bild↓', '', 'Vorheriges / nächstes Ergebnis'),
        ('F1', '', 'Bedienhilfe öffnen'),
    )
    rows = []
    for row in range(len(shortcuts)):
        key_label = tk.Label(body, fg=GOLD_LIGHT, bg=SECONDARY_BG)
        key_label.grid(row=row, column=0, sticky='w', padx=(0, 14), pady=2)
        description_label = tk.Label(body, fg=TEXT, bg=SECONDARY_BG)
        description_label.grid(row=row, column=1, sticky='w', pady=2)
        rows.append((key_label, description_label))
    hint = tk.Label(body, fg=TEXT, bg=SECONDARY_BG, justify='left', wraplength=380)
    hint.grid(row=len(shortcuts), column=0, columnspan=2, sticky='w', pady=(8, 0))
    close_button = ttk.Button(dialog, command=dialog.destroy)
    close_button.pack(pady=(0, 12))

    def localize(_event=None):
        dialog.title(translate('Bedienhilfe'))
        for (key_label, description_label), (key, suffix, description) in zip(rows, shortcuts):
            key_label.configure(text=translate(key) + suffix)
            description_label.configure(text=translate(description))
        hint.configure(text=translate(
            '„Beibehalten“ schaltet die LUT mit derselben Stärke beim Öffnen des nächsten Eingabebildes wieder ein.'
        ))
        close_button.configure(text=translate('Schließen'))

    dialog.bind('<<LanguageChanged>>', localize)
    localize()
    dialog.bind('<Escape>', lambda _event: dialog.destroy())
    dialog.bind('<F1>', lambda _event: dialog.destroy())
    dialog.focus_set()
    return 'break'
