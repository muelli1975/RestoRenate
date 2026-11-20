"""Freeze the GUI from exactly the application and dependencies in a portable folder."""
from importlib.metadata import distribution, distributions
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MANIFEST = "pyinstaller-files.json"


def build_windows_gui(package):
    package = package.resolve()
    code = package / "_internal"
    if not (code / "app.py").is_file():
        code = package
    icon = next(p for p in (package / "assets/restorenate.ico", package / "restorenate.ico") if p.is_file())
    # Match the GUI libraries of the release being rebuilt, including older versions.
    site = package / "runtime/python/Lib/site-packages"
    dependencies = sorted(f"{d.metadata['Name']}=={d.version}" for d in distributions(path=[str(site)]))
    if not dependencies:
        raise ValueError("Missing portable GUI dependencies")
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:", *dependencies], check=True)
    with TemporaryDirectory(prefix="rr-freeze-") as tmp:
        stage = Path(tmp)
        subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "--noupx",
                        "--onedir", "--windowed", "--name", "RestoRenate", "--icon", str(icon),
                        "--contents-directory", "." if code == package else "_internal",
                        "--paths", str(code), "--collect-data", "customtkinter",
                        "--distpath", str(stage / "dist"), "--workpath", str(stage / "work"),
                        "--specpath", str(stage), str(HERE / "windows_gui.py")], cwd=stage, check=True)
        frozen = stage / "dist/RestoRenate"
        manifest = package / "licenses" / MANIFEST
        manifest.parent.mkdir(exist_ok=True)
        if manifest.exists():
            for name in json.loads(manifest.read_text(encoding="utf-8"))["files"]:
                path = (package / name).resolve()
                if not path.is_relative_to(package):
                    raise ValueError("Unexpected PyInstaller file path")
                path.unlink(missing_ok=True)
        files = sorted(p.relative_to(frozen).as_posix() for p in frozen.rglob("*") if p.is_file())
        for name in files:
            dest = package / name
            if dest.exists() and name != "RestoRenate.exe":
                raise ValueError(f"PyInstaller output collides with an existing package file: {name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(frozen / name, dest)
        installer = distribution("PyInstaller")
        license_file = next(f for f in installer.files if f.name == "COPYING.txt")
        shutil.copy2(installer.locate_file(license_file), manifest.parent / "PyInstaller-COPYING.txt")
        manifest.write_text(json.dumps({"pyinstaller": installer.version, "files": files,
                                        "packaging_commit": os.environ.get("GITHUB_SHA")}, indent=2),
                            encoding="utf-8")
