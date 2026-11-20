"""Centered geometry controls following StereoFine’s exposure slider."""

import math
import tkinter as tk

import customtkinter as ctk

from language import translate
from theme import APP_BG, BORDER, GOLD, GOLD_LIGHT, SECONDARY_BG, TEXT


SHIFT_MASK = 0x0001


class CenteredSlider(ctk.CTkSlider):
    """Colour the track from the neutral midpoint to the current grip."""

    def _draw(self, no_color_updates=False):
        super()._draw(no_color_updates)
        tag = 'centered_progress'
        canvas = self._canvas
        if self.cget('state') == 'disabled' or self.get() == 0:
            canvas.itemconfigure(tag, state='hidden')
            return
        grip = canvas.bbox('slider_parts')
        rail = canvas.bbox('inner_parts')
        if grip is None or rail is None:
            return
        midpoint = (rail[0] + rail[2]) / 2
        grip_center = (grip[0] + grip[2]) / 2
        coords = (min(midpoint, grip_center), max(0, rail[1]),
                  max(midpoint, grip_center), min(self._apply_widget_scaling(self._current_height), rail[3]))
        if canvas.find_withtag(tag):
            canvas.coords(tag, *coords)
            canvas.itemconfigure(tag, state='normal')
        else:
            canvas.create_rectangle(*coords, fill=GOLD, width=0, state='normal', tags=(tag,))
        canvas.tag_lower(tag, 'slider_parts')


def bind_slider_wheel(slider, enabled, step):
    windows = slider.tk.call('tk', 'windowingsystem') == 'win32'
    remainder = 0

    def scroll(event, ticks=None):
        nonlocal remainder
        if not event.state & SHIFT_MASK or not enabled():
            remainder = 0
            return None
        if ticks is None:
            delta = event.delta
            if windows:
                delta += remainder
                ticks = int(delta / 120)
                remainder = delta - 120 * ticks
            else:
                ticks = (delta > 0) - (delta < 0)
        if ticks:
            step(ticks)
        return 'break'

    def reset(_event):
        nonlocal remainder
        remainder = 0

    canvas = slider._canvas
    canvas.bind('<MouseWheel>', scroll)
    canvas.bind('<Button-4>', lambda event: scroll(event, 1))
    canvas.bind('<Button-5>', lambda event: scroll(event, -1))
    canvas.bind('<Leave>', reset, add='+')


def bind_slider_reset(slider, enabled, reset):
    resetting = False

    def double_click(_event):
        nonlocal resetting
        resetting = enabled()
        if resetting:
            return 'break'

    def release(_event):
        nonlocal resetting
        if resetting:
            resetting = False
            if enabled():
                reset()
            return 'break'

    # Motion before the second release can still change the slider value.
    slider.bind('<Double-Button-1>', double_click)
    slider.bind('<ButtonRelease-1>', release)


class AlignmentSlider(tk.Frame):
    """Signed adjustment with a live preview and locale-aware numeric entry."""

    def __init__(self, parent, label, variable, limit, step, command, focus_preview):
        super().__init__(parent, bg=APP_BG)
        self.variable = variable
        self.limit = limit
        self.step = step
        self.command = command
        self.focus_preview = focus_preview
        self.caption = tk.Label(self, text=translate(label), bg=APP_BG, fg=TEXT)
        self.caption.pack(anchor='w')
        self.value = tk.StringVar(self)
        self.entry = ctk.CTkEntry(self, width=60, height=25, textvariable=self.value, justify='right',
                                  fg_color=SECONDARY_BG, bg_color=APP_BG, border_color=BORDER,
                                  text_color=TEXT, corner_radius=8, font=('Segoe UI', 12))
        self.entry.pack(side='right')
        self.slider = CenteredSlider(self, from_=-limit, to=limit, number_of_steps=round(2 * limit / step),
                                     variable=variable, command=self.drag, width=68, bg_color=APP_BG,
                                     fg_color=BORDER, progress_color=BORDER, button_color=GOLD_LIGHT,
                                     button_hover_color=GOLD_LIGHT)
        self.slider.pack(side='left', fill='x', expand=True, padx=(0, 5))
        bind_slider_wheel(self.slider, self.enabled, lambda ticks: self.set_value(variable.get() + step * ticks))
        bind_slider_reset(self.slider, self.enabled, lambda: self.set_value(0))
        self.entry.bind('<FocusOut>', lambda event: self.commit())
        for key in ('Return', 'KP_Enter'):
            self.entry.bind(f'<{key}>', self.accept)
        self.entry.bind('<Escape>', self.revert)
        for key, direction in (('Up', 1), ('Down', -1)):
            self.entry.bind(f'<{key}>', lambda event, direction=direction: self.commit(direction))
        variable.trace_add('write', self.sync)
        self.sync()

    def enabled(self):
        return self.slider.cget('state') == 'normal'

    def formatted_value(self):
        current = self.variable.get()
        if self.step == 1:
            return f'{current:+d}'
        return f'{current:+.1f}°'.replace('.', translate(','))

    def sync(self, *_args):
        self.value.set(self.formatted_value())

    def set_value(self, value):
        bounded = max(-self.limit, min(self.limit, value))
        self.variable.set(round(bounded) if self.step == 1 else round(bounded, 1))
        self.command()

    def drag(self, _value):
        self.focus_preview()
        self.command()

    def commit(self, direction=0):
        try:
            value = float(self.value.get().strip().removesuffix('°').replace(',', '.'))
            if not math.isfinite(value):
                raise ValueError
        except ValueError:
            self.sync()
        else:
            self.set_value(value + direction * self.step)
        return 'break'

    def accept(self, _event):
        self.commit()
        self.focus_preview()
        return 'break'

    def revert(self, _event):
        self.sync()
        self.focus_preview()
        return 'break'

