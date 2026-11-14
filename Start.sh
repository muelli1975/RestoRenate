#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "$(uname -s):$(uname -m)" in
    Linux:x86_64) environment=runtime/linux-app ;;
    Darwin:arm64)
        if [[ $(sw_vers -productVersion | cut -d. -f1) -lt 15 ]]; then
            echo 'macOS 15 oder neuer erforderlich. / macOS 15 or newer is required.' >&2
            exit 1
        fi
        environment=runtime/macos-app
        export PATH="/opt/homebrew/bin:$PATH"
        ;;
    *)
        echo 'Linux x86-64 oder Apple Silicon erforderlich. / Linux x86-64 or Apple Silicon is required.' >&2
        exit 1
        ;;
esac

python=${RESTORENATE_PYTHON:-python3.12}
if ! "$python" -c 'import sys, tkinter; sys.exit(sys.version_info[:2] != (3, 12))'; then
    echo 'Python 3.12 mit Tk und venv benötigt. / Python 3.12 with Tk and venv is required.' >&2
    exit 1
fi

requirements=requirements-unix.txt
signature=$("$python" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$requirements")
if [[ ! -x $environment/bin/python || ! -f $environment/.ready || $(<"$environment/.ready") != "$signature" ]]; then
    "$python" -m venv "$environment"
    "$environment/bin/python" -I -m pip --isolated --disable-pip-version-check install \
        --no-cache-dir --only-binary=:all: --index-url https://pypi.org/simple -r "$requirements"
    "$environment/bin/python" -I -c 'import tkinter, customtkinter, numpy, onnxruntime; from PIL import Image'
    printf '%s\n' "$signature" > "$environment/.ready"
fi

exec "$environment/bin/python" -I -X utf8 _internal/bootstrap.py --gui
