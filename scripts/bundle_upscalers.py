"""Install the classic model weights into a portable package at build time."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from methods import LANCZOS, SEEDVR2, UPSCALERS, UPSCALING, VOSR2, model_specs


def bundle_upscalers(package):
    manifest = json.loads((ROOT / 'download_manifest.json').read_bytes())
    optional = json.loads((ROOT / 'method_downloads.json').read_bytes())
    for name in UPSCALERS:
        if name in (LANCZOS, SEEDVR2, VOSR2):
            continue
        for spec in model_specs(manifest, optional, UPSCALING, upscaler=name):
            relative = Path(spec['path'])
            if relative.parent != Path('models/upscale_models'):
                raise ValueError(f'Unexpected upscaler path: {relative}')
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.part')
            try:
                subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--retry', '3',
                                '--proto', '=https', '--proto-redir', '=https', '--output', str(temporary),
                                spec['url']], check=True)
                with temporary.open('rb') as stream:
                    if temporary.stat().st_size != spec['size'] or hashlib.file_digest(stream, 'sha256').hexdigest() != spec['sha256']:
                        raise ValueError(f'Invalid model size or SHA-256: {relative}')
                temporary.replace(target)
                print(f'Bundled {relative}', flush=True)
            finally:
                temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    bundle_upscalers(Path(sys.argv[1]))
