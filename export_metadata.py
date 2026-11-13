"""Serialize the executed Comfy graph and its editable representation."""
import json
from pathlib import Path

APP_NAME = 'RestoRenate'
APP_VERSION = '0.2.83'
MAX_SEED = 2**64 - 1
PRIMITIVES = {'INT', 'FLOAT', 'STRING', 'BOOLEAN', 'COMBO', 'COMFY_DYNAMICCOMBO_V3'}


def compact(data, *, ascii_only=False):
    return json.dumps(data, ensure_ascii=ascii_only, separators=(',', ':'))


def connected(value, graph):
    return (isinstance(value, list) and len(value) == 2 and
            isinstance(value[0], str) and value[0] in graph and isinstance(value[1], int))


def parse_seed(value):
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 20:
        value = int(value)
    return value if type(value) is int and 0 <= value <= MAX_SEED else None


def seed_from_metadata(metadata):
    # The API graph preserves the exact seed, including values above 2**53.
    for field in ('prompt', 'workflow'):
        raw = metadata.get(field)
        if not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except (ValueError, RecursionError):
            continue
        if not isinstance(data, dict):
            continue
        nodes = data.values() if field == 'prompt' else data.get('nodes', [])
        if field == 'workflow' and not isinstance(nodes, list):
            continue
        seeds = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            kind = node.get('class_type' if field == 'prompt' else 'type')
            if kind not in ('KSampler', 'KSamplerAdvanced', 'RandomNoise'):
                continue
            if field == 'prompt':
                inputs = node.get('inputs')
                value = inputs.get('seed' if kind == 'KSampler' else 'noise_seed') if isinstance(inputs, dict) else None
            else:
                widgets = node.get('widgets_values')
                slot = int(kind == 'KSamplerAdvanced')
                value = widgets[slot] if isinstance(widgets, list) and len(widgets) > slot else None
            seed = parse_seed(value)
            if seed is not None:
                seeds.add(seed)
        if len(seeds) > 1:
            return None
        if seeds:
            return seeds.pop()
    return None


def editable_workflow(graph, definitions, source_name, *, second_image=None):
    """Translate the API graph using the running ComfyUI node definitions."""
    nodes, links = {}, []
    # Graph insertion order follows dependencies in the API graphs produced by the app.
    for order, (key, spec) in enumerate(graph.items()):
        kind = spec['class_type']
        definition = definitions.get(kind, {})
        values = spec['inputs']
        slots, widgets = [], []
        fields = {}
        field_groups = definition.get('input', {})
        field_order = definition.get('input_order', {})
        for group in ('required', 'optional'):
            inputs = field_groups.get(group, {})
            for name in field_order.get(group, inputs):
                if name not in inputs:
                    continue
                signature = inputs[name]
                if signature[0] == 'COMFY_AUTOGROW_V3':
                    template = signature[1]['template']
                    field, = (item for group in template['input'].values() for item in group.values())
                    prefix = name + '.'
                    fields.update((key, field) for key in values if key.startswith(prefix))
                else:
                    fields[name] = signature
        for name in (*fields, *(name for name in values if name not in fields)):
            signature = fields.get(name, ('*',))
            field_type = signature[0]
            options = signature[1] if len(signature) > 1 else {}
            is_widget = (isinstance(field_type, list) or field_type in PRIMITIVES) and not options.get('forceInput')
            value = values.get(name, options.get('default'))
            is_link = connected(value, graph)
            if is_widget:
                if value is None or is_link:
                    choices = field_type if isinstance(field_type, list) else options.get('options', [])
                    value = options.get('default', choices[0] if choices else None)
                if kind == 'LoadImage' and name == 'image':
                    value = second_image if key == '30' and second_image else source_name
                widgets.append(value)
                if options.get('control_after_generate'):
                    widgets.append('fixed')
                if options.get('image_upload'):
                    widgets.append('image')
            if not is_widget or is_link:
                slot_type = field_type if isinstance(field_type, str) else 'COMBO'
                slot = {'name': name, 'type': slot_type, 'link': None}
                if is_link:
                    origin, output = values[name]
                    link_id = len(links) + 1
                    slot['link'] = link_id
                    links.append([link_id, int(origin), output, int(key), len(slots), slot_type])
                    if is_widget:
                        slot['widget'] = {'name': name}
                slots.append(slot)
        outputs = [{'name': name, 'type': kind, 'links': [], 'slot_index': slot}
                   for slot, (name, kind) in enumerate(zip(definition.get('output_name', definition.get('output', [])),
                                                          definition.get('output', [])))]
        nodes[int(key)] = {'id': int(key), 'type': spec['class_type'], 'pos': [40 + order % 5 * 350, 120 + order // 5 * 430],
                           'size': [310, 240], 'flags': {}, 'order': order, 'mode': 0,
                           'inputs': slots, 'outputs': outputs, 'properties': {'Node name for S&R': spec['class_type']},
                           'widgets_values': widgets}
    for link_id, origin, slot, _, _, _ in links:
        outputs = nodes[origin]['outputs']
        if slot < len(outputs):
            outputs[slot]['links'].append(link_id)
    return {'last_node_id': max(nodes, default=0), 'last_link_id': len(links), 'nodes': list(nodes.values()),
            'links': links, 'groups': [], 'config': {}, 'extra': {'ds': {'scale': 0.75, 'offset': [0, 0]}},
            'version': 0.4}


def editor_graph(graph, settings):
    """Recreate the input crop and working-size preparation on the original photo."""
    source_crop = settings.get('source_crop')
    working_crop = settings.get('working_crop')
    rotation = settings.get('source_rotation', 0)
    second_size = settings.get('second_size')
    if not (source_crop or working_crop or rotation or second_size):
        return graph
    prepared = {}
    result = ['4', 0]
    input_size = tuple(settings['original_size'])
    if rotation:
        prepared['93'] = {'class_type': 'ImageRotate', 'inputs': {
            'image': result, 'rotation': f'{rotation * 90} degrees',
        }}
        result = ['93', 0]
    if source_crop:
        x, y, right, bottom = source_crop
        input_size = right - x, bottom - y
        prepared['90'] = {'class_type': 'ImageCrop', 'inputs': {
            'image': result, 'x': x, 'y': y, 'width': input_size[0], 'height': input_size[1],
        }}
        result = ['90', 0]
    if working_crop:
        left, top, width, height = working_crop
        working_width, working_height = settings['working_size']
        if (width, height) != input_size:
            prepared['91'] = {'class_type': 'ImageScale', 'inputs': {
                'image': result, 'upscale_method': 'lanczos', 'width': width, 'height': height, 'crop': 'disabled',
            }}
            result = ['91', 0]
        right, bottom = working_width - width - left, working_height - height - top
        if left or top or right or bottom:
            prepared['92'] = {'class_type': 'ImagePadForOutpaint', 'inputs': {
                'image': result, 'left': left, 'top': top, 'right': right, 'bottom': bottom, 'feathering': 0,
            }}
            result = ['92', 0]
    if second_size and '30' in graph:
        prepared['94'] = {'class_type': 'ImageScale', 'inputs': {
            'image': ['30', 0], 'upscale_method': 'lanczos',
            'width': second_size[0], 'height': second_size[1], 'crop': 'disabled',
        }}
    if not prepared:
        return graph
    out = {'4': graph['4']}
    if '30' in graph:
        out['30'] = graph['30']
    out.update(prepared)
    replacements = {'4': result, '30': ['94', 0]} if '94' in prepared else {'4': result}
    for node_id, node in graph.items():
        if node_id not in out:
            inputs = {name: replacements.get(value[0], value) if connected(value, graph) and value[1] == 0 else value
                      for name, value in node['inputs'].items()}
            out[node_id] = {**node, 'inputs': inputs}
    return out


def png_metadata(settings, graph, definitions, source_name):
    if not graph:
        return {}
    second = settings.get('second_image')
    workflow = editable_workflow(editor_graph(graph, settings), definitions, source_name,
                                 second_image=Path(second).name if second else None)
    return {'prompt': compact(graph, ascii_only=True), 'workflow': compact(workflow, ascii_only=True)}


def set_output_size(graph, node_id, size):
    """Resize before preview so the exact exported dimensions are part of the executed graph."""
    preview = graph.pop(node_id)
    graph['80'] = {'class_type': 'ImageScale', 'inputs': {
        'image': preview['inputs']['images'], 'upscale_method': 'lanczos',
        'width': size[0], 'height': size[1], 'crop': 'disabled',
    }}
    preview['inputs']['images'] = ['80', 0]
    graph[node_id] = preview


def output_graph(graph, node_id):
    """Keep only the branch that produced this specific image."""
    required = set()

    def visit(key):
        if key in required:
            return
        required.add(key)
        for value in graph[key]['inputs'].values():
            if connected(value, graph):
                visit(value[0])

    visit(node_id)
    return {key: node for key, node in graph.items() if key in required}
