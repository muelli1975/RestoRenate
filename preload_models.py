"""Select portable model downloads before starting a restoration."""
import tkinter as tk
from tkinter import ttk

from language import translate
from methods import (FIRERED_BASE, FIRERED_LIGHTNING, LANCZOS, LICENSES, METHODS, MICROSOFT,
                     QWEN2509_BASE, QWEN2509_LIGHTNING_4, QWEN2509_NUNCHAKU,
                     QWEN2511_BASE, QWEN2511_LIGHTNING_4, UPSCALE_LICENSES, UPSCALERS,
                     UPSCALING, available_methods)
from portable_setup import CPU, NVIDIA, Setup, compute_label
from theme import APP_BG, MUTED, PANEL_BG, checkbox, set_control_state


LIGHTNING_MODELS = {
    QWEN2509_LIGHTNING_4: (QWEN2509_BASE, 'Lightning-LoRA · 4 Schritte'),
    QWEN2511_LIGHTNING_4: (QWEN2511_BASE, 'Lightning-LoRA · 4 Schritte'),
    FIRERED_LIGHTNING: (FIRERED_BASE, 'Lightning-LoRA · 8 Schritte'),
}
OPTION_SPACING = (0, 5)
OPTION_INDENT = 18


def preload_requests(methods, upscalers, *, faces=False):
    requests = [(method, method == MICROSOFT and faces, LANCZOS)
                for method in dict.fromkeys(methods) if method != UPSCALING]
    requests.extend((UPSCALING, False, upscaler)
                    for upscaler in dict.fromkeys(upscalers) if upscaler != LANCZOS)
    return tuple(requests)


def available_preload_methods(compute, supports_nunchaku):
    return tuple(method for method in available_methods(compute == NVIDIA and supports_nunchaku, cpu=compute == CPU)
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
        self.lightning = {}
        self.upscalers = {}

        options = tk.Frame(self, bg=APP_BG, padx=14, pady=12)
        options.pack(fill='both', expand=True)
        left = tk.Frame(options, bg=PANEL_BG, padx=12, pady=8)
        right = tk.Frame(options, bg=PANEL_BG, padx=12, pady=8)
        left.grid(row=0, column=0, padx=(0, 8), sticky='nsew')
        right.grid(row=0, column=1, sticky='nsew')
        ttk.Label(left, text=translate('Verfahren'), background=PANEL_BG).pack(anchor='w', pady=(0, 4))
        ttk.Label(right, text='Upscaler', background=PANEL_BG).pack(anchor='w', pady=(0, 4))

        self.faces = tk.BooleanVar(self, faces)
        methods = available_preload_methods(compute, supports_nunchaku)
        grouped_bases = {base for base, _ in LIGHTNING_MODELS.values()}
        for method in methods:
            if method in LIGHTNING_MODELS:
                base, label = LIGHTNING_MODELS[method]
                base_option = self.option(left, translate(METHODS[base]), translate(LICENSES[base]),
                                          current_method in (base, method),
                                          command=lambda method=method: self.update_lightning(method, base_changed=True),
                                          enabled=base in methods)
                lora_option = self.option(left, translate(label), '', current_method == method, indent=OPTION_INDENT,
                                          command=lambda method=method: self.update_lightning(method))
                self.lightning[method] = base_option, lora_option
                if base in methods:
                    self.methods[base] = base_option
                continue
            if method in grouped_bases:
                continue
            license_label = translate(LICENSES[method])
            label = translate(METHODS[method])
            if method == QWEN2509_NUNCHAKU:
                label = translate('{0} · Lightning integriert', label)
            self.methods[method] = self.option(left, label, license_label, method == current_method)
            if method == MICROSOFT:
                faces_row = tk.Frame(left, bg=PANEL_BG)
                faces_row.pack(fill='x', padx=(OPTION_INDENT, 0), pady=OPTION_SPACING)
                self.face_option = checkbox(faces_row, translate('Gesichter verbessern'), self.faces, self.update_total)
                self.face_option.pack(side='left')
                tk.Label(faces_row, text=translate('iBUG · nicht kommerziell'), bg=PANEL_BG, fg=MUTED,
                         padx=6).pack(side='right')
        for upscaler in UPSCALERS:
            if upscaler != LANCZOS:
                self.upscalers[upscaler] = self.option(right, upscaler, UPSCALE_LICENSES[upscaler],
                                                       upscaler == current_upscaler)

        footer = tk.Frame(self, bg=APP_BG, padx=14, pady=10)
        footer.pack(fill='x')
        self.total = tk.StringVar(self)
        tk.Label(footer, textvariable=self.total, bg=APP_BG, fg=MUTED).pack(anchor='w', pady=(0, 8))
        self.runtime_status = tk.StringVar(self)
        tk.Label(footer, textvariable=self.runtime_status, bg=APP_BG, fg=MUTED).pack(anchor='w', pady=(0, 8))
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

    def option(self, parent, label, license_label, selected, *, indent=0, command=None, enabled=True):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill='x', padx=(indent, 0), pady=OPTION_SPACING)
        value = tk.BooleanVar(self, selected)
        control = checkbox(row, label, value, command or self.update_total)
        control.pack(side='left')
        if not enabled:
            set_control_state(control, 'disabled')
        if license_label:
            tk.Label(row, text=license_label, bg=PANEL_BG, fg=MUTED, padx=6).pack(side='right')
        return value

    def update_lightning(self, method, *, base_changed=False):
        base_option, lora_option = self.lightning[method]
        base = LIGHTNING_MODELS[method][0]
        if base not in self.methods:
            base_option.set(lora_option.get())
        elif base_changed and not base_option.get():
            lora_option.set(False)
        elif lora_option.get():
            base_option.set(True)
        self.update_total()

    def select_all(self, selected):
        for value in (*self.methods.values(), *self.upscalers.values()):
            value.set(selected)
        for base, lora in self.lightning.values():
            base.set(selected)
            lora.set(selected)
        self.faces.set(selected)
        self.update_total()

    def selection(self):
        lightning = {LIGHTNING_MODELS[method][0]: method for method, (_, lora) in self.lightning.items() if lora.get()}
        methods = [method for method, value in self.methods.items() if value.get() and method not in lightning]
        methods.extend(lightning.values())
        return preload_requests(methods,
                                (upscaler for upscaler, value in self.upscalers.items() if value.get()),
                                faces=self.faces.get())

    def update_total(self):
        set_control_state(self.face_option, 'normal' if self.methods[MICROSOFT].get() else 'disabled')
        requests = self.selection()
        remaining = {}
        runtime = None
        for request in requests:
            if request not in self.downloads:
                method, faces, upscaler = request
                setup = Setup(self.root, method=method, faces=faces, upscaler=upscaler, compute=self.compute)
                pending = setup.remaining_downloads()
                info = (setup.runtime['path'] if setup.runtime else None, bool(setup.runtime_ready())) if setup.comfy else None
                self.downloads[request] = pending, info
            pending, info = self.downloads[request]
            remaining.update(pending)
            if info is not None:
                runtime = info
        runtime_status = ''
        if runtime is not None:
            path, ready = runtime
            if ready:
                runtime_status = 'ComfyUI · bereits eingerichtet'
            elif path is None:
                runtime_status = 'ComfyUI · Python-Pakete werden eingerichtet'
            elif remaining.get(path, 0):
                runtime_status = 'ComfyUI · wird mitgeladen'
            else:
                runtime_status = 'ComfyUI · wird eingerichtet'
        self.runtime_status.set(translate(runtime_status))
        remaining_bytes = sum(remaining.values())
        transfer = (translate('Noch etwa {0} Download', format_download_size(remaining_bytes)) if remaining_bytes
                    else translate('Keine Downloads erforderlich'))
        if runtime is not None and runtime[0] is None and not runtime[1]:
            transfer = translate('Noch etwa {0} Modelldownload', format_download_size(remaining_bytes)) if remaining_bytes else translate('Keine Modelle herunterzuladen')
        self.total.set(translate('Berechnung: {0}', compute_label(self.compute)) + ' · ' + transfer)
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
