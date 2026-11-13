"""Bounded local diagnostics. Result history is managed by the application."""
from codecs import getincrementaldecoder
from io import TextIOBase
from pathlib import Path
from threading import Lock
import time


MAX_LOG_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 2
MAX_LOG_AGE = 30 * 24 * 60 * 60
TECHNICAL_LOG_NAMES = ('application.log', 'backend.log', 'setup.log', 'launcher_error.log')
_log_lock = Lock()


def _backup(path, index):
    return path.with_name(f'{path.name}.{index}')


def _rotate(path):
    for index in range(BACKUP_COUNT, 0, -1):
        source = path if index == 1 else _backup(path, index - 1)
        try:
            source.replace(_backup(path, index))
        except FileNotFoundError:
            pass


def _is_utf8_continuation(byte):
    return byte & 0xC0 == 0x80


def prepare_technical_logs(folder):
    """Apply startup retention to the app's own logs and their two backups."""
    cutoff = time.time() - MAX_LOG_AGE
    with _log_lock:
        for name in TECHNICAL_LOG_NAMES:
            current = folder / name
            for path in (current, *(_backup(current, n) for n in range(1, BACKUP_COUNT + 1))):
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    info = path.stat()
                    if info.st_mtime < cutoff:
                        path.unlink()
                except OSError:
                    # Logs on read-only media must not prevent startup.
                    pass


class TechnicalLog(TextIOBase):
    """UTF-8 output stream with byte-based rotation, shared by log producers."""

    def __init__(self, path):
        self.path = Path(path)
        if self.path.name not in TECHNICAL_LOG_NAMES:
            raise ValueError(f'Not a technical log: {self.path.name}')

    @property
    def encoding(self):
        return 'utf-8'

    def writable(self):
        return True

    def write(self, text):
        if self.closed:
            raise ValueError('I/O operation on closed log')
        if not text:
            return 0
        data = text.encode(self.encoding, errors='backslashreplace')
        with _log_lock:
            try:
                self._append(data)
            except OSError:
                # Keep the app and subprocess output drain alive on I/O failure.
                pass
        return len(text)

    def _append(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            return
        if self.path.is_file() and self.path.stat().st_size + len(data) > MAX_LOG_BYTES:
            _rotate(self.path)
        start = 0
        while start < len(data):
            end = min(start + MAX_LOG_BYTES, len(data))
            while end < len(data) and _is_utf8_continuation(data[end]):
                end -= 1
            with self.path.open('ab') as log:
                log.write(data[start:end])
            start = end
            if start < len(data):
                _rotate(self.path)


def drain_process_log(output, log):
    """Drain a subprocess pipe continuously, including progress without newlines."""
    decode = getincrementaldecoder('utf-8')(errors='replace')
    with output:
        for data in iter(lambda: output.read1(16 * 1024), b''):
            log.write(decode.decode(data))
        log.write(decode.decode(b'', final=True))
