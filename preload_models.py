"""Select portable model downloads before starting a restoration."""
import tkinter as tk
from tkinter import ttk

from language import translate
from methods import LANCZOS, LICENSES, METHODS, MICROSOFT, UPSCALE_LICENSES, UPSCALERS, UPSCALING, available_methods
from portable_setup import COMPUTE_DEVICES, NVIDIA, Setup
from theme import APP_BG, MUTED, PANEL_BG, checkbox, set_control_state


def preload_requests(methods, upscalers, *, faces=False):
    requests = [(method, method == MICROSOFT and faces, LANCZOS)
                for method in dict.fromkeys(methods) if method != UPSCALING]
    requests.extend((UPSCALING, False, upscaler)
                    for upscaler in dict.fromkeys(upscalers) if upscaler != LANCZOS)
    return tuple(requests)


def available_preload_methods(compute, supports_nunchaku):
    return tuple(method for method in available_methods(compute == NVIDIA and supports_nunchaku)
                 if method != UPSCALING)


def preload_label(method, upscaler):
    return upscaler if method == UPSCALING else translate(METHODS[method])


def format_download_size(size):
    return f'{size / 1e6:.1f} MB' if size < 1e9 else f'{size / 1e9:.1f} GB'


class PreloadDialog(tk.Toplevel):
    def __init__(self, parent, root, compute, current_method, current_upscaler, faces, supports_nunchaku):
        super().__init__(parent)
        self.transient(parent)
        self.title(translate('Modelle vorab laden …'))
        self.configure(bg=APP_BG)
        self.resizable(False, False)
        self.result = None
        self.root = root
        self.compute = compute
        self.downloads = {}
        self.methods = {}
        self.upscalers = {}

        options = tk.Frame(self, bg=APP_BG, padx=14, pady=12)
        options.pack(fill='both', expand=True)
        left = tk.Frame(options, bg=PANEL_BG, padx=12, pady=8)
        right = tk.Frame(options, bg=PANEL_BG, padx=12, pady=8)
        left.grid(row=0, column=0, padx=(0, 8), sticky='nsew')
        right.grid(row=0, column=1, sticky='nsew')
        ttk.Label(left, text=translate('Verfahren'), background=PANEL_BG).pack(anchor='w', pady=(0, 4))
        ttk.Label(right, text='Upscaler', background=PANEL_BG).pack(anchor='w', pady=(0, 4))

        for method in available_preload_methods(compute, supports_nunchaku):
            license_label = translate(LICENSES[method])
            self.methods[method] = self.option(left, translate(METHODS[method]), license_label,
                                               method == current_method)
        self.faces = tk.BooleanVar(self, faces)
        self.face_option = checkbox(left, translate('Gesichtsverbesserung · iBUG (nicht kommerziell)'),
                                    self.faces, self.update_total)
        self.face_option.pack(anchor='w', padx=(12, 0), pady=(4, 0))
        for upscaler in UPSCALERS:
            if upscaler != LANCZOS:
                self.upscalers[upscaler] = self.option(right, upscaler, UPSCALE_LICENSES[upscaler],
                                                       upscaler == current_upscaler)

        footer = tk.Frame(self, bg=APP_BG, padx=14, pady=10)
        footer.pack(fill='x')
        self.total = tk.StringVar(self)
        tk.Label(footer, textvariable=self.total, bg=APP_BG, fg=MUTED).pack(anchor='w', pady=(0, 8))
        actions = tk.Frame(footer, bg=APP_BG)
        actions.pack(fill='x')
        ttk.Button(actions, text=translate('Alle auswählen'),
                   command=lambda: self.select_all(True)).pack(side='left')
        ttk.Button(actions, text=translate('Auswahl leeren'),
                   command=lambda: self.select_all(False)).pack(side='left', padx=6)
        self.submit = ttk.Button(actions, text=translate('Vorab laden'), style='Primary.TButton', command=self.apply)
        self.submit.pack(side='right')
        ttk.Button(actions, text=translate('Abbrechen'), command=self.destroy).pack(side='right', padx=6)
        self.bind('<Escape>', lambda event: self.destroy())
        self.bind('<Return>', lambda event: self.apply())
        self.update_total()

    def option(self, parent, label, license_label, selected):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill='x')
        value = tk.BooleanVar(self, selected)
        checkbox(row, label, value, self.update_total).pack(side='left')
        tk.Label(row, text=license_label, bg=PANEL_BG, fg=MUTED, padx=6).pack(side='right')
        return value

    def select_all(self, selected):
        for value in (*self.methods.values(), *self.upscalers.values()):
            value.set(selected)
        self.faces.set(selected)
        self.update_total()

    def selection(self):
        return preload_requests((method for method, value in self.methods.items() if value.get()),
                                (upscaler for upscaler, value in self.upscalers.items() if value.get()),
                                faces=self.faces.get())

    def update_total(self):
        set_control_state(self.face_option, 'normal' if self.methods[MICROSOFT].get() else 'disabled')
        requests = self.selection()
        remaining = {}
        for request in requests:
            if request not in self.downloads:
                method, faces, upscaler = request
                self.downloads[request] = Setup(self.root, method=method, faces=faces, upscaler=upscaler,
                                                compute=self.compute).remaining_downloads()
            remaining.update(self.downloads[request])
        self.total.set(translate('Berechnung: {0} · Noch etwa {1} Download',
                                 COMPUTE_DEVICES[self.compute], format_download_size(sum(remaining.values()))))
        self.submit.configure(state='normal' if requests else 'disabled')

    def apply(self):
        selected = self.selection()
        if selected:
            self.result = selected
            self.destroy()


def choose_preloads(parent, root, compute, method, upscaler, faces, supports_nunchaku):
    dialog = PreloadDialog(parent, root, compute, method, upscaler, faces, supports_nunchaku)
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    parent.wait_window(dialog)
    return dialog.result
