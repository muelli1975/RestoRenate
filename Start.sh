#!/bin/bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec "$PWD/runtime/python/bin/python3.12" -I -X utf8 _internal/bootstrap.py --gui
