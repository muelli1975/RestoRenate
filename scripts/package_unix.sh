#!/usr/bin/env bash
set -euo pipefail

root=$1
case $(uname -s):$(uname -m) in
    Linux:x86_64)
        platform=x86_64-unknown-linux-gnu
        python_sha=6a9e62dad033790aef722dbd370e0ce76ce17b73627ba3ae679f537049350b39
        ;;
    Darwin:arm64)
        platform=aarch64-apple-darwin
        python_sha=2f11b8aa3726bdbd87dd9eb76568412faddf4f47e26913fa45d6a2e424972acd
        ;;
    *) exit 1 ;;
esac

mkdir -p "$root/_internal" "$root/runtime" "$root/tools"
cp Start.sh README.md README_DE.md README_DE_EN.txt LICENSE THIRD_PARTY.txt "$root/"
cp -r assets vendor "$root/"
cp ./*.py constraints-comfy-unix.txt download_manifest.json method_downloads.json exiftool_restorenate.config "$root/_internal/"

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
curl -fLS --retry 3 "https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.12.16%2B20261110-$platform-install_only_stripped.tar.gz" -o "$stage/python.tar.gz"
printf '%s  %s\n' "$python_sha" "$stage/python.tar.gz" | shasum -a 256 -c -
tar -xzf "$stage/python.tar.gz" -C "$root/runtime"
python="$root/runtime/python/bin/python3.12"
"$python" -I -m pip --isolated --disable-pip-version-check install \
    --no-cache-dir --only-binary=:all: --index-url https://pypi.org/simple -r requirements-unix.txt
"$python" -I -c 'import tkinter, customtkinter, numpy, onnxruntime; from PIL import Image'

exiftool_sha=668ea3acececb7235fbd0f4900e72d5f12c9b07e5c778fd36cb1e9b5828fd65a
curl -fLS --retry 3 https://sourceforge.net/projects/exiftool/files/Image-ExifTool-13.59.tar.gz/download -o "$stage/exiftool.tar.gz"
printf '%s  %s\n' "$exiftool_sha" "$stage/exiftool.tar.gz" | shasum -a 256 -c -
mkdir "$root/tools/exiftool"
tar -xzf "$stage/exiftool.tar.gz" -C "$root/tools/exiftool" --strip-components=1
test "$("$root/tools/exiftool/exiftool" -ver)" = 13.59

comfy_commit=$("$python" -I -c 'import ast; from pathlib import Path; tree = ast.parse(Path("portable_setup.py").read_bytes()); print(next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "COMFY_COMMIT" for target in node.targets)))')
git init --quiet "$stage/comfy"
git -C "$stage/comfy" fetch --quiet --depth=1 https://github.com/Comfy-Org/ComfyUI.git "$comfy_commit"
mkdir "$root/vendor/ComfyUI"
git -C "$stage/comfy" archive --format=tar "$comfy_commit" | tar -xf - -C "$root/vendor/ComfyUI"

chmod +x "$root/Start.sh"
if [[ $(uname -s) == Darwin ]]; then
    bundle="$root/RestoRenate.app/Contents"
    mkdir -p "$bundle/MacOS" "$bundle/Resources"
    cp scripts/macos/Info.plist "$bundle/"
    printf '%s\n' '#!/bin/bash' 'exec "$(dirname -- "$0")/../../../Start.sh"' > "$bundle/MacOS/RestoRenate"
    chmod +x "$bundle/MacOS/RestoRenate"
    "$python" -I -c 'from PIL import Image; import sys; Image.open(sys.argv[1]).save(sys.argv[2])' assets/restorenate.ico "$bundle/Resources/RestoRenate.icns"
    codesign --force --sign - "$root/RestoRenate.app"
fi
