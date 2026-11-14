"""Exercise output selection, settings and the job's actual target."""
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from unittest.mock import Mock, patch

from PIL import Image

import app
from imaging import save_result


def check_output_destination():
    with TemporaryDirectory() as temp:
        folder = Path(temp).resolve()
        first = folder / 'first'
        second = folder / 'second'
        custom = folder / 'custom'
        for source_folder in (first, second):
            source_folder.mkdir()
            with Image.new('RGB', (48, 32), '#303030') as image:
                image.save(source_folder / 'image.png')

        with patch.object(app, 'SETTINGS', folder / 'settings.json'):
            window = tk.Tk()
            try:
                gui = app.Application(window)
                assert gui.output_in_source.get()
                assert gui.output_entry.get() == ''
                assert gui.output_entry.instate(['readonly'])

                with patch.object(app.filedialog, 'askopenfilename', return_value=str(first / 'image.png')) as dialog:
                    gui.choose_photo()
                    assert dialog.call_args.kwargs['initialdir'] == str(app.ROOT)
                assert gui.output_entry.get() == str(first / 'output')
                with patch.object(app.filedialog, 'askdirectory', return_value=str(second)) as dialog:
                    gui.choose_folder()
                    assert dialog.call_args.kwargs['initialdir'] == str(first)
                assert gui.output_entry.get() == str(second / 'output')
                assert not (first / 'output').exists()
                assert not (second / 'output').exists()
                gui.change_language('en')
                assert gui.output_entry.get() == str(second / 'output')
                assert gui.output_mode.cget('text') == 'Use a subfolder inside the input folder'

                gui.setup_for_job = Mock(return_value=Mock(ready=lambda: True))
                gui.launch = Mock()
                gui.start_clicked()
                assert gui.launch.call_args.args[1][1] == second / 'output'

                with patch.object(app.filedialog, 'askdirectory', return_value=str(custom)):
                    gui.choose_output()
                assert not gui.output_in_source.get()
                assert gui.output_entry.instate(['!readonly', '!disabled'])
                with patch.object(app.filedialog, 'askopenfilename', return_value='') as dialog:
                    gui.choose_photo()
                    assert dialog.call_args.kwargs['initialdir'] == str(second)
                with patch.object(app.filedialog, 'askdirectory', return_value='') as dialog:
                    gui.choose_folder()
                    assert dialog.call_args.kwargs['initialdir'] == str(second)
                with patch.object(app.filedialog, 'askopenfilename', return_value=str(first / 'image.png')) as dialog:
                    gui.choose_photo()
                    assert dialog.call_args.kwargs['initialdir'] == str(second)
                assert gui.output_entry.get() == str(custom)
                gui.start_clicked()
                sources, target, output_format, *_ = gui.launch.call_args.args[1]
                assert target == custom
                with Image.open(sources[0]) as image:
                    output, _ = save_result(image, sources[0], target, output_format, None, None)
                assert output.parent == custom and output.is_file()
                assert not (custom / 'output').exists()
                assert app.read_settings()['output_in_source'] is False
                assert app.read_settings()['custom_output'] == str(custom)
                assert app.read_settings()['input_folder'] == str(first)
                gui.results = [(sources[0], output, None, 0)]
                gui.index = 0
                gui.reuse_result()
                assert gui.input_dialog_folder() == str(first)
                gui.pick_sources(first / 'image.png')

                gui.output_mode.toggle()
                assert gui.output_entry.get() == str(first / 'output')
                gui.save_settings()
                assert app.read_settings()['output_in_source'] is True
                assert app.read_settings()['custom_output'] == str(custom)
            finally:
                gui.destroy_window()

            window = tk.Tk()
            try:
                gui = app.Application(window)
                assert gui.output_in_source.get()
                with patch.object(app.filedialog, 'askdirectory', return_value=str(second)) as dialog:
                    gui.choose_folder()
                    assert dialog.call_args.kwargs['initialdir'] == str(first)
                assert gui.output_entry.get() == str(second / 'output')
                gui.output_mode.toggle()
                assert gui.output_entry.get() == str(custom)
                gui.output_entry.delete(0, 'end')
                gui.output_entry.insert(0, str(folder / 'typed'))
                gui.save_settings()
                assert app.read_settings()['custom_output'] == str(folder / 'typed')
            finally:
                gui.destroy_window()

    print('Input dialogs, automatic and custom destinations, job target and saved settings passed.')
