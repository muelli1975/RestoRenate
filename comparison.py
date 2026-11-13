"""Before/after canvas with a shared viewport and movable divider."""
import tkinter as tk

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from language import translate
from theme import APP_BG, MUTED, PREVIEW_BG, TEXT

HANDLE_SIZE = 44
HANDLE_RADIUS = 17


def slider_handle():
    """Draw a small neutral grip at higher resolution for smooth edges."""
    scale = 4
    size = HANDLE_SIZE * scale
    middle = size // 2
    radius = HANDLE_RADIUS * scale
    shadow = Image.new('RGBA', (size, size))
    ImageDraw.Draw(shadow).ellipse(
        (middle - radius, middle - radius + scale, middle + radius, middle + radius + scale),
        fill=(0, 0, 0, 115),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(2 * scale))
    face = Image.new('RGBA', (size, size))
    draw = ImageDraw.Draw(face)
    draw.ellipse((middle - radius, middle - radius, middle + radius, middle + radius),
                 fill='#fafafa', outline='#d7d7d7', width=scale)
    for direction in (-1, 1):
        points = [(middle + direction * x * scale, middle + y * scale) for x, y in ((4, -4), (8, 0), (4, 4))]
        draw.line(points, fill='#292929', width=2 * scale, joint='curve')
    return Image.alpha_composite(shadow, face).resize((HANDLE_SIZE, HANDLE_SIZE), Image.Resampling.LANCZOS)


def handle_position(divider, left, top, right, bottom):
    inset = min(HANDLE_SIZE // 2, (right - left) // 2)
    return max(left + inset, min(right - inset, divider)), (top + bottom) // 2


class Comparison(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=PREVIEW_BG, highlightthickness=0, takefocus=True)
        self.before_image = self.after_image = self.rendered = None
        self.handle = ImageTk.PhotoImage(slider_handle(), master=self)
        self.fraction = 0.5
        self.zoom = 1.0
        self.pan = (0.0, 0.0)
        self.drag = None
        self.pending = False
        self.fit_notice_job = None
        self.bind('<Configure>', self.schedule)
        self.bind('<Button-1>', self.divide)
        self.bind('<B1-Motion>', self.divide)
        self.bind('<Motion>', self.hover)
        self.bind('<Leave>', lambda event: self.configure(cursor=''))
        self.bind('<ButtonPress-3>', self.pan_start)
        self.bind('<B3-Motion>', self.pan_move)
        self.bind('<ButtonPress-2>', self.pan_start)
        self.bind('<B2-Motion>', self.pan_move)
        self.bind('<MouseWheel>', self.wheel)
        self.bind('<Button-4>', self.wheel)
        self.bind('<Button-5>', self.wheel)
        self.bind('<Double-Button-1>', self.fit)
        self.bind('<Left>', lambda event: self.nudge(-0.025))
        self.bind('<Right>', lambda event: self.nudge(0.025))

    def show(self, before=None, after=None, *, reset_divider=False):
        self.before_image, self.after_image = before, after
        if reset_divider:
            self.fraction = 0.5
        self.configure(cursor='')
        self.fit(notice_ms=0)

    def fit(self, event=None, *, notice_ms=2000):
        self.zoom, self.pan = 1.0, (0.0, 0.0)
        self.cancel_fit_notice()
        if notice_ms and self.before_image is not None:
            self.fit_notice_job = self.after(notice_ms, self.hide_fit_notice)
        self.schedule()

    def hide_fit_notice(self):
        self.fit_notice_job = None
        self.delete('zoom_notice')

    def cancel_fit_notice(self):
        if self.fit_notice_job is not None:
            self.after_cancel(self.fit_notice_job)
            self.hide_fit_notice()

    def schedule(self, event=None):
        if not self.pending:
            self.pending = True
            self.after_idle(self.draw)

    def display_scale(self, image):
        fit = min(self.winfo_width() / image.width, self.winfo_height() / image.height)
        return fit * self.zoom

    def geometry(self):
        image = self.after_image or self.before_image
        cw, ch = self.winfo_width(), self.winfo_height()
        scale = self.display_scale(image)
        width, height = max(1, round(image.width * scale)), max(1, round(image.height * scale))
        bound_x = max(0, (width - cw) / 2)
        bound_y = max(0, (height - ch) / 2)
        px = max(-bound_x, min(bound_x, self.pan[0]))
        py = max(-bound_y, min(bound_y, self.pan[1]))
        return round((cw - width) / 2 + px), round((ch - height) / 2 + py), width, height

    def divide(self, event):
        if self.after_image is not None:
            self.focus_set()
            x, _, width, _ = self.geometry()
            self.fraction = max(0.0, min(1.0, (event.x - x) / width))
            self.schedule()

    def hover(self, event):
        cursor = ''
        if self.after_image is not None:
            x, y, width, height = self.geometry()
            canvas_width, canvas_height = self.winfo_width(), self.winfo_height()
            left, top = max(x, 0), max(y, 0)
            right, bottom = min(x + width, canvas_width), min(y + height, canvas_height)
            divider = round(x + self.fraction * width)
            handle_x, handle_y = handle_position(divider, left, top, right, bottom)
            over_line = (left <= divider <= right and top <= event.y <= bottom and
                         abs(event.x - divider) <= HANDLE_RADIUS)
            over_handle = (abs(event.x - handle_x) <= HANDLE_RADIUS and abs(event.y - handle_y) <= HANDLE_RADIUS)
            if over_line or over_handle:
                cursor = 'sb_h_double_arrow'
        if self.cget('cursor') != cursor:
            self.configure(cursor=cursor)

    def nudge(self, delta):
        if self.after_image is not None:
            self.fraction = max(0.0, min(1.0, self.fraction + delta))
            self.schedule()
        return 'break'

    def pan_start(self, event):
        self.drag = (event.x, event.y, *self.pan)

    def pan_move(self, event):
        if self.drag and self.zoom > 1:
            x, y, px, py = self.drag
            self.pan = (px + event.x - x, py + event.y - y)
            left, top, width, height = self.geometry()
            self.pan = (left - (self.winfo_width() - width) / 2, top - (self.winfo_height() - height) / 2)
            self.schedule()

    def wheel(self, event):
        if self.before_image is None:
            return
        up = getattr(event, 'num', None) == 4 or getattr(event, 'delta', 0) > 0
        new_zoom = max(1.0, min(8.0, self.zoom * (1.25 if up else 0.8)))
        if new_zoom == self.zoom:
            return
        if new_zoom == 1.0:
            self.fit(notice_ms=1000)
            return
        self.cancel_fit_notice()
        x, y, width, height = self.geometry()
        factor = new_zoom / self.zoom
        self.zoom = new_zoom
        self.pan = (
            event.x - (event.x - x) * factor - (self.winfo_width() - width * factor) / 2,
            event.y - (event.y - y) * factor - (self.winfo_height() - height * factor) / 2,
        )
        self.schedule()

    def draw(self):
        self.pending = False
        self.delete('all')
        cw, ch = self.winfo_width(), self.winfo_height()
        if self.before_image is None:
            self.create_text(cw / 2, ch / 2, text=translate('Bild oder Ordner auswählen'),
                             fill=MUTED, font=('Segoe UI', 14))
            return
        x, y, width, height = self.geometry()
        left, top, right, bottom = max(x, 0), max(y, 0), min(x + width, cw), min(y + height, ch)
        if right <= left or bottom <= top:
            return
        raster = Image.new('RGB', (right - left, bottom - top))
        divider = round(x + self.fraction * width) if self.after_image is not None else None
        split = right if divider is None else min(right, max(left, divider))
        for photo, a, b in ((self.before_image, left, split), (self.after_image, split, right)):
            if photo is None or b <= a:
                continue
            box = ((a - x) * photo.width / width, (top - y) * photo.height / height,
                   (b - x) * photo.width / width, (bottom - y) * photo.height / height)
            raster.paste(photo.resize((b - a, bottom - top), Image.Resampling.LANCZOS, box=box), (a - left, 0))
        if divider is not None and left <= divider <= right:
            local_x = min(divider, right - 1) - left
            rule = ImageDraw.Draw(raster, 'RGBA')
            rule.line((local_x, 0, local_x, raster.height - 1), fill=(0, 0, 0, 95), width=3)
            rule.line((local_x, 0, local_x, raster.height - 1), fill=(255, 255, 255, 235))
        self.rendered = ImageTk.PhotoImage(raster, master=self)
        self.create_image(left, top, anchor='nw', image=self.rendered)
        if divider is not None:
            handle_x, handle_y = handle_position(divider, left, top, right, bottom)
            self.create_image(handle_x, handle_y, image=self.handle)
        if self.zoom > 1.0:
            scale = self.display_scale(self.after_image or self.before_image)
            self.draw_zoom_notice(left, bottom, translate('Ansicht: {0:.0f} %', scale * 100))
        elif self.fit_notice_job is not None:
            self.draw_zoom_notice(left, bottom, translate('Ansicht: Eingepasst'))

    def draw_zoom_notice(self, left, bottom, text):
        label = self.create_text(left + 12, max(24, bottom - 12), text=text, anchor='sw',
                                 font=('Segoe UI', 10), fill=TEXT, tags='zoom_notice')
        x0, y0, x1, y1 = self.bbox(label)
        background = self.create_rectangle(x0 - 5, y0 - 2, x1 + 5, y1 + 2, fill=APP_BG,
                                           outline='', tags='zoom_notice')
        self.tag_lower(background, label)

    def destroy(self):
        self.cancel_fit_notice()
        super().destroy()
