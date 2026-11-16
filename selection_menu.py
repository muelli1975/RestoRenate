"""Native grouped menus with a visible path to the current selection."""
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

        size = max(10, round(self.winfo_fpixels('9p')))
        self.blank = tk.PhotoImage(master=self, width=size, height=size)
        check = Image.new('RGBA', (size, size))
        ImageDraw.Draw(check).line(((1, size // 2), (size // 3, size - 3), (size - 2, 2)),
                                   fill=GOLD_LIGHT, width=max(2, size // 6), joint='curve')
        self.check = ImageTk.PhotoImage(check, master=self)
        self.marker_options = dict(image=self.blank, compound='left', hidemargin=True)
        self.selection_trace = selection.trace_add('write', self.update_marks)
        self.bind('<Destroy>', self.remove_trace, add='+')

    def remove_trace(self, _event):
        self.selection.trace_remove('write', self.selection_trace)

    def add_heading(self, label):
        if self.tk.call('tk', 'windowingsystem') != 'aqua':
            self.add_command(label=label, state='disabled', font=('Segoe UI', 9))
            return
        # Aqua draws native menu text in system colors. An image carries the heading color.
        font = ImageFont.load_default(size=round(self.winfo_fpixels('9p')))
        left, top, right, bottom = font.getbbox(label)
        heading = Image.new('RGBA', (right - left, bottom - top + 4))
        ImageDraw.Draw(heading).text((-left, 2 - top), label, font=font, fill=GOLD)
        image = ImageTk.PhotoImage(heading, master=self)
        self.heading_images.append(image)
        self.add_command(label=label, state='disabled', image=image)

    def add_category(self, label, submenu):
        self.add_cascade(label=label, menu=submenu, **self.marker_options)
        self.categories[submenu] = self, self.index('end')

    def add_choice(self, label, value, command, *, menu):
        menu.add_radiobutton(label=label, value=value, variable=self.selection, command=command,
                             indicatoron=False, **self.marker_options)
        self.choices[value] = menu, menu.index('end')

    def update_marks(self, *_):
        choice = self.choices.get(self.selection.get())
        marked = {choice} if choice else set()
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
