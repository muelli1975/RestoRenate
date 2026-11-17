from copy import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
PLATFORMS = {"windows": "Windows", "macos": "macOS", "linux": "Linux"}
OLD_PATHS = {
    "RestoRenate/_internal/app.py": b"ROOT / 'settings' / 'settings.json'",
    "RestoRenate/_internal/bootstrap.py": b"ROOT / 'settings/settings.json'",
}
DE = ("Einstellungen und eigene Presets stehen in settings.json direkt im Programmordner. "
      "Bei einem Update aus einer älteren Ausgabe die vorhandene Datei aus dem Unterordner settings "
      "direkt in den Programmordner verschieben.")
EN = ("The settings and custom presets are stored in settings.json at the top level of the program folder. "
      "When updating an older build, move the existing file from the settings subfolder to the program folder.")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def member_path(name):
    return name.removeprefix("./").rstrip("/")


def update_readme(name, data):
    text = data.decode("utf-8")
    ending = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    old_de = "Modelle, Einstellungen und eigene Presets lassen sich weiterverwenden."
    old_en = "Models, settings and custom presets\ncan be reused."
    if old_de in text:
        text = text.replace(old_de, f"Modelle lassen sich weiterverwenden. {DE}", 1)
    elif name.endswith("README_DE.md"):
        text = text.replace(", `settings` sowie", " sowie").rstrip() + f"\n\n{DE}\n"
    if old_en in text:
        text = text.replace(old_en, f"Models can be reused. {EN}", 1)
    elif name.endswith(("README_EN.md", "README.md")):
        text = text.replace(", `settings` and", " and").rstrip() + f"\n\n{EN}\n"
    assert "settings.json" in text, name
    return text.replace("\n", ending).encode("utf-8")


def update_entry(name, data):
    if name in OLD_PATHS:
        old = OLD_PATHS[name]
        assert data.count(old) == 1, name
        patched = data.replace(old, b"ROOT / 'settings.json'")
        compile(patched, name, "exec")
        return patched
    return update_readme(name, data)


def is_update(name):
    return name in OLD_PATHS or name in {
        f"RestoRenate/{readme}" for readme in ("README.md", "README_DE.md", "README_EN.md", "README_DE_EN.txt")
    }


def check_name(name):
    path = member_path(name)
    assert path not in {"RestoRenate/settings.json", "RestoRenate/settings"}
    assert not path.startswith("RestoRenate/settings/")
    return path


def repack(original, target):
    changed = set()
    if original.suffix == ".zip":
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(target, "w", compresslevel=6) as dst:
            dst.comment = src.comment
            for info in src.infolist():
                name = check_name(info.filename)
                output_info = copy(info)
                if is_update(name):
                    dst.writestr(output_info, update_entry(name, src.read(info)))
                    changed.add(name)
                else:
                    with src.open(info) as data, dst.open(output_info, "w") as output:
                        shutil.copyfileobj(data, output, 1024 * 1024)
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(target) as dst:
            before, after = src.infolist(), dst.infolist()
            assert [i.filename for i in before] == [i.filename for i in after]
            for a, b in zip(before, after, strict=True):
                assert a.external_attr == b.external_attr
                if member_path(a.filename) not in changed:
                    assert (a.CRC, a.file_size) == (b.CRC, b.file_size), a.filename
            assert dst.testzip() is None
    else:
        with tarfile.open(original, "r|gz") as src, target.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w|") as dst:
                    for info in src:
                        name = check_name(info.name)
                        data = src.extractfile(info) if info.isreg() else None
                        output_info = copy(info)
                        if is_update(name):
                            patched = update_entry(name, data.read())
                            output_info.size = len(patched)
                            data = io.BytesIO(patched)
                            changed.add(name)
                        dst.addfile(output_info, data)
    assert changed >= OLD_PATHS.keys(), changed
    assert len(changed) > len(OLD_PATHS), changed


def launch_smoke(archive, platform):
    with tempfile.TemporaryDirectory(prefix="rr-settings-") as tmp:
        folder = Path(tmp)
        if platform == "macos":
            args = ["ditto", "-x", "-k", str(archive), tmp]
        elif platform == "linux":
            args = ["tar", "-xzf", str(archive), "-C", tmp]
        else:
            args = [sys.executable, "-m", "zipfile", "-e", str(archive), tmp]
        subprocess.run(args, check=True)
        root = folder / "RestoRenate"
        runtime = "runtime/python/python.exe" if platform == "windows" else "runtime/python/bin/python3.12"
        subprocess.run([str(root / runtime), "-I", "-X", "utf8", str(HERE / "smoke.py"), str(root)], check=True)


def main():
    platform = sys.argv[1]
    destination = Path("candidates").resolve()
    original_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "original").resolve()
    releases = json.loads((HERE / "releases.json").read_text(encoding="utf-8"))
    for release in releases:
        if release["draft"]:
            continue
        tag = release["tag"]
        asset, = (a for a in release["assets"] if PLATFORMS[platform] in a["name"])
        name = asset["name"]
        original = original_dir / tag / name
        original.parent.mkdir(parents=True, exist_ok=True)
        if not original.exists():
            subprocess.run(["curl", "-fsSL", "--retry", "4", "-o", str(original), asset["url"]], check=True)
        assert sha256(original) == asset["digest"], name
        target = destination / tag / name
        target.parent.mkdir(parents=True, exist_ok=True)
        repack(original, target)
        launch_smoke(target, platform)
        digest = sha256(target)
        target.with_name(f"{name}.sha256").write_text(f"{digest}\n", encoding="utf-8")
        print(f"{tag} {name} {digest}", flush=True)


if __name__ == "__main__":
    main()
