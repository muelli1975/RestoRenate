"""Check the new model plans, edit graphs, and the packaged controls."""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import font, ttk
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / '_internal' if (root / '_internal').is_dir() else root))

from export_metadata import editable_workflow, seed_from_metadata
from methods import (DDCOLOR_TINY, FIBO2_TURBO, FLUX2, FLUX3, LANCZOS, METHODS, MICROSOFT, NOMOS2_HQ,
                     NOMOS2_DAT2, NOMOS8K_DAT, SEEDVR2, UPSCALE_MENU_SECTIONS, UPSCALERS, UPSCALING,
                     VOSR2, available_methods, model_files)
from portable_setup import CPU, MACOS, MPS, NVIDIA, Setup
from restoration import restore, restoration_graph
from sizes import CUSTOM_SIZE, DOUBLE_SIZE, FULL_HD, NO_RESCALE, ULTRA_HD
from theme import GOLD


def has_choice_mark(menu, choice_menu, index):
    if menu.windowing_system == 'win32':
        assert int(choice_menu.entrycget(index, 'indicatoron')) == 1
        assert int(choice_menu.entrycget(index, 'hidemargin')) == 0
        assert choice_menu.entrycget(index, 'image') == ''
        return choice_menu.getvar(choice_menu.entrycget(index, 'variable')) == choice_menu.entrycget(index, 'value')
    return choice_menu.entrycget(index, 'image') == str(menu.check)


def make_graph(second=None):
    models = {key: filename for key, (_, _, filename) in model_files(FLUX3, LANCZOS).items()}
    return restoration_graph(FLUX3, models, 'main.png', (1024, 768), (0, 2, 1024, 764),
                             'Remove the scratch.', 123456789, False, False, second_image=second)


def check_graphs():
    assert FLUX3 in available_methods(False)
    assert FLUX3 not in available_methods(False, cpu=True)
    flux, single = make_graph('reference.png'), make_graph()
    assert flux['6']['inputs']['images.image2'] == flux['8']['inputs']['images.image1'] == ['30', 0]
    assert '30' not in single and 'images.image2' not in single['6']['inputs']
    assert flux['9']['inputs']['steps'] == 16
    for graph in (flux, single):
        assert graph['11']['inputs']['height'] == 764
        assert seed_from_metadata({'prompt': json.dumps(graph)}) == 123456789
    flux_files, fibo_files = (
        {Path(spec['path']).name: spec for spec in Setup(root, method=method, upscaler=LANCZOS).models}
        for method in (FLUX3, FIBO2_TURBO)
    )
    for name in ('qwen3vl_4b_int8_convrot.safetensors', 'flux2-vae.safetensors'):
        assert flux_files[name] == fibo_files[name]
    new_flux = flux_files.keys() - fibo_files.keys()
    assert len(new_flux) == 2
    assert all(flux_files[name]['repo'] == 'KoalaNation/FLUX-3-KLEIN-MODELS' for name in new_flux)


def check_backend_schemas(definitions):
    graph = make_graph('reference.png')
    for node in graph.values():
        definition = definitions[node['class_type']]
        inputs = node['inputs']
        fields = {}
        for group in definition['input'].values():
            for name, spec in group.items():
                fields[name] = spec
                if spec[0] == 'COMFY_DYNAMICCOMBO_V3' and name in inputs:
                    option = next(option for option in spec[1]['options'] if option['key'] == inputs[name])
                    for children in option['inputs'].values():
                        fields.update((f'{name}.{child}', info) for child, info in children.items())
                if spec[0] == 'COMFY_AUTOGROW_V3':
                    template = spec[1]['template']
                    names = template.get('names')
                    if names is None:
                        names = [f"{template['prefix']}{index}" for index in range(template['max'])]
                    item, = (item for group in template['input'].values() for item in group.values())
                    fields.update((f'{name}.{child}', item) for child in names)
        assert set(inputs) <= fields.keys(), (node['class_type'], set(inputs) - fields.keys())
        if node['class_type'] == 'CLIPLoader':
            spec = fields['type']
            choices = spec[1]['options'] if spec[0] == 'COMBO' else spec[0]
            assert inputs['type'] in choices

    workflow = editable_workflow(graph, definitions, 'main.png', second_image='reference.png')
    for node in workflow['nodes']:
        if node['type'] == 'TextGenerateV2':
            assert 'on' in node['widgets_values'] and 123456789 in node['widgets_values']
            assert {'images.image1', 'images.image2', 'system_prompt'} <= {slot['name'] for slot in node['inputs']}
    print('The FLUX 3 API graph matches the installed ComfyUI node schemas.')


def check_upscale_graphs(source, directory):
    expected = (333, 200)
    choices = {
        NOMOS2_DAT2: ('ImageUpscaleWithModel', 13, 1),
        NOMOS8K_DAT: ('ImageUpscaleWithModel', 13, 1),
        SEEDVR2: ('SeedVR2PostProcessing', 48, 2),
        VOSR2: ('VOSR2Upscale', 41, 5),
    }
    for upscaler, (node_type, node_id, files) in choices.items():
        setup = Setup(root, method=UPSCALING, upscaler=upscaler)
        assert len(setup.models) == files and all(len(spec['sha256']) == 64 for spec in setup.models)
        for method in (UPSCALING, MICROSOFT):
            models = {key: file for key, (_, _, file) in model_files(method, upscaler).items()}
            client = SimpleNamespace(root=directory, image=lambda _: Image.new('RGB', expected))
            record = dict(method=method, models=models, prompt='', seed=None)
            with patch('restoration.generate', return_value={'filename': 'out.png'}) as run:
                output, warning = restore(client, models, source, directory, 'PNG', None, '', None,
                                          lambda _: None, lambda: False, record, method=method,
                                          size_choice=(CUSTOM_SIZE, expected[0]), upscaler=upscaler)
            graph = run.call_args.args[1]
            assert graph[str(node_id)]['class_type'] == node_type
            assert graph['80']['inputs']['image'] == [str(node_id), 0]
            assert graph['80']['inputs']['width'] == expected[0]
            assert graph['80']['inputs']['height'] == expected[1]
            first_id = '40' if upscaler == SEEDVR2 else str(node_id)
            assert graph[first_id]['inputs']['image'] == (['4', 0] if method == UPSCALING else ['11', 0])
            assert not warning
            with Image.open(output) as result:
                assert result.size == expected and 'workflow' in result.info
                assert str(node_id) in json.loads(result.info['prompt'])
            assert set(models) <= record['settings']['models'].keys()
    print('Four upscale models passed both export paths and model-manifest checks.')


def check_layout(source, language):
    import app
    from preload_models import PreloadDialog

    def menu_labels(menu):
        return [menu.entrycget(index, 'label') for index in range(menu.index('end') + 1)
                if menu.type(index) != 'separator']

    window = tk.Tk()
    compute = MPS if MACOS else NVIDIA
    try:
        ttk.Style(window).theme_use('clam')
        with patch.object(app, 'read_settings', return_value={'language': language, 'compute': compute}):
            gui = app.Application(window)
        with patch.object(gui, 'save_settings'):
            gui.pick_sources(source)
            menu = gui.method_menu
            headings = ('Bearbeiten', 'Kolorieren', 'Nur hochskalieren') if language == 'de' else ('Edit', 'Colorize', 'Upscale only')
            assert menu_labels(menu) == [headings[0], METHODS[FIBO2_TURBO], 'FireRed', 'FLUX', METHODS[MICROSOFT],
                                         'Qwen', headings[1], 'DDColor', 'DeOldify', headings[2]]
            assert menu.entrycget(headings[0], 'state') == menu.entrycget(headings[1], 'state') == 'disabled'
            assert all(str(menu.entrycget(heading, 'activebackground')) == str(menu.cget('background'))
                       for heading in headings[:2])
            if menu.windowing_system != 'aqua':
                assert str(menu.cget('disabledforeground')) == GOLD
            graphic = 'image' if menu.windowing_system == 'aqua' else 'bitmap'
            for heading in headings[:2]:
                assert menu.entrycget(heading, graphic) and menu.entrycget(heading, 'compound') == 'none'
            assert menu.entrycget(headings[2], 'value') == app.translate(METHODS[UPSCALING])
            upscale_menu = gui.upscale_menu
            assert menu_labels(upscale_menu) == [
                value for heading, choices in UPSCALE_MENU_SECTIONS
                for value in (app.translate(heading), *choices)
            ] + [LANCZOS]
            assert tuple(upscale_menu.choices) == UPSCALERS
            assert all(upscale_menu.entrycget(app.translate(heading), 'state') == 'disabled'
                       for heading, _ in UPSCALE_MENU_SECTIONS)
            upscale_menu.invoke(NOMOS2_DAT2)
            assert gui.upscaler.get() == NOMOS2_DAT2 and has_choice_mark(upscale_menu, upscale_menu, NOMOS2_DAT2)
            flux = menu.nametowidget(menu.entrycget('FLUX', 'menu'))
            assert [flux.entrycget(index, 'value') for index in range(flux.index('end') + 1)] == [METHODS[FLUX2], METHODS[FLUX3]]
            assert menu.entrycget('FLUX', 'image') == str(menu.blank)
            flux.invoke(1)
            assert gui.current_method == FLUX3
            assert menu.entrycget('FLUX', 'image') == str(menu.check) and has_choice_mark(menu, flux, 1)
            assert not has_choice_mark(menu, flux, 0)
            assert not has_choice_mark(menu, menu, METHODS[FIBO2_TURBO])
            window.update()
            assert gui.second_row.winfo_ismapped()
            minimum = window.minsize()
            for width, height in ((app.START_WINDOW_WIDTH, app.START_WINDOW_HEIGHT), minimum):
                window.geometry(f'{width}x{height}')
                window.update()
                button = gui.method_widget
                chosen_font = ttk.Style(window).lookup(button.cget('style'), 'font') or 'TkDefaultFont'
                text_width = font.Font(window, font=chosen_font).measure(METHODS[FLUX3])
                assert button.winfo_width() >= text_width + 28, (button.winfo_width(), text_width)
                assert gui.footer.winfo_ismapped() and button.winfo_ismapped()
                upscale_button = gui.upscale_options
                upscale_font = ttk.Style(window).lookup(upscale_button.cget('style'), 'font') or 'TkDefaultFont'
                upscale_width = max(font.Font(window, font=upscale_font).measure(name) for name in UPSCALERS)
                assert upscale_button.winfo_width() >= upscale_width + 20, (upscale_button.winfo_width(), upscale_width)
                print(f'{language} {FLUX3}: {window.winfo_width()}x{window.winfo_height()}, '
                      f'minimum {minimum}, method field {button.winfo_width()}x{button.winfo_height()} px, '
                      f'upscaler field {upscale_button.winfo_width()}x{upscale_button.winfo_height()} px.')
            menu.invoke(METHODS[FIBO2_TURBO])
            assert has_choice_mark(menu, menu, METHODS[FIBO2_TURBO])
            assert menu.entrycget('FLUX', 'image') == str(menu.blank) and not has_choice_mark(menu, flux, 1)
            with patch.object(app.messagebox, 'askyesno', return_value=True):
                assert gui.offer_cpu_fallback('Test CPU fallback')
            assert 'FireRed' not in menu_labels(menu)
            flux = menu.nametowidget(menu.entrycget('FLUX', 'menu'))
            assert flux.index('end') == 0 and flux.entrycget(0, 'value') == METHODS[FLUX2]
        dialog = PreloadDialog(window, root, compute, False)
        try:
            dialog.update_idletasks()
            assert FLUX3 in dialog.methods
            assert tuple(dialog.upscalers) == UPSCALERS[:-1]
            assert dialog.winfo_reqheight() <= dialog.winfo_screenheight(), dialog.winfo_reqheight()
            print(f'{language} download dialog: {dialog.winfo_reqwidth()}x{dialog.winfo_reqheight()}.')
        finally:
            dialog.destroy()
    finally:
        window.destroy()


def check_compute_settings(directory):
    import app

    @contextmanager
    def launch():
        gui = app.Application(tk.Tk())
        try:
            yield gui
        finally:
            gui.destroy_window()

    def switch(gui, compute):
        gui.compute.set(compute)
        gui.choose_compute()

    def select(gui, method, size, upscaler):
        gui.method.set(app.translate(METHODS[method]))
        gui.choose_method()
        gui.size.set(app.translate(size))
        gui.upscaler.set(upscaler)
        assert gui.save_settings()

    def selected(gui):
        return gui.current_method, gui.size_choice(), gui.effective_upscaler()

    settings = directory / 'compute-settings.json'
    gpu = MPS if MACOS else NVIDIA
    cpu_standard = (MICROSOFT, NO_RESCALE, LANCZOS)
    gpu_standard = (FIBO2_TURBO, ULTRA_HD, NOMOS2_HQ)
    with patch.object(app, 'SETTINGS', settings), patch.object(app.messagebox, 'showinfo'):
        settings.write_text(json.dumps({'compute': CPU}), encoding='utf-8')
        with launch() as gui:
            assert selected(gui) == cpu_standard
            assert gui.upscale_options.instate(['disabled'])
            select(gui, DDCOLOR_TINY, DOUBLE_SIZE, LANCZOS)
            gui.load_processing_preset('Standard')
            assert selected(gui) == cpu_standard
            switch(gui, gpu)
            assert gui.active_compute == CPU and selected(gui) == cpu_standard
            gui.save_settings()
        with launch() as gui:
            assert gui.active_compute == gpu and selected(gui) == gpu_standard

        # A settings file from 1.1 belongs to the device it was saved with.
        settings.write_text(json.dumps({'compute': gpu, 'method': FLUX2,
                                        'scaling': {'restoration': {'size': FULL_HD, 'upscaler': LANCZOS}}}),
                            encoding='utf-8')
        gpu_saved = (FLUX2, FULL_HD, LANCZOS)
        cpu_saved = (DDCOLOR_TINY, DOUBLE_SIZE, LANCZOS)
        with launch() as gui:
            assert selected(gui) == gpu_saved
            switch(gui, CPU)
        with launch() as gui:
            assert selected(gui) == cpu_standard
            select(gui, *cpu_saved)
            switch(gui, gpu)
        with launch() as gui:
            assert selected(gui) == gpu_saved
            with patch.object(app.messagebox, 'askyesno', return_value=True):
                assert gui.offer_cpu_fallback('GPU test')
            assert gui.active_compute == CPU and selected(gui) == gpu_saved
            select(gui, FIBO2_TURBO, NO_RESCALE, LANCZOS)
        with launch() as gui:
            assert gui.active_compute == gpu and selected(gui) == gpu_saved
            switch(gui, CPU)
        with launch() as gui:
            assert selected(gui) == cpu_saved
    print('CPU/GPU defaults, settings migration, restart switching and temporary fallback passed.')


if __name__ == '__main__':
    check_graphs()
    with TemporaryDirectory() as directory:
        source = Path(directory) / 'reference.png'
        with Image.new('RGB', (200, 120)) as image:
            image.save(source)
        check_upscale_graphs(source, Path(directory))
        for language in ('de', 'en'):
            check_layout(source, language)
        check_compute_settings(Path(directory))
