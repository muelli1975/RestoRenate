"""Local ComfyUI workflow and the shared photo-to-file pipeline."""
from __future__ import annotations

import io
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PIL import Image

try:
    import websocket
except ImportError:
    websocket = None

from language import translate
from export_metadata import APP_VERSION, output_graph, set_output_size
from imaging import open_photo, prepare, save_result
from photo_colors import Colorizer
from sizes import (NO_RESCALE, limited_size, method_size, needs_enlargement, output_size,
                   restoration_canvas, restoration_size)
from method_graphs import (
    RESULT_NODE, append_export, append_upscale,
    fibo2_graph, flux2_graph, microsoft_graph, qwen_graph, standalone_upscale_graph,
)
from methods import (COLORIZATION_METHODS, DEFAULT_METHOD, FIBO2_TURBO, FIRERED_METHODS, FLUX2, LANCZOS,
                     METHOD_FILENAME_LABELS, MICROSOFT, NATIVE_METHODS, NUNCHAKU_LOADER, QWEN_METHODS, REALESRGAN,
                     UPSCALE_FILENAME_LABELS, UPSCALE_FILES, UPSCALE_SCALES,
                     TWO_IMAGE_METHODS, UPSCALING, model_files, resolve_upscaler)
from portable_setup import SetupCancelled, contained

PHASES = {
    'LoadImage': 'Bild wird eingelesen',
    'UnetLoaderGGUF': 'Modell wird geladen',
    NUNCHAKU_LOADER: 'Modell wird geladen',
    'UNETLoader': 'Modell wird geladen',
    'CLIPLoader': 'Textencoder wird geladen',
    'VAELoader': 'Bilddecoder wird geladen',
    'LoraLoaderModelOnly': 'Lightning-LoRA wird geladen',
    'ModelSamplingAuraFlow': 'Bearbeitung wird vorbereitet',
    'TextEncodeQwenImageEditPlus': 'Bild und Prompt werden verarbeitet',
    'TextEncodeFibo2': 'Bild und Prompt werden verarbeitet',
    'CLIPTextEncode': 'Prompt wird verarbeitet',
    'VAEEncode': 'Bild wird kodiert',
    'KSampler': 'Bild wird bearbeitet',
    'SamplerCustomAdvanced': 'Bild wird bearbeitet',
    'FotoRestaurierungMicrosoft': 'Bild wird restauriert',
    'FotoRestaurierungGesichter': 'Gesichter werden restauriert',
    'VAEDecode': 'Bild wird dekodiert',
    'ImageCrop': 'Bildränder werden entfernt',
    'ImageScale': 'Ausgabegröße wird angepasst',
    'UpscaleModelLoader': 'Upscaler wird geladen',
    'ImageUpscaleWithModel': 'Bild wird hochskaliert',
    'PreviewImage': 'Vorschau wird erstellt',
}
SAMPLER_NODES = ('KSampler', 'SamplerCustomAdvanced')
STEP_UNITS = {
    'KSampler': 'Schritt', 'SamplerCustomAdvanced': 'Schritt', 'ImageUpscaleWithModel': 'Kachel',
    'FotoRestaurierungMicrosoft': 'Phase', 'FotoRestaurierungGesichter': 'Phase',
}



class Client:
    def __init__(self, server, root):
        self.server = server
        self.root = Path(root)
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, route, data=None, timeout=10):
        body = json.dumps(data).encode('utf-8') if data is not None else None
        request = urllib.request.Request(
            self.server + route, data=body,
            headers={'Content-Type': 'application/json'} if body is not None else {},
        )
        try:
            with self.http.open(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read(12_000).decode('utf-8', 'replace')
            raise RuntimeError(f'ComfyUI HTTP {exc.code}: {detail}') from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(translate('ComfyUI ist nicht erreichbar. Details in logs/backend.log.')) from exc

    def json(self, route, data=None, timeout=10):
        return json.loads(self.request(route, data, timeout))

    def open_progress(self, client_id):
        if websocket is None:
            return None
        route = '/ws?' + urllib.parse.urlencode({'clientId': client_id})
        url = 'ws://' + self.server.removeprefix('http://') + route
        try:
            connection = websocket.create_connection(
                url, timeout=2, http_no_proxy=['127.0.0.1'], enable_multithread=False,
            )
            connection.settimeout(0.25)
            return connection
        except (OSError, websocket.WebSocketException):
            return None

    def device(self):
        try:
            devices = self.json('/system_stats', timeout=2).get('devices', [])
        except RuntimeError:
            return ''
        if not devices:
            return ''
        device = devices[0]
        name = device['name'].split(' : ', 1)[0]
        if device.get('type') == 'cpu' or name.casefold() == 'cpu':
            return 'CPU'
        return name.replace('cuda:', 'CUDA ', 1) if name.startswith('cuda:') else name

    def image(self, descriptor):
        query = urllib.parse.urlencode({key: descriptor.get(key, '') for key in ('filename', 'subfolder', 'type')})
        with Image.open(io.BytesIO(self.request('/view?' + query, timeout=45))) as image:
            return image.convert('RGB')


def select_models(info, method=DEFAULT_METHOD, upscaler=None):
    files = model_files(method, upscaler)
    missing = sorted({entry[0] for entry in files.values()} - info.keys())
    if missing:
        raise RuntimeError(translate('ComfyUI-Komponenten fehlen: ') + ', '.join(missing))
    selected = {}
    for key, (node, field, basename) in files.items():
        field_spec = info[node]['input']['required'][field]
        values = field_spec[1]['options'] if field_spec[0] == 'COMBO' else field_spec[0]
        matches = [value for value in values if value.replace('\\', '/').rsplit('/', 1)[-1] == basename]
        if len(matches) != 1:
            raise RuntimeError(translate('Modelldatei fehlt oder ist mehrdeutig: {0}', basename))
        selected[key] = matches[0]
    return selected


def report_progress(event, graph, prompt_id, status, progress):
    if not isinstance(event, dict):
        return
    kind = event.get('type')
    data = event.get('data')
    if not isinstance(data, dict) or data.get('prompt_id') != prompt_id:
        return
    node_id = str(data.get('node'))
    node = graph.get(node_id)
    if not node:
        return
    node_type = node['class_type']
    phase = translate(PHASES.get(node_type, 'Bild wird bearbeitet'))
    if kind == 'executing':
        if node_type == 'FotoRestaurierungMicrosoft' and node['inputs']['scratches']:
            phase = translate('Kratzer werden gesucht')
        progress(None)
        if node_type in SAMPLER_NODES:
            status(translate('Sampling · Erster Rechenschritt läuft …'))
        else:
            status(phase + ' …')
    elif kind == 'progress':
        unit = STEP_UNITS.get(node_type)
        value, total = data.get('value'), data.get('max')
        if unit and isinstance(value, int) and isinstance(total, int) and 0 <= value <= total and total > 0:
            if value == 0 and node_type in SAMPLER_NODES:
                return
            progress(100 * value / total)
            status(f'{phase} · {translate(unit)} {value}/{total}')


def generate(client, graph, status, cancelled, progress=lambda value: None, node_seconds=None):
    if cancelled():
        raise SetupCancelled(translate('Bearbeitung abgebrochen.'))
    client_id = uuid.uuid4().hex
    connection = client.open_progress(client_id)
    active_node, node_started = None, 0.0

    def finish_node(now):
        if node_seconds is not None and active_node in graph:
            kind = graph[active_node]['class_type']
            node_seconds[kind] = round(node_seconds.get(kind, 0.0) + now - node_started, 2)

    try:
        reply = client.json('/prompt', {'prompt': graph, 'client_id': client_id})
        if reply.get('node_errors') or not reply.get('prompt_id'):
            raise RuntimeError(translate('ComfyUI hat den Workflow abgelehnt: ') + json.dumps(reply, ensure_ascii=False))
        prompt_id = reply['prompt_id']
        unavailable = translate('Bild wird bearbeitet · Fortschritt nicht verfügbar')
        status(translate('Bearbeitung wird vorbereitet') + ' …' if connection else unavailable)
        deadline = time.monotonic() + 4 * 3600
        next_history = 0.0
        while time.monotonic() < deadline:
            if cancelled():
                # The application closes its dedicated backend after the worker returns.
                raise SetupCancelled(translate('Bearbeitung abgebrochen.'))
            if time.monotonic() >= next_history:
                history = client.json('/history/' + prompt_id)
                if prompt_id in history:
                    record = history[prompt_id]
                    state = record.get('status', {})
                    if state.get('status_str') == 'error':
                        for event, detail in state.get('messages', []):
                            if event in ('execution_error', 'execution_interrupted'):
                                raise RuntimeError(detail.get('exception_message') or event)
                        raise RuntimeError(translate('ComfyUI konnte das Bild nicht bearbeiten.'))
                    images = record.get('outputs', {}).get(RESULT_NODE, {}).get('images', [])
                    if len(images) != 1 or images[0].get('type') != 'temp':
                        raise RuntimeError(translate('ComfyUI hat kein eindeutiges Ergebnis geliefert.'))
                    finish_node(time.monotonic())
                    return images[0]
                next_history = time.monotonic() + 0.75
            if connection is None:
                time.sleep(0.25)
                continue
            try:
                message = connection.recv()
                if message == '':
                    raise websocket.WebSocketConnectionClosedException()
            except websocket.WebSocketTimeoutException:
                continue
            except (OSError, websocket.WebSocketException):
                connection.shutdown()
                connection = None
                active_node = None
                progress(None)
                status(unavailable)
            else:
                if isinstance(message, str):
                    try:
                        event = json.loads(message)
                    except ValueError:
                        continue
                    if node_seconds is not None and isinstance(event, dict):
                        data = event.get('data')
                        if isinstance(data, dict) and data.get('prompt_id') == prompt_id:
                            kind, node_id = event.get('type'), str(data.get('node'))
                            if kind == 'executing':
                                now = time.monotonic()
                                finish_node(now)
                                active_node, node_started = node_id, now
                            elif (kind == 'progress' and node_id == active_node and node_id in graph
                                  and graph[node_id]['class_type'] in SAMPLER_NODES
                                  and data.get('value') == 1):
                                node_seconds.setdefault('first_sampling_step', round(time.monotonic() - node_started, 2))
                    report_progress(event, graph, prompt_id, status, progress)
        raise TimeoutError(translate('Die Berechnung hat das Zeitlimit von vier Stunden erreicht.'))
    finally:
        if connection is not None:
            connection.shutdown()


def restoration_graph(method, models, name, size, crop, prompt, seed, scratches, faces, *, second_image=None):
    if method == MICROSOFT:
        graph = microsoft_graph(name, size, scratches, faces)
    elif method == FIBO2_TURBO:
        graph = fibo2_graph(models, name, size, prompt, seed, second_image=second_image)
    elif method == FLUX2:
        graph = flux2_graph(models, name, size, prompt, seed, second_image=second_image)
    elif method in (*QWEN_METHODS, *FIRERED_METHODS):
        graph = qwen_graph(models, name, prompt, seed, method, second_image=second_image)
    else:
        raise ValueError(translate('Unbekanntes Verfahren: {0}', method))
    return append_export(graph, crop)


def processing_settings(record, model_name, graph):
    sampling = []
    for node in (graph or {}).values():
        kind, inputs = node['class_type'], node['inputs']
        if kind in ('KSampler', 'Flux2Scheduler', 'CFGGuider', 'KSamplerSelect'):
            sampling.append({'node': kind, **{key: value for key, value in inputs.items()
                             if isinstance(value, (int, float, str, bool))}})
    used_models = {key: name for key, name in record['models'].items()
                   if key not in UPSCALE_SCALES or name == model_name}
    return {'version': APP_VERSION, 'method': record['method'], 'models': used_models,
            'prompt': record['prompt'], 'seed': record['seed'], 'sampling': sampling,
            'original_size': record['original_size'], 'working_size': record['working_size'],
            'working_crop': record.get('active_crop'), 'output_size': record['output_size'], 'upscaler': model_name,
            **{key: record[key] for key in ('source_crop', 'source_rotation', 'second_image', 'second_rotation', 'second_size')
               if key in record},
            **{key: record[key] for key in ('scratches', 'faces') if key in record}}


def restore(client, models, source, folder, output_format, exiftool, prompt, seed, status, cancelled, record,
            progress=lambda value: None, method=DEFAULT_METHOD, scratches=True, faces=False,
            staged_id=None, size_choice=(None, 2160), upscaler=None, definitions=None, colorizer=None,
            source_crop=None, source_rotation=0, second_image=None, second_rotation=0):
    started = time.monotonic()
    timing = record['seconds_by_stage'] = {}
    status(translate('Bild wird vorbereitet …'))
    progress(None)
    if second_image is not None and method not in TWO_IMAGE_METHODS:
        raise ValueError(translate('Dieses Verfahren verarbeitet nur ein Bild.'))
    original, dpi = open_photo(source, crop=source_crop, rotation=source_rotation)
    choice, side_pixels = size_choice
    choice = method_size(method, choice)
    expected = output_size(original.size, choice, side_pixels, method=method)
    upscaler = resolve_upscaler(method, upscaler)
    source_size = source_crop.original_size if source_crop else original.size
    record.update(original_size=source_size, output_size=expected)
    if source_crop:
        record['source_crop'] = source_crop.box
    if source_rotation:
        record['source_rotation'] = source_rotation
    if second_image is not None:
        record['second_image'] = str(second_image)
        if second_rotation:
            record['second_rotation'] = second_rotation
    if method == MICROSOFT:
        record.update(scratches=scratches, faces=faces)

    def export(image, model_name, graph=None):
        if cancelled():
            raise SetupCancelled(translate('Bearbeitung abgebrochen.'))
        settings = processing_settings(record, model_name, graph)
        labels = []
        if method != UPSCALING:
            labels.append(METHOD_FILENAME_LABELS[method])
        if model_name == LANCZOS:
            labels.append('lanczos')
        elif model_name and upscaler == REALESRGAN:
            labels.append('RealESRGAN-x2' if model_name == models.get('esrgan2') else 'RealESRGAN-x4')
        elif model_name:
            labels.append(UPSCALE_FILENAME_LABELS[upscaler])
        status(translate('Bild wird gespeichert ({0} × {1} px) …', expected[0], expected[1]))
        with (image.copy() if image.size == expected else image.resize(expected, Image.Resampling.LANCZOS)) as result:
            return save_result(result, source, folder, output_format, dpi, exiftool,
                               settings=settings, graph=graph, definitions=definitions, labels=labels)

    native = method in NATIVE_METHODS
    if native:
        if method in COLORIZATION_METHODS:
            status(translate('Bild wird koloriert …'))
            with original:
                prepared = (colorizer or Colorizer(models['colorizer'], method=method)).process(original)
        else:
            prepared = original
        crop = (0, 0, *prepared.size)
        record['working_size'] = prepared.size
        if upscaler == LANCZOS or not needs_enlargement(prepared.size, expected):
            with prepared:
                return export(prepared, LANCZOS if prepared.size != expected else None)
    else:
        size = restoration_size(original.size, method)
        alignment = 32 if method == FLUX2 else 16
        canvas = restoration_canvas(original.size, method)
        prepared, crop = prepare(original, size, alignment=alignment, canvas=canvas)
    if prepared is not original:
        original.close()
    record.update(working_size=prepared.size, active_crop=crop)
    if client is None:
        prepared.close()
        raise RuntimeError(translate('Für dieses Verfahren muss ComfyUI bereit sein.'))
    input_dir = client.root / 'work/input'
    name = 'foto_' + (staged_id or uuid.uuid4().hex) + '.png'
    staged = input_dir / name
    reference = staged.with_name(staged.stem + '_2.png') if second_image is not None else None
    descriptor = None
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        with prepared:
            prepared.save(staged, 'PNG')
        if reference is not None:
            second, _ = open_photo(second_image, rotation=second_rotation)
            with second:
                if method == FLUX2:
                    second_size = restoration_size(second.size, method)
                    second_size = tuple(max(32, round(edge / 32) * 32) for edge in second_size)
                else:
                    second_size = limited_size(second.size, max_pixels=1024**2)
                if second_size == second.size:
                    second.save(reference, 'PNG')
                else:
                    with second.resize(second_size, Image.Resampling.LANCZOS) as resized:
                        resized.save(reference, 'PNG')
            record['second_size'] = second_size
        current = crop[2:]
        use_model = upscaler != LANCZOS and needs_enlargement(current, expected)
        model_name = LANCZOS if current != expected else None
        if use_model:
            if upscaler == REALESRGAN:
                key = 'esrgan2' if all(end <= 2 * start for start, end in zip(current, expected)) else 'esrgan4'
            else:
                key, = UPSCALE_FILES[upscaler]
            scale = UPSCALE_SCALES[key]
            if current[0] * current[1] * scale**2 > 100_000_000:
                raise ValueError(translate('Dieses Modell würde intern mehr als 100 Megapixel erzeugen. Wähle Lanczos oder eine kleinere Eingabedatei.'))
            model_name = models[key]
        if native:
            graph = standalone_upscale_graph(name, model_name)
        else:
            graph = restoration_graph(method, models, name, record['working_size'], crop, prompt, seed, scratches, faces,
                                      second_image=reference.name if reference is not None else None)
            if use_model:
                append_upscale(graph, model_name)
        if choice != NO_RESCALE:
            set_output_size(graph, RESULT_NODE, expected)
        timing['prepare'] = round(time.monotonic() - started, 2)
        graph_started = time.monotonic()
        nodes = timing['comfy_nodes'] = {}
        descriptor = generate(client, graph, status, cancelled, progress, nodes)
        timing['comfy_total'] = round(time.monotonic() - graph_started, 2)
        progress(None)
        status(translate('Ergebnis wird übertragen …'))
        with client.image(descriptor) as upscaled:
            if upscaled.size != expected:
                raise RuntimeError(translate(
                                       'Unerwartete Ausgabegröße: {0} × {1} px.',
                                       upscaled.width, upscaled.height,
                                   ))
            return export(upscaled, model_name, output_graph(graph, RESULT_NODE))
    finally:
        staged.unlink(missing_ok=True)
        if reference is not None:
            reference.unlink(missing_ok=True)
        if descriptor is not None:
            relative = Path(descriptor.get('subfolder', '')) / descriptor['filename']
            contained(client.root / 'work/temp/temp', relative).unlink(missing_ok=True)
