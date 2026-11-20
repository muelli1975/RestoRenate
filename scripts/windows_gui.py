"""Entry point for the PyInstaller Windows build."""
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import traceback

from technical_logs import TechnicalLog


def main():
    folder = Path(sys.executable).parent / "logs"
    folder.mkdir(exist_ok=True)
    with TechnicalLog(folder / "application.log") as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                from app import run_gui
                run_gui()
            except Exception:
                log.write(traceback.format_exc())
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
