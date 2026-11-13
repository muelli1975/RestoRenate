"""Progress for one processing phase, with an activity indicator when unmeasured."""
import time
import tkinter as tk


class ProgressTrack(tk.Canvas):
    def __init__(self, parent, background, accent, track):
        super().__init__(parent, bg=background, height=10, highlightthickness=0, borderwidth=0)
        self.value = 0
        self.started = 0.0
        self.timer = None
        self.track = self.create_line(4, 5, 4, 5, fill=track, width=5, capstyle=tk.ROUND)
        self.fill = self.create_line(4, 5, 4, 5, fill=accent, width=5, capstyle=tk.ROUND)
        self.bind('<Configure>', self.draw)

    def set(self, value):
        if value is None and self.value is not None:
            self.started = time.monotonic()
            self.value = None
            self.animate()
        elif value is not None:
            self.stop_timer()
            self.value = max(0, min(value, 100))
            self.draw()

    def stop_timer(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None

    def animate(self):
        self.draw()
        self.timer = self.after(33, self.animate)

    def draw(self, event=None):
        width = max(0, self.winfo_width() - 8)
        self.coords(self.track, 4, 5, 4 + width, 5)
        if self.value is None:
            phase = (time.monotonic() - self.started) / 1.6 % 1
            start = (width * 1.20) * phase - width * 0.20
            end = min(width, start + width * 0.20)
            start = max(0, start)
        else:
            start, end = 0, width * self.value / 100
        self.coords(self.fill, 4 + start, 5, 4 + end, 5)
        self.itemconfigure(self.fill, state='normal' if end > start else 'hidden')

    def destroy(self):
        self.stop_timer()
        super().destroy()
