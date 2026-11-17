from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlencode

from repack import HERE, sha256

REPO = os.environ["GH_REPO"]
API = f"repos/{REPO}/releases"
STAGED = ".settings-update"
BACKUP = ".settings-backup"
NOTE = """## Speicherort der Einstellungen / Settings location

Die Pakete speichern Einstellungen und eigene Presets als `settings.json` direkt im Programmordner. Beim Umstieg von einem früheren Paket RestoRenate schließen und die Datei einmal aus dem Unterordner `settings` direkt in den Programmordner verschieben.

The packages store settings and custom presets in `settings.json` at the top level of the program folder. When updating from an earlier package, close RestoRenate and move the existing file from the `settings` subfolder to the program folder.
"""


def api(endpoint, method="GET", payload=None):
    args = ["gh", "api", "--method", method, endpoint]
    if payload is not None:
        args += ["--input", "-"]
    result = subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                            text=True, stdout=subprocess.PIPE, check=True)
    return json.loads(result.stdout) if result.stdout else None


def get_release(plan):
    release = api(f"{API}/{plan['id']}")
    if plan["draft"] and release["draft"] and release["tag_name"].startswith("untagged-"):
        api(f"{API}/{plan['id']}", "PATCH", {"tag_name": plan["tag"]})
        release = api(f"{API}/{plan['id']}")
    assert release["tag_name"] == plan["tag"], (plan["tag"], release["tag_name"])
    assert release["draft"] == plan["draft"] and release["prerelease"] == plan["prerelease"]
    assert release["immutable"] is False
    return release


def by_name(release):
    return {asset["name"]: asset for asset in release["assets"]}


def matches(asset, digest):
    return asset is not None and asset["state"] == "uploaded" and asset["digest"] == f"sha256:{digest}"


def rename(asset, name, label):
    result = api(f"{API}/assets/{asset['id']}", "PATCH", {"name": name, "label": label})
    assert result["name"] == name
    return result


def upload(plan, asset):
    old = by_name(get_release(plan))
    name = asset["name"]
    digest = asset["new_digest"]
    if matches(old.get(name), digest) or matches(old.get(name + STAGED), digest):
        return
    current = old.get(name + STAGED)
    if current is not None:
        assert current["state"] == "starter", current
        api(f"{API}/assets/{current['id']}", "DELETE")
    query = urlencode({"name": name + STAGED, "label": asset["label"]})
    url = f"https://uploads.github.com/repos/{REPO}/releases/{plan['id']}/assets?{query}"
    auth = f'header = "Authorization: Bearer {os.environ["GH_TOKEN"]}"\n'
    args = ["curl", "--fail-with-body", "--silent", "--show-error", "--config", "-",
            "--connect-timeout", "20", "--max-time", "360", "-X", "POST",
            "-H", "Content-Type: application/octet-stream", "--data-binary", f"@{asset['file']}", url]
    result = subprocess.run(args, input=auth, text=True, stdout=subprocess.PIPE, check=True)
    assert matches(json.loads(result.stdout), digest), name


def swap(plan, asset):
    name = asset["name"]
    items = by_name(get_release(plan))
    active = items.get(name)
    if matches(active, asset["new_digest"]):
        return
    waiting = items[name + STAGED]
    assert matches(waiting, asset["new_digest"]), name
    backup = items.get(name + BACKUP)
    if active is not None:
        assert matches(active, asset["digest"]), name
        assert backup is None, name
        backup = rename(active, name + BACKUP, asset["label"])
    assert matches(backup, asset["digest"]), name
    try:
        activated = rename(waiting, name, asset["label"])
        assert matches(activated, asset["new_digest"]), name
    except Exception:
        present = by_name(get_release(plan))
        if name not in present:
            rename(backup, name, asset["label"])
        raise


def prepare(plan, candidates):
    release = get_release(plan)
    items = by_name(release)
    updates = []
    for asset in plan["assets"]:
        name = asset["name"]
        if name == "SHA256SUMS.txt":
            continue
        if not name.endswith((".zip", ".tar.gz")):
            assert matches(items.get(name), asset["digest"]), name
            continue
        source = candidates[asset["digest"]]
        digest = source.with_name(f"{source.name}.sha256").read_text(encoding="utf-8").strip()
        assert sha256(source) == digest
        updates.append(dict(asset, file=source, new_digest=digest))
    sums = next(asset for asset in plan["assets"] if asset["name"] == "SHA256SUMS.txt")
    new_sums = Path("checksums") / plan["tag"] / sums["name"]
    new_sums.parent.mkdir(parents=True, exist_ok=True)
    new_sums.write_text("".join(f"{a['new_digest']}  {a['name']}\n"
                                for a in sorted(updates, key=lambda a: a["name"])), encoding="utf-8")
    body = (release["body"] or "").rstrip()
    for asset in updates:
        body = body.replace(asset["digest"], asset["new_digest"])
        if not plan["draft"]:
            assert asset["new_digest"] in body, (plan["tag"], asset["name"])
    if NOTE.splitlines()[0] not in body:
        link = f"https://github.com/{REPO}/pull/4"
        body += f"\n\n{NOTE}\n[Änderung im Quellcode / Source change]({link})\n"
    updates.append(dict(sums, file=new_sums, new_digest=sha256(new_sums)))
    for item in updates:
        name = item["name"]
        active = items.get(name)
        backup = items.get(name + BACKUP)
        assert (matches(active, item["digest"]) or matches(active, item["new_digest"])
                or (active is None and matches(backup, item["digest"]))), name
    return updates, body


def execute():
    plans = json.loads((HERE / "releases.json").read_text(encoding="utf-8"))
    candidates = {}
    for plan in plans:
        if not plan["draft"]:
            for asset in plan["assets"]:
                if asset["name"].endswith((".zip", ".tar.gz")):
                    matches_on_disk = list(Path("staged").glob(f"*/{plan['tag']}/{asset['name']}"))
                    path, = matches_on_disk
                    candidates[asset["digest"]] = path
    bundle = [(plan, *prepare(plan, candidates)) for plan in plans]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [pool.submit(upload, plan, asset) for plan, assets, _ in bundle for asset in assets]
        for task in tasks:
            task.result()
    print("All replacement assets uploaded and verified by SHA-256.", flush=True)

    for plan, assets, body in bundle:
        for asset in assets:
            swap(plan, asset)
        current = get_release(plan)
        if (current["body"] or "").rstrip() != body.rstrip():
            updated = api(f"{API}/{plan['id']}", "PATCH", {"body": body, "tag_name": plan["tag"]})
            assert updated["body"].rstrip() == body.rstrip()
        print(f"{plan['tag']}: archives, checksum list and release notes updated.", flush=True)

    for plan, assets, body in bundle:
        items = by_name(get_release(plan))
        for asset in assets:
            name = asset["name"]
            assert matches(items.get(name), asset["new_digest"]), name
            backup = items.get(name + BACKUP)
            if backup is not None:
                assert matches(backup, asset["digest"])
                api(f"{API}/assets/{backup['id']}", "DELETE")
        assert set(by_name(get_release(plan))) == {a["name"] for a in plan["assets"]}
        print(f"{plan['tag']}: final names and digests verified.", flush=True)
    if api(f"{API}/latest")["tag_name"] != "v1.3":
        release = next(plan for plan in plans if plan["tag"] == "v1.3")
        api(f"{API}/{release['id']}", "PATCH", {"make_latest": "true", "tag_name": "v1.3"})
    assert api(f"{API}/latest")["tag_name"] == "v1.3"


if __name__ == "__main__":
    execute()
