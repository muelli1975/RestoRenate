"""Rebuild one published Windows ZIP from its own versioned, verified payload."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from freeze_windows import build_windows_gui
from repack_portable import extract, zip_portable


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", *args], encoding="utf-8"))


def build(version, output):
    tag = f"v{version}"
    name = f"RestoRenate_{version}_Windows_x64.zip"
    output.mkdir(parents=True, exist_ok=True)
    release = gh_json("release", "view", tag, "--json", "assets")
    asset = next(a for a in release["assets"] if a["name"] == name)
    with tempfile.TemporaryDirectory() as folder:
        temp = Path(folder)
        subprocess.run(["gh", "release", "download", tag, "-p", name, "-D", str(temp)], check=True)
        archive = temp / name
        old = digest(archive)
        if asset["digest"] != "sha256:" + old:
            raise ValueError(f"Invalid original ZIP digest for {tag}")
        extract(archive, temp / "stage")
        package = temp / "stage/RestoRenate"
        build_windows_gui(package)
        result = output / name
        zip_portable(package.parent, result)
        with ZipFile(result) as zipped:
            zipped.extractall(temp / "tested")
        subprocess.run(["pwsh", "-NoProfile", "-File", str(Path(__file__).resolve().parents[1] /
                        "tests/windows_exe.ps1"), str(temp / "tested/RestoRenate"), version], check=True)
        (output / "refresh.json").write_text(json.dumps({"tag": tag, "name": name, "before": old,
                                                         "after": digest(result)}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", choices=["1.0", "1.1", "1.2", "1.3"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.version, args.output)
