"""Native grouped menus with a visible path to the current selection."""
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from theme import GOLD, GOLD_LIGHT


class SelectionMenu(tk.Menu):
    def __init__(self, parent, selection, **options):
        super().__init__(parent, **options)
        self.selection = selection
        self.choices = {}
        self.categories = {}
        self.marked = set()
        self.heading_images = []
        self.heading_directory = None
        self.heading_bitmaps = {}
        self.windowing_system = self.tk.call('tk', 'windowingsystem')

        size = max(10, round(self.winfo_fpixels('9p')))
        self.blank = tk.PhotoImage(master=self, width=size, height=size)
        check = Image.new('RGBA', (size, size))
        ImageDraw.Draw(check).line(((1, size // 2), (size // 3, size - 3), (size - 2, 2)),
                                   fill=GOLD_LIGHT, width=max(2, size // 6), joint='curve')
        self.check = ImageTk.PhotoImage(check, master=self)
        self.marker_options = dict(image=self.blank, compound='left',
                                   hidemargin=self.windowing_system != 'win32')
        self.selection_trace = selection.trace_add('write', self.update_marks)
        self.bind('<Destroy>', self.remove_trace, add='+')

    def remove_trace(self, _event):
        self.selection.trace_remove('write', self.selection_trace)
        if self.heading_directory is not None:
            self.heading_directory.cleanup()

    def add_heading(self, label):
        options = dict(label=label, state='disabled', activebackground=self.cget('background'))
        size = round(self.winfo_fpixels('9p'))
        if self.windowing_system != 'aqua':
            font_path = 'segoeuib.ttf' if self.windowing_system == 'win32' else 'DejaVuSans-Bold.ttf'
            bitmap = self.heading_bitmap(label, size, font_path)
            self.add_command(bitmap=f'@{bitmap}', compound='none', **options)
            return
        # Aqua uses system text colors. An image preserves the heading color.
        heading = self.draw_heading(label, size, '/System/Library/Fonts/Supplemental/Arial Bold.ttf', 'RGBA', GOLD)
        image = ImageTk.PhotoImage(heading, master=self)
        self.heading_images.append(image)
        self.add_command(image=image, compound='none', **options)

    @staticmethod
    def draw_heading(label, size, font_path, mode, color):
        try:
            font = ImageFont.truetype(font_path, size)
            stroke = 0
        except OSError:
            font = ImageFont.load_default(size=size)
            stroke = 1
        left, top, right, bottom = font.getbbox(label, stroke_width=stroke)
        image = Image.new(mode, (right - left, bottom - top + 4))
        ImageDraw.Draw(image).text((-left, 2 - top), label, font=font, fill=color, stroke_width=stroke)
        return image

    def heading_bitmap(self, label, size, font_path):
        # A Tk bitmap uses disabledforeground directly and supplies its own font.
        key = label, size
        if key in self.heading_bitmaps:
            return self.heading_bitmaps[key]
        if self.heading_directory is None:
            self.heading_directory = TemporaryDirectory(prefix='restorenate-menu-')
        bitmap = self.draw_heading(label, size, font_path, '1', 1)
        path = Path(self.heading_directory.name) / f'heading-{len(self.heading_bitmaps)}.xbm'
        bitmap.save(path)
        self.heading_bitmaps[key] = path
        return path

    def add_category(self, label, submenu):
        self.add_cascade(label=label, menu=submenu, **self.marker_options)
        self.categories[submenu] = self, self.index('end')

    def add_choice(self, label, value, command, *, menu, state='normal'):
        options = (dict(selectcolor=GOLD_LIGHT) if self.windowing_system == 'win32'
                   else dict(indicatoron=False, **self.marker_options))
        menu.add_radiobutton(label=label, value=value, variable=self.selection, command=command, state=state,
                             **options)
        self.choices[value] = menu, menu.index('end')

    def update_marks(self, *_):
        choice = self.choices.get(self.selection.get())
        marked = {choice} if choice and self.windowing_system != 'win32' else set()
        if choice and choice[0] in self.categories:
            marked.add(self.categories[choice[0]])
        for menu, index in self.marked - marked:
            menu.entryconfigure(index, image=self.blank)
        for menu, index in marked - self.marked:
            menu.entryconfigure(index, image=self.check)
        self.marked = marked

    def clear_entries(self):
        self.delete(0, 'end')
        for submenu in self.categories:
            submenu.destroy()
        self.choices.clear()
        self.categories.clear()
        self.marked.clear()
        self.heading_images.clear()
