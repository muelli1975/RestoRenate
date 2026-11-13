"""Choose a CPU thread count for this RestoRenate session."""
import json
import math
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import time


THREAD_VARIABLES = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS')
PROBE_TIMEOUT = 25.0


def cpu_thread_override(env):
    try:
        threads = int(env.get('RESTORENATE_CPU_THREADS', ''))
    except ValueError:
        return None
    return threads if 1 <= threads <= (os.cpu_count() or 1) else None


def thread_candidates(physical, available):
    physical = min(available, physical or available)
    return sorted({1, min(4, available), max(1, physical // 2), physical, available})


def benchmark():
    import psutil
    import torch
    from torch.nn.functional import scaled_dot_product_attention

    available = getattr(os, 'process_cpu_count', os.cpu_count)() or 1
    try:
        available = min(available, len(psutil.Process().cpu_affinity()) or available)
    except (AttributeError, OSError, psutil.Error):
        pass
    physical = min(available, psutil.cpu_count(logical=False) or available)

    # CPU diffusion uses large projections and attention. Keep this probe
    # small enough to run at startup with the installed PyTorch build.
    torch.set_num_threads(1)
    with torch.inference_mode():
        image = torch.ones((768, 2048), dtype=torch.float32)
        weights = torch.ones((2048, 2048), dtype=torch.float32)
        projected = torch.empty((768, 2048), dtype=torch.float32)
        query = torch.ones((1, 8, 512, 64), dtype=torch.float32)

        def sample():
            start = time.perf_counter()
            torch.mm(image, weights, out=projected)
            scaled_dot_product_attention(query, query, query)
            return time.perf_counter() - start

        timings = []
        for threads in thread_candidates(physical, available):
            torch.set_num_threads(threads)
            if torch.get_num_threads() != threads:
                continue
            sample()
            seconds = median(sample() for _ in range(3))
            timings.append((threads, seconds))
    return {'physical': physical, 'available': available, 'timings': timings}


def run_probe(python, root, env, cancelled):
    if cancelled():
        return None
    script = Path(__file__).resolve()
    args = [str(python), '-E', '-s', '-X', 'utf8', str(script)]
    probe_env = dict(env, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with subprocess.Popen(args, cwd=root, env=probe_env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)) as process:
        deadline = time.monotonic() + PROBE_TIMEOUT
        try:
            while not cancelled():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Zeitlimit beim Threadtest erreicht')
                try:
                    output, _ = process.communicate(timeout=min(0.2, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            else:
                return None
            if process.returncode:
                raise RuntimeError(f'Threadtest beendet mit Status {process.returncode}')
            return json.loads(output.decode('utf-8', 'replace').splitlines()[-1])
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


def choose_cpu_threads(python, root, env, cancelled, log):
    try:
        result = run_probe(python, root, env, cancelled)
        if result is None or cancelled():
            return None
        available = result['available']
        physical = result['physical']
        timings = result['timings']
        if not (type(available) is int and type(physical) is int and 1 <= physical <= available
                and timings and all(type(n) is int and 1 <= n <= available
                                    and math.isfinite(t) and t > 0 for n, t in timings)):
            raise ValueError('Ungültiges Ergebnis des Threadtests')
        threads = min(timings, key=lambda item: (item[1], item[0]))[0]
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, IndexError) as exc:
        if cancelled():
            return None
        threads = min(4, os.cpu_count() or 1)
        log.write(f'RestoRenate CPU: Threadtest fehlgeschlagen ({exc}); Ersatzwert {threads}\n')
        return threads
    times = ', '.join(f'{n}: {t * 1000:.1f} ms' for n, t in timings)
    log.write(f'RestoRenate CPU: {physical} Kerne, {available} logische Prozessoren verfügbar; '
              f'Threadtest [{times}]; gewählt: {threads}\n')
    return threads


if __name__ == '__main__':
    print(json.dumps(benchmark()))
