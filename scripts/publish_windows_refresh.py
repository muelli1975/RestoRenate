"""Replace only the tested Windows asset and its checksum; preserve release prose."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def gh(*args, data=None):
    return subprocess.check_output(["gh", *map(str, args)], input=data)


def api(endpoint, method="GET", **fields):
    options = ["api", endpoint, "-X", method]
    return gh(*options, "--input", "-", data=json.dumps(fields).encode()) if fields else gh(*options)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def update(folder):
    record = json.loads((folder / "refresh.json").read_bytes())
    tag, name = record["tag"], record["name"]
    repo = "repos/" + os.environ["GITHUB_REPOSITORY"]
    endpoint = repo + "/releases/assets/"
    release = json.loads(api(repo + "/releases/tags/" + tag))
    assets = {a["name"]: a for a in release["assets"]}
    package = folder / name
    old, new = record["before"], record["after"]
    if sha(package.read_bytes()) != new or assets[name]["digest"] != "sha256:" + old:
        raise ValueError(f"Release changed or artifact checksum mismatch for {tag}")
    staged = {}
    moved = {}
    promoted = {}
    body = release["body"]
    if body.count(old) != 1:
        raise ValueError(f"Unexpected download table for {tag}")
    with TemporaryDirectory() as tmp:
        stage = Path(tmp)
        manifest = "SHA256SUMS.txt"
        gh("release", "download", tag, "-p", manifest, "-D", stage)
        previous = (stage / manifest).read_bytes()
        if sha(previous) != assets[manifest]["digest"].removeprefix("sha256:") or previous.count(old.encode()) != 1:
            raise ValueError(f"Unexpected checksum file for {tag}")
        (stage / manifest).write_bytes(previous.replace(old.encode(), new.encode()))
        files = {name: package, manifest: stage / manifest}
        suffix = "." + os.environ["GITHUB_RUN_ID"] + "." + os.environ["GITHUB_RUN_ATTEMPT"]
        try:
            for key, file in files.items():
                pending = stage / (key + suffix + ".pending")
                pending.write_bytes(file.read_bytes())
                gh("release", "upload", tag, pending)
                uploaded = json.loads(api(repo + "/releases/tags/" + tag))["assets"]
                item = next(a for a in uploaded if a["name"] == pending.name)
                staged[key] = item["id"]
                if item["digest"] != "sha256:" + sha(file.read_bytes()):
                    raise ValueError(f"Upload checksum mismatch for {key}")
            for key in files:
                ident = assets[key]["id"]
                api(endpoint + str(ident), "PATCH", name=key + suffix + ".previous")
                moved[key] = ident
                api(endpoint + str(staged[key]), "PATCH", name=key)
                promoted[key] = staged[key]
            api(repo + "/releases/" + str(release["id"]), "PATCH", body=body.replace(old, new))
            for key, file in files.items():
                gh("release", "download", tag, "-p", key, "-D", stage / "verify")
                if sha((stage / "verify" / key).read_bytes()) != sha(file.read_bytes()):
                    raise ValueError(f"Published download mismatch for {key}")
        except BaseException:
            for key, ident in promoted.items():
                api(endpoint + str(ident), "PATCH", name=key + suffix + ".pending")
            for key, ident in moved.items():
                api(endpoint + str(ident), "PATCH", name=key)
            if moved:
                api(repo + "/releases/" + str(release["id"]), "PATCH", body=body)
            for ident in staged.values():
                api(endpoint + str(ident), "DELETE")
            raise
        for ident in moved.values():
            api(endpoint + str(ident), "DELETE")
        print(f"{tag}: verified public Windows download {new}", flush=True)


if __name__ == "__main__":
    for path in sorted(Path(sys.argv[1]).glob("*/refresh.json"), reverse=True):
        update(path.parent)
