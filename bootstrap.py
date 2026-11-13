import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import runpy
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from language import configure_language, translate
from technical_logs import TechnicalLog


def run_application():
    with TechnicalLog(ROOT / 'logs/application.log') as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
            except Exception:
                log.write(traceback.format_exc())
                return 1
    return 0


def launch():
    try:
        pythonw = ROOT / 'runtime/python/pythonw.exe'
        env = dict(os.environ,
                   TCL_LIBRARY=str(ROOT / 'runtime/python/tcl/tcl8.6'),
                   TK_LIBRARY=str(ROOT / 'runtime/python/tcl/tk8.6'))
        subprocess.Popen([str(pythonw), '-I', '-X', 'utf8', str(ROOT / 'bootstrap.py'), '--gui'],
                         cwd=ROOT, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except Exception:
        TechnicalLog(ROOT / 'logs/launcher_error.log').write(traceback.format_exc())
        from tkinter import messagebox
        try:
            settings = json.loads((ROOT / 'settings/settings.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            settings = {}
        configure_language(settings.get('language') if isinstance(settings, dict) else None)
        messagebox.showerror('RestoRenate', translate('Start fehlgeschlagen. Siehe logs/launcher_error.log.'))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(run_application() if sys.argv[1:] == ['--gui'] else launch())
