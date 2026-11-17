"""Select portable model downloads before starting a restoration."""
from queue import Empty, SimpleQueue
from threading import Event, Thread
import tkinter as tk
from tkinter import ttk

from language import translate
from methods import (FIRERED_BASE, FIRERED_LIGHTNING, LANCZOS, LICENSES, METHODS, MICROSOFT,
                     QWEN2509_BASE, QWEN2509_LIGHTNING_4, QWEN2509_NUNCHAKU,
                     QWEN2511_BASE, QWEN2511_LIGHTNING_4, UPSCALE_LICENSES, UPSCALE_MENU_SECTIONS,
                     UPSCALING, available_methods)
from portable_setup import CPU, NVIDIA, Setup, SetupCancelled, compute_label, contained, file_size
from progress_track import ProgressTrack
from theme import APP_BG, BORDER, GOLD, MUTED, PANEL_BG, TEXT, checkbox


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


def verify_local_models(root, compute, models, cancelled, results):
    try:
        setup = Setup(root, compute=compute, notify=lambda _: None, cancelled=cancelled.is_set)
        for path, spec in models.items():
            try:
                if setup.download(spec, local_only=True) is not None:
                    results.put(path)
            except OSError:
                continue
    except SetupCancelled:
        pass
    finally:
        results.put(None)


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
        self.local_models = {}
        self.pending_checks = {}
        self.verified_local = set()
        self.verification_results = SimpleQueue()
        self.verification_cancelled = Event()
        self.verification_timer = None

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
        for heading, upscalers in UPSCALE_MENU_SECTIONS:
            ttk.Label(right, text=translate(heading), background=PANEL_BG, foreground=GOLD,
                      font=('TkDefaultFont', 9, 'bold')).pack(anchor='w', pady=(2, 1))
            for upscaler in upscalers:
                self.upscalers[upscaler] = self.option(right, upscaler, UPSCALE_LICENSES[upscaler],
                                                       request=(UPSCALING, False, upscaler), spacing=(0, 2))

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
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        if self.local_models:
            complete = sorted((paths for _, paths in self.pending_checks.values()),
                              key=lambda paths: sum(self.local_models[path]['size'] for path in paths))
            # Finish small, complete selections before checking partial selections.
            order = dict.fromkeys(path for paths in complete for path in paths)
            order.update(self.local_models)
            self.verification_timer = self.after(75, self.poll_verification)
            Thread(target=verify_local_models, daemon=True,
                   args=(self.root, self.compute, order,
                         self.verification_cancelled, self.verification_results)).start()
        self.update_total()

    def option(self, parent, label, license_label, *, request, base=None, indent=0, command=None, spacing=OPTION_SPACING):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill='x', padx=(indent, 0), pady=spacing)
        setup, _, _ = self.download_plan(request)
        base_files = {spec['path'] for spec in self.download_plan(base)[0].models} if base else set()
        models = [spec for spec in setup.models
                  if spec['path'] not in base_files and not spec['path'].endswith('.whl')]
        unverified = [spec for spec in models if not setup.valid(spec)]
        value = tk.BooleanVar(self, bool(models) and not unverified)
        complete = {spec['path']: spec for spec in unverified
                    if file_size(contained(self.root, spec['path'])) == spec['size']}
        self.local_models.update(complete)
        if complete and len(complete) == len(unverified):
            self.pending_checks[request] = value, complete.keys()

            def keep_selection(*_):
                self.pending_checks.pop(request, None)

            value.trace_add('write', keep_selection)
        control = checkbox(row, label, value, command or self.update_total)
        control.pack(side='left')
        if license_label:
            tk.Label(row, text=license_label, bg=PANEL_BG, fg=MUTED, padx=6).pack(side='right')
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

    def poll_verification(self):
        finished = False
        while True:
            try:
                path = self.verification_results.get_nowait()
            except Empty:
                break
            if path is None:
                finished = True
                break
            self.verified_local.add(path)
        self.verification_timer = None if finished else self.after(75, self.poll_verification)
        changed = False
        for value, paths in tuple(self.pending_checks.values()):
            if paths <= self.verified_local:
                value.set(True)
                changed = True
        if finished:
            self.pending_checks.clear()
        if finished or changed:
            self.update_total()

    def destroy(self):
        self.verification_cancelled.set()
        if self.verification_timer is not None:
            self.after_cancel(self.verification_timer)
            self.verification_timer = None
        super().destroy()

    def update_microsoft(self):
        if not self.methods[MICROSOFT].get():
            self.faces.set(False)
        self.update_total()

    def select_faces(self):
        if self.faces.get():
            self.methods[MICROSOFT].set(True)
        self.update_total()

    def update_lightning(self, method, *, base_changed=False):
        base_option, lora_option = self.lightning[method]
        if base_changed and not base_option.get():
            lora_option.set(False)
        elif lora_option.get():
            base_option.set(True)
        self.update_total()

    def select_all(self, selected):
        loras = [lora for _, lora in self.lightning.values()]
        for value in (*self.methods.values(), *self.upscalers.values(), *loras, self.faces):
            value.set(selected)
        self.update_total()

    def selection(self):
        lightning = {LIGHTNING_MODELS[method][0]: method
                     for method, (base, lora) in self.lightning.items() if base.get() and lora.get()}
        methods = [method for method, value in self.methods.items() if value.get() and method not in lightning]
        methods.extend(lightning.values())
        return preload_requests(methods,
                                (upscaler for upscaler, value in self.upscalers.items() if value.get()),
                                faces=self.faces.get())

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
        if self.verification_timer is not None:
            checking = translate('Modelldateien werden geprüft …')
            transfer = f'{transfer} · {checking}' if requests else checking
        self.total.set(translate('Berechnung: {0}', compute_label(self.compute)) + ' · ' + transfer)
        self.submit.configure(state='normal' if requests else 'disabled')

    def apply(self):
        selected = self.selection()
        if selected:
            self.result = selected, self.quoted_downloads
            self.destroy()


class PreloadProgress(tk.Toplevel):
    def __init__(self, parent, cancel, closed):
        super().__init__(parent)
        self.transient(parent)
        self.configure(bg=APP_BG, padx=14, pady=12)
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', self.dismiss)
        self.bind('<Escape>', self.dismiss)
        self.active = True
        self.answer = None
        self.closed = closed

        panel = tk.Frame(self, bg=PANEL_BG, padx=12, pady=10, width=448)
        panel.pack(fill='both', expand=True)
        panel.columnconfigure(0, weight=1, minsize=424)
        self.status = tk.Label(panel, bg=PANEL_BG, fg=TEXT, anchor='w', justify='left', wraplength=424)
        self.status.grid(row=0, column=0, sticky='ew')
        self.progress = ProgressTrack(panel, PANEL_BG, GOLD, BORDER)
        self.progress.grid(row=1, column=0, sticky='ew', pady=6)
        self.details = tk.Label(panel, bg=PANEL_BG, fg=MUTED, anchor='nw', justify='left', wraplength=424)
        self.details.grid(row=2, column=0, sticky='ew')
        actions = tk.Frame(self, bg=APP_BG)
        actions.pack(fill='x', pady=(8, 0))
        self.dismiss_button = ttk.Button(actions, command=self.dismiss)
        self.dismiss_button.pack(side='right')
        self.cancel_button = ttk.Button(actions, command=cancel)
        self.cancel_button.pack(side='right', padx=(4, 6))
        self.approve_button = ttk.Button(actions, style='Primary.TButton', command=self.approve)
        self.localize()
        self.update_status(translate('Modelldateien werden geprüft …'))

    def localize(self):
        self.title(translate('Modelldownloads'))
        self.dismiss_button.configure(text=translate('Ausblenden' if self.active else 'Schließen'))
        self.cancel_button.configure(text=translate('Abbrechen'))
        self.approve_button.configure(text=translate('Herunterladen'))

    def update_status(self, text, detail='', percent=None):
        self.status.configure(text=text)
        self.details.configure(text=detail)
        self.progress.set(percent)

    def ask(self, name, amount, answer):
        self.answer = answer
        self.update_status(translate('Zusätzlicher Download'), f'{name} · {format_download_size(amount)}', 0)
        self.approve_button.pack(side='left')
        self.show()

    def approve(self):
        if self.answer is not None:
            self.answer.put_nowait(True)
            self.answer = None
        self.approve_button.pack_forget()

    def cancelling(self):
        self.approve_button.pack_forget()
        self.cancel_button.configure(state='disabled')
        self.update_status(translate('Abbruch läuft …'))

    def finish(self, text, detail='', *, success, dismiss_hidden=False):
        self.active = False
        self.answer = None
        if self.state() == 'withdrawn' and dismiss_hidden:
            self.dismiss()
            return
        self.cancel_button.pack_forget()
        self.approve_button.pack_forget()
        self.dismiss_button.configure(text=translate('Schließen'))
        self.update_status(text, detail, 100 if success else 0)

    def dismiss(self, _event=None):
        if self.active:
            self.withdraw()
        else:
            self.destroy()
            self.closed()

    def show(self):
        self.deiconify()
        self.lift()


def choose_preloads(parent, root, compute, supports_nunchaku):
    dialog = PreloadDialog(parent, root, compute, supports_nunchaku)
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    parent.wait_window(dialog)
    return dialog.result
