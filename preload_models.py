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
    if size < 1000:
        return translate('{0} Byte', size)
    if size < 1e6:
        return f'{size / 1e3:.1f} kB'
    return f'{size / 1e6:.1f} MB' if size < 1e9 else f'{size / 1e9:.1f} GB'


class PreloadDialog(tk.Toplevel):
    def __init__(self, parent, root, compute, supports_nunchaku):
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
        self.installed = set()

        tk.Label(self, text=translate('Ausgegraute Haken zeigen vorhandene Dateien. Weitere Dateien per Haken auswählen.'),
                 bg=APP_BG, fg=MUTED).pack(anchor='w', padx=14, pady=(10, 0))
        options = tk.Frame(self, bg=APP_BG, padx=14, pady=12)
        options.pack(fill='both', expand=True)
        left = tk.Frame(options, bg=PANEL_BG, padx=12, pady=8)
        right = tk.Frame(options, bg=PANEL_BG, padx=12, pady=8)
        left.grid(row=0, column=0, padx=(0, 8), sticky='nsew')
        right.grid(row=0, column=1, sticky='nsew')
        ttk.Label(left, text=translate('Verfahren'), background=PANEL_BG).pack(anchor='w', pady=(0, 4))
        ttk.Label(right, text='Upscaler', background=PANEL_BG).pack(anchor='w', pady=(0, 4))

        methods = available_preload_methods(compute, supports_nunchaku)
        grouped_bases = {base for base, _ in LIGHTNING_MODELS.values()}
        for method in methods:
            if method in LIGHTNING_MODELS:
                base, label = LIGHTNING_MODELS[method]
                base_option = self.option(left, translate(METHODS[base]), translate(LICENSES[base]),
                                          request=(base, False, LANCZOS),
                                          command=lambda method=method: self.update_lightning(method, base_changed=True))
                lora_option = self.option(left, translate(label), '', indent=OPTION_INDENT,
                                          request=(method, False, LANCZOS), base=(base, False, LANCZOS),
                                          command=lambda method=method: self.update_lightning(method))
                self.lightning[method] = base_option, lora_option
                self.methods[base] = base_option
                continue
            if method in grouped_bases:
                continue
            license_label = translate(LICENSES[method])
            label = translate(METHODS[method])
            if method == QWEN2509_NUNCHAKU:
                label = translate('{0} · Lightning integriert', label)
            request = (method, False, LANCZOS)
            self.methods[method] = self.option(
                left, label, license_label, request=request,
                command=self.update_microsoft if method == MICROSOFT else None,
            )
            if method == MICROSOFT:
                self.faces = self.option(
                    left, translate('Gesichter verbessern'), translate('iBUG · nicht kommerziell'),
                    request=(method, True, LANCZOS), base=request,
                    indent=OPTION_INDENT, command=self.select_faces,
                )
        for upscaler in UPSCALERS:
            if upscaler != LANCZOS:
                self.upscalers[upscaler] = self.option(right, upscaler, UPSCALE_LICENSES[upscaler],
                                                       request=(UPSCALING, False, upscaler))

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

    def option(self, parent, label, license_label, *, request, base=None, indent=0, command=None):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill='x', padx=(indent, 0), pady=OPTION_SPACING)
        status = self.model_status(request, base)
        available = status == 'Vorhanden'
        value = tk.BooleanVar(self, available)
        control = checkbox(row, label, value, command or self.update_total)
        control.pack(side='left')
        if available:
            self.installed.add(str(value))
            set_control_state(control, 'disabled')
        details = ' · '.join(filter(None, (license_label, translate(status))))
        if details:
            tk.Label(row, text=details, bg=PANEL_BG, fg=MUTED, padx=6).pack(side='right')
        return value

    def download_plan(self, request):
        if request not in self.downloads:
            method, faces, upscaler = request
            setup = Setup(self.root, method=method, faces=faces, upscaler=upscaler, compute=self.compute)
            pending = setup.remaining_downloads()
            runtime = ((setup.runtime['path'] if setup.runtime else None, not setup.runtime_needs_setup())
                       if setup.comfy else None)
            self.downloads[request] = setup, pending, runtime
        return self.downloads[request]

    def model_status(self, request, base):
        setup, pending, _ = self.download_plan(request)
        base_files = {spec['path'] for spec in self.download_plan(base)[0].models} if base else set()
        models = [spec for spec in setup.models
                  if spec['path'] not in base_files and not spec['path'].endswith('.whl')]
        if not models:
            return ''
        if any(pending.get(spec['path'], 0) for spec in models):
            return 'Download nötig'
        return 'Vorhanden' if all(setup.valid(spec) for spec in models) else 'Zu prüfen'

    def chosen(self, value):
        return str(value) not in self.installed and value.get()

    def choose(self, value, selected):
        if str(value) not in self.installed:
            value.set(selected)

    def update_microsoft(self):
        if not self.methods[MICROSOFT].get():
            self.choose(self.faces, False)
        self.update_total()

    def select_faces(self):
        if self.chosen(self.faces):
            self.choose(self.methods[MICROSOFT], True)
        self.update_total()

    def update_lightning(self, method, *, base_changed=False):
        base_option, lora_option = self.lightning[method]
        if base_changed and not base_option.get():
            self.choose(lora_option, False)
        elif self.chosen(lora_option):
            self.choose(base_option, True)
        self.update_total()

    def select_all(self, selected):
        loras = [lora for _, lora in self.lightning.values()]
        for value in (*self.methods.values(), *self.upscalers.values(), *loras, self.faces):
            self.choose(value, selected)
        self.update_total()

    def selection(self):
        lightning = {LIGHTNING_MODELS[method][0]: method
                     for method, (_, lora) in self.lightning.items() if self.chosen(lora)}
        methods = [method for method, value in self.methods.items() if self.chosen(value) and method not in lightning]
        methods.extend(lightning.values())
        faces = self.chosen(self.faces)
        if faces and MICROSOFT not in methods:
            methods.append(MICROSOFT)
        return preload_requests(methods,
                                (upscaler for upscaler, value in self.upscalers.items() if self.chosen(value)),
                                faces=faces)

    def update_total(self):
        requests = self.selection()
        remaining = {}
        runtime = None
        for request in requests:
            _, pending, info = self.download_plan(request)
            remaining.update(pending)
            if info is not None and (runtime is None or not info[1]):
                runtime = info
        self.quoted_downloads = remaining
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
        if not requests:
            transfer = translate('Keine Auswahl')
        elif runtime is not None and runtime[0] is None and not runtime[1]:
            transfer = translate('Noch etwa {0} Modelldownload', format_download_size(remaining_bytes)) if remaining_bytes else translate('Keine Modelle herunterzuladen')
        self.total.set(translate('Berechnung: {0}', compute_label(self.compute)) + ' · ' + transfer)
        self.submit.configure(state='normal' if requests else 'disabled')

    def apply(self):
        selected = self.selection()
        if selected:
            self.result = selected, self.quoted_downloads
            self.destroy()


def choose_preloads(parent, root, compute, supports_nunchaku):
    dialog = PreloadDialog(parent, root, compute, supports_nunchaku)
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    parent.wait_window(dialog)
    return dialog.result
