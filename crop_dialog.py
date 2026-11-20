"""Modal editor for non-destructive crop selections."""
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageEnhance, ImageTk

from alignment_slider import AlignmentSlider
from crop import ASPECTS, Alignment, CropRegion, box_size, clamp, fit_aspect, move_box, parse_aspect, resize_box
from imaging import align_photo, open_photo
from language import translate
from look_controls import controls_dialog
from theme import APP_BG, GOLD_LIGHT, MUTED

CORNERS = ((-1, -1), (1, -1), (-1, 1), (1, 1))
EDGES = ((0, -1), (-1, 0), (1, 0), (0, 1))
CURSORS = {
    (-1, -1): 'size_nw_se', (1, 1): 'size_nw_se',
    (1, -1): 'size_ne_sw', (-1, 1): 'size_ne_sw',
    (-1, 0): 'sb_h_double_arrow', (1, 0): 'sb_h_double_arrow',
    (0, -1): 'sb_v_double_arrow', (0, 1): 'sb_v_double_arrow',
}


class CropDialog(tk.Toplevel):
    def __init__(self, parent, sources, crops, selected, *, rotations=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(translate('Ausrichten und beschneiden'))
        self.configure(bg=APP_BG)
        self.minsize(520, 410)
        width = min(1020, self.winfo_screenwidth() - 80)
        height = min(780, self.winfo_screenheight() - 100)
        self.geometry(f'{width}x{height}')
        self.sources = tuple(sources)
        self.crops = dict(crops)
        self.rotations = rotations or {}
        self.result = None
        self.image = None
        self.index = None
        self.box = None
        self.aspect = None
        self.drag = None
        self.display = None
        self.display_box = None
        self.preview_base = None
        self.alignment = Alignment()
        self.redraw_job = None

        toolbar = tk.Frame(self, bg=APP_BG, padx=12, pady=10)
        toolbar.pack(fill='x')
        if len(self.sources) > 1:
            self.source_choice = ttk.Combobox(toolbar, state='readonly', width=1,
                                             values=tuple(source.name for source in self.sources))
            self.source_choice.pack(side='left', fill='x', expand=True, padx=(0, 12))
            self.source_choice.bind('<<ComboboxSelected>>', self.choose_source)
        else:
            self.source_choice = None
        tk.Label(toolbar, text=translate('Seitenverhältnis'), bg=APP_BG, fg=MUTED).pack(side='left', padx=(0, 6))
        self.aspect_choice = ttk.Combobox(toolbar, state='readonly', width=19)
        self.aspect_choice.pack(side='left')
        self.aspect_choice.bind('<<ComboboxSelected>>', self.choose_aspect)
        self.custom_entry = ttk.Entry(toolbar, width=10)
        self.custom_entry.bind('<Return>', self.enter_custom_aspect)
        self.custom_entry.bind('<FocusOut>', lambda event: self.commit_custom_aspect(report_error=False))

        alignment_bar = tk.Frame(self, bg=APP_BG, padx=12)
        alignment_bar.pack(fill='x')
        self.angle = tk.DoubleVar(self, 0.)
        self.vertical = tk.IntVar(self, 0)
        self.horizontal = tk.IntVar(self, 0)
        def slider(label, variable, limit, step):
            control = AlignmentSlider(alignment_bar, label, variable, limit, step, self.change_alignment,
                                      lambda: self.canvas.focus_set())
            control.pack(side='left', fill='x', expand=True, padx=(0, 10))
            return control

        self.angle_slider = slider('Horizont', self.angle, 5, 0.1)
        self.vertical_slider = slider('Perspektive', self.vertical, 20, 1)
        # A quarter turn takes an existing vertical correction onto the horizontal axis.
        self.side_slider = slider('Horizontale Perspektive', self.horizontal, 20, 1)
        self.side_slider.pack_forget()
        self.fit_button = ttk.Button(alignment_bar, text=translate('Ränder einpassen'), command=self.fit_edges)
        self.fit_button.pack(side='right')

        self.canvas = tk.Canvas(self, bg=APP_BG, highlightthickness=0, takefocus=True)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', self.draw_image)
        self.canvas.bind('<ButtonPress-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.update_drag)
        self.canvas.bind('<ButtonRelease-1>', self.finish_drag)
        self.canvas.bind('<Motion>', self.hover)
        for key, dx, dy in (('Left', -1, 0), ('Right', 1, 0), ('Up', 0, -1), ('Down', 0, 1)):
            self.canvas.bind(f'<{key}>', lambda event, dx=dx, dy=dy: self.nudge(dx, dy))
            self.canvas.bind(f'<Shift-{key}>', lambda event, dx=dx, dy=dy: self.step_alignment(dx, -dy))

        footer = tk.Frame(self, bg=APP_BG, padx=12, pady=10)
        footer.pack(fill='x')
        self.dimensions = tk.StringVar(self)
        tk.Label(footer, textvariable=self.dimensions, bg=APP_BG, fg=MUTED).pack(side='left')
        self.apply_button = ttk.Button(footer, text=translate('Übernehmen'), style='Primary.TButton',
                                       command=self.apply_crop)
        self.apply_button.pack(side='right')
        ttk.Button(footer, text=translate('Abbrechen'), command=self.destroy).pack(side='right', padx=6)
        self.reset_button = ttk.Button(footer, text=translate('Zurücksetzen'), command=self.reset_crop)
        self.reset_button.pack(side='right')

        self.bind('<F1>', self.open_help)
        self.bind('<Escape>', lambda event: self.destroy())
        self.bind('<Return>', lambda event: self.apply_crop())
        self.load_source(self.sources.index(selected))

    def load_source(self, index):
        try:
            source = self.sources[index]
            image, _ = open_photo(source, rotation=self.rotations.get(source, 0))
        except (OSError, ValueError, SyntaxError) as exc:
            if self.source_choice is not None:
                self.source_choice.current(index if self.index is None else self.index)
            if self.image is None:
                self.apply_button.configure(state='disabled')
                self.reset_button.configure(state='disabled')
                self.aspect_choice.configure(state='disabled')
            messagebox.showerror(translate('Ausrichten und beschneiden'), str(exc), parent=self)
            return
        self.store_crop()
        if self.image is not None:
            self.image.close()
        self.index, self.image = index, image
        self.preview_base = None
        region = self.crops.get(self.sources[index])
        self.aspects = (None, *(aspect for aspect in ASPECTS
                               if aspect[0] <= image.width and aspect[1] <= image.height))
        labels = tuple(translate('Frei') if aspect is None else f'{aspect[0]}:{aspect[1]}' for aspect in self.aspects)
        self.aspect_choice.configure(
            values=(*labels, translate('Benutzerdefiniert …')),
            state='readonly',
        )
        self.apply_button.configure(state='normal')
        self.reset_button.configure(state='normal')
        if self.source_choice is not None:
            self.source_choice.current(index)
        if region and region.original_size == image.size:
            self.box, self.aspect = region.box, region.aspect
        else:
            self.box, self.aspect = (0, 0, *image.size), None
        self.alignment = region.alignment if region and region.original_size == image.size else Alignment()
        self.set_sliders()
        if self.aspect in self.aspects:
            self.aspect_choice.current(self.aspects.index(self.aspect))
            self.custom_entry.pack_forget()
        else:
            self.aspect_choice.current(len(self.aspects))
            self.show_custom_aspect()
        self.drag = None
        self.draw_image()

    def choose_source(self, _event):
        index = self.source_choice.current()
        if index == self.index:
            return
        if self.commit_custom_aspect():
            self.load_source(index)
        else:
            self.source_choice.current(self.index)

    def store_crop(self):
        if self.image is None:
            return
        for control in (self.angle_slider, self.vertical_slider, self.side_slider):
            if control.value.get() != control.formatted_value():
                control.commit()
        source = self.sources[self.index]
        if self.box == (0, 0, *self.image.size) and self.alignment == Alignment():
            self.crops.pop(source, None)
        else:
            self.crops[source] = CropRegion(self.image.size, self.box, self.aspect, self.alignment)

    def choose_aspect(self, _event):
        index = self.aspect_choice.current()
        if index == len(self.aspects):
            self.show_custom_aspect()
            self.commit_custom_aspect()
            self.custom_entry.focus_set()
            self.custom_entry.select_range(0, 'end')
            return
        self.custom_entry.pack_forget()
        self.aspect = self.aspects[index]
        self.drag = None
        if self.aspect:
            self.box = fit_aspect(self.box, self.image.size, self.aspect)
        self.draw_selection()

    def show_custom_aspect(self):
        width, height = self.aspect or box_size(self.box)
        self.custom_entry.delete(0, 'end')
        self.custom_entry.insert(0, f'{width}:{height}')
        self.custom_entry.pack(side='left', padx=(6, 0))

    def commit_custom_aspect(self, *, report_error=True):
        if self.image is None or self.aspect_choice.current() != len(self.aspects):
            return True
        try:
            aspect = parse_aspect(self.custom_entry.get(), self.image.size)
        except ValueError as exc:
            if report_error:
                messagebox.showerror(translate('Seitenverhältnis'), translate(str(exc)), parent=self)
                self.custom_entry.focus_set()
            return False
        if aspect != self.aspect:
            self.aspect = aspect
            self.drag = None
            self.box = fit_aspect(self.box, self.image.size, aspect)
            self.draw_selection()
        return True

    def enter_custom_aspect(self, _event):
        if self.commit_custom_aspect():
            self.canvas.focus_set()
        return 'break'

    def open_help(self, _event):
        help_window = controls_dialog(self)
        help_window.wait_visibility()
        help_window.grab_set()
        self.wait_window(help_window)
        if self.winfo_exists():
            self.grab_set()
            self.canvas.focus_set()
        return 'break'

    def step_alignment(self, roll, perspective):
        self.angle.set(clamp(round(self.angle.get() + 0.1 * roll, 1), -5, 5))
        self.vertical.set(clamp(self.vertical.get() + perspective, -20, 20))
        self.change_alignment()
        return 'break'

    def set_sliders(self):
        # The controls express forward corrections. Pillow stores the inverse mapping.
        self.angle.set(-self.alignment.angle)
        self.vertical.set(-self.alignment.vertical)
        self.horizontal.set(-self.alignment.horizontal)
        if self.alignment.horizontal:
            self.side_slider.pack(side='left', fill='x', expand=True, before=self.fit_button, padx=(0, 10))
        else:
            self.side_slider.pack_forget()

    def change_alignment(self, _value=None):
        if self.image is None:
            return
        updated = Alignment(-round(self.angle.get(), 1), -self.vertical.get(), -self.horizontal.get())
        if updated == self.alignment:
            return
        full = (0, 0, *self.image.size)
        if self.aspect is None and self.box == self.alignment.fit_box(self.image.size, full):
            self.box = updated.fit_box(self.image.size, full)
        self.alignment = updated
        if self.redraw_job is None:
            self.redraw_job = self.after_idle(self.draw_image)

    def fit_edges(self):
        if self.image is not None:
            self.box = self.alignment.fit_box(self.image.size, self.box)
            self.draw_selection()

    def reset_crop(self):
        if self.image is None:
            return
        self.aspect_choice.current(0)
        self.custom_entry.pack_forget()
        self.aspect = None
        self.drag = None
        self.box = (0, 0, *self.image.size)
        self.alignment = Alignment()
        self.set_sliders()
        self.draw_image()

    def apply_crop(self):
        if self.image is not None and self.commit_custom_aspect():
            self.store_crop()
            self.result = self.sources[self.index], self.crops
            self.destroy()

    def destroy(self):
        if self.redraw_job is not None:
            self.after_cancel(self.redraw_job)
            self.redraw_job = None
        if self.image is not None:
            self.image.close()
        super().destroy()

    def draw_image(self, _event=None):
        if self.redraw_job is not None:
            self.after_cancel(self.redraw_job)
            self.redraw_job = None
        if self.image is None:
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if min(width, height) < 25:
            return
        scale = min((width - 24) / self.image.width, (height - 24) / self.image.height)
        dw, dh = (max(1, round(length * scale)) for length in self.image.size)
        x, y = (width - dw) // 2, (height - dh) // 2
        self.display_box = x, y, dw, dh
        if self.preview_base is None or self.preview_base.size != (dw, dh):
            self.preview_base = self.image.resize((dw, dh), Image.Resampling.LANCZOS, reducing_gap=3)
        self.display = (self.preview_base if self.alignment == Alignment()
                        else align_photo(self.preview_base, self.alignment))
        dark = ImageEnhance.Brightness(self.display).enhance(0.38)
        self.canvas.delete('all')
        self.background_photo = ImageTk.PhotoImage(dark, master=self.canvas)
        self.canvas.create_image(x, y, image=self.background_photo, anchor='nw')
        self.draw_selection()

    def canvas_box(self):
        x, y, width, height = self.display_box
        left, top, right, bottom = self.box
        left = min(width - 1, round(left * width / self.image.width))
        top = min(height - 1, round(top * height / self.image.height))
        right = max(left + 1, round(right * width / self.image.width))
        bottom = max(top + 1, round(bottom * height / self.image.height))
        return x + left, y + top, x + right, y + bottom

    def handles(self, box):
        left, top, right, bottom = box
        xs = {-1: left, 0: (left + right) / 2, 1: right}
        ys = {-1: top, 0: (top + bottom) / 2, 1: bottom}
        for handle in CORNERS if self.aspect else (*CORNERS, *EDGES):
            yield handle, (xs[handle[0]], ys[handle[1]])

    def draw_selection(self):
        self.dimensions.set('{} × {} px'.format(*box_size(self.box)))
        if self.display_box is None:
            return
        x, y, _, _ = self.display_box
        left, top, right, bottom = self.canvas_box()
        selection = self.display.crop((left - x, top - y, right - x, bottom - y))
        self.canvas.delete('selection')
        self.selection_photo = ImageTk.PhotoImage(selection, master=self.canvas)
        self.canvas.create_image(left, top, image=self.selection_photo, anchor='nw', tags='selection')
        divisions = 6 if self.alignment != Alignment() else 3
        for step in range(1, divisions):
            gx = left + (right - left) * step / divisions
            gy = top + (bottom - top) * step / divisions
            for line in ((gx, top, gx, bottom), (left, gy, right, gy)):
                self.canvas.create_line(*line, fill='#202020', width=2, tags='selection')
                self.canvas.create_line(*line, fill='#f3f3f3', tags='selection')
        self.canvas.create_rectangle(left, top, right, bottom, outline=GOLD_LIGHT, width=2, tags='selection')
        for _, (hx, hy) in self.handles((left, top, right, bottom)):
            self.canvas.create_rectangle(hx - 3, hy - 3, hx + 3, hy + 3, outline='#292929',
                                         fill=GOLD_LIGHT, tags='selection')

    def image_point(self, x, y):
        left, top, width, height = self.display_box
        return (
            round((x - left) * self.image.width / width),
            round((y - top) * self.image.height / height),
        )

    def target(self, x, y):
        left, top, right, bottom = self.canvas_box()
        for handle, (hx, hy) in self.handles((left, top, right, bottom)):
            if abs(hx - x) <= 7 and abs(hy - y) <= 7:
                return handle
        if self.box != (0, 0, *self.image.size) and left <= x <= right and top <= y <= bottom:
            return 'move'
        ix, iy, width, height = self.display_box
        return 'new' if ix <= x <= ix + width and iy <= y <= iy + height else None

    def hover(self, event):
        if self.display_box is not None:
            target = self.target(event.x, event.y)
            cursor = CURSORS.get(target, {'move': 'fleur', 'new': 'crosshair'}.get(target, ''))
            if self.tk.call('tk', 'windowingsystem') != 'win32' and cursor.startswith('size_'):
                cursor = 'crosshair'
            self.canvas.configure(cursor=cursor)

    def start_drag(self, event):
        if self.display_box is None or not self.commit_custom_aspect():
            return
        target = self.target(event.x, event.y)
        if target is not None:
            self.canvas.focus_set()
            x, y = self.image_point(event.x, event.y)
            if target == 'new':
                x, y = clamp(x, 0, self.image.width), clamp(y, 0, self.image.height)
            self.drag = target, self.box, (x, y)

    def update_drag(self, event):
        if self.drag is None:
            return
        target, start, (x, y) = self.drag
        px, py = self.image_point(event.x, event.y)
        if target == 'move':
            box = move_box(start, self.image.size, px - x, py - y)
        elif target == 'new':
            if (px, py) == (x, y):
                return
            handle = (-1 if px < x else 1, -1 if py < y else 1)
            box = resize_box((x, y, x, y), self.image.size, handle, (px, py), self.aspect)
        else:
            edge_x = start[0] if target[0] < 0 else start[2]
            edge_y = start[1] if target[1] < 0 else start[3]
            box = resize_box(start, self.image.size, target, (edge_x + px - x, edge_y + py - y), self.aspect)
        if box is not None and box != self.box:
            self.box = box
            self.draw_selection()

    def finish_drag(self, event):
        self.update_drag(event)
        self.drag = None
        self.hover(event)

    def nudge(self, dx, dy):
        if self.image is not None:
            self.box = move_box(self.box, self.image.size, dx, dy)
            self.draw_selection()
        return 'break'


def edit_crops(parent, sources, crops, selected, *, rotations=None):
    dialog = CropDialog(parent, sources, crops, selected, rotations=rotations)
    if not dialog.winfo_viewable():
        dialog.wait_visibility()
    dialog.grab_set()
    dialog.canvas.focus_set()
    parent.wait_window(dialog)
    return dialog.result
