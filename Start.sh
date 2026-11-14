#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
    echo 'Dieses Paket benötigt Linux x86-64. / This package requires Linux x86-64.' >&2
    exit 1
fi

python=${RESTORENATE_PYTHON:-python3.12}
if ! "$python" -c 'import sys, tkinter; sys.exit(sys.version_info[:2] != (3, 12))'; then
    echo 'Python 3.12 mit Tk und venv benötigt. / Python 3.12 with Tk and venv is required.' >&2
    exit 1
fi

environment=runtime/linux-app
signature=$(sha256sum requirements-linux.txt)
if [[ ! -x $environment/bin/python || ! -f $environment/.ready || $(<"$environment/.ready") != "$signature" ]]; then
    "$python" -m venv "$environment"
    "$environment/bin/python" -I -m pip --isolated --disable-pip-version-check install \
        --no-cache-dir --only-binary=:all: --index-url https://pypi.org/simple -r requirements-linux.txt
    "$environment/bin/python" -I -c 'import tkinter, customtkinter, numpy, onnxruntime; from PIL import Image'
    printf '%s\n' "$signature" > "$environment/.ready"
fi

exec "$environment/bin/python" -I -X utf8 _internal/bootstrap.py --gui
