"""ComfyUI graphs for single-photo restoration."""
from methods import (FIRERED_LIGHTNING, NUNCHAKU_LOADER, QWEN2509_LIGHTNING,
                     QWEN2509_NUNCHAKU, QWEN2511_LIGHTNING)

RESULT_NODE = '14'


def qwen_graph(models, filename, prompt, seed, method):
    graph = {}

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    nunchaku = method == QWEN2509_NUNCHAKU
    four_steps = method in (QWEN2509_NUNCHAKU, QWEN2509_LIGHTNING)
    if nunchaku:
        # Keep one transformer block resident to leave room for activations on smaller GPUs.
        add(1, NUNCHAKU_LOADER, model_name=models['diffusion'], cpu_offload='enable',
            num_blocks_on_gpu=1, use_pin_memory='disable')
    else:
        add(1, 'UnetLoaderGGUF', unet_name=models['diffusion'])
    add(2, 'CLIPLoader', clip_name=models['text'], type='qwen_image', device='default')
    add(3, 'VAELoader', vae_name=models['vae'])
    add(4, 'LoadImage', image=filename)
    sampling_model = ['1', 0]
    if method in (QWEN2509_LIGHTNING, FIRERED_LIGHTNING):
        # These ComfyUI templates apply Lightning before sampling patches.
        add(16, 'LoraLoaderModelOnly', model=sampling_model, lora_name=models['lightning'], strength_model=1.0)
        sampling_model = ['16', 0]
    add(5, 'ModelSamplingAuraFlow', model=sampling_model, shift=3.0 if four_steps else 3.1)
    add(6, 'TextEncodeQwenImageEditPlus', clip=['2', 0], vae=['3', 0], prompt=prompt, image1=['4', 0])
    add(7, 'TextEncodeQwenImageEditPlus', clip=['2', 0], vae=['3', 0], prompt='', image1=['4', 0])
    add(8, 'VAEEncode', pixels=['4', 0], vae=['3', 0])
    add(15, 'CFGNorm', model=['5', 0], strength=1.0)
    model, positive, negative = ['15', 0], ['6', 0], ['7', 0]
    if method == QWEN2511_LIGHTNING:
        add(16, 'LoraLoaderModelOnly', model=model, lora_name=models['lightning'], strength_model=1.0)
        add(17, 'FluxKontextMultiReferenceLatentMethod', conditioning=positive, reference_latents_method='index_timestep_zero')
        add(18, 'FluxKontextMultiReferenceLatentMethod', conditioning=negative, reference_latents_method='index_timestep_zero')
        model, positive, negative = ['16', 0], ['17', 0], ['18', 0]
    add(9, 'KSampler', model=model, positive=positive, negative=negative, latent_image=['8', 0],
        seed=seed, steps=4 if four_steps else 8, cfg=1.0,
        sampler_name='euler', scheduler='simple', denoise=1.0)
    add(10, 'VAEDecode', samples=['9', 0], vae=['3', 0])
    return graph


def fibo2_graph(models, filename, size, prompt, seed):
    # Single-reference edit from the native Turbo template with direct prompt input.
    width, height = size
    graph = {}

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    add(1, 'UNETLoader', unet_name=models['diffusion'], weight_dtype='default')
    add(2, 'CLIPLoader', clip_name=models['text'], type='fibo2', device='default')
    add(3, 'VAELoader', vae_name=models['vae'])
    add(4, 'LoadImage', image=filename)
    add(6, 'TextEncodeFibo2', clip=['2', 0], vae=['3', 0], prompt=prompt, negative_prompt='',
        width=width, height=height, batch_size=1, **{'images.image_1': ['4', 0]})
    add(9, 'KSampler', model=['1', 0], positive=['6', 0], negative=['6', 1], latent_image=['6', 2],
        seed=seed, steps=4, cfg=1.0, sampler_name='euler', scheduler='simple', denoise=1.0)
    add(10, 'VAEDecode', samples=['9', 0], vae=['3', 0])
    return graph


def microsoft_graph(filename, size, scratches, faces):
    width, height = size
    graph = {
        '4': {'class_type': 'LoadImage', 'inputs': {'image': filename}},
        '9': {'class_type': 'FotoRestaurierungMicrosoft', 'inputs': {'image': ['4', 0], 'scratches': scratches}},
    }
    restored = ['9', 0]
    if faces:
        graph['20'] = {'class_type': 'FotoRestaurierungGesichter', 'inputs': {'image': restored}}
        restored = ['20', 0]
    graph['10'] = {'class_type': 'ImageScale', 'inputs': {
        'image': restored, 'upscale_method': 'lanczos', 'width': width, 'height': height, 'crop': 'disabled',
    }}
    return graph


def append_export(graph, crop):
    x, y, width, height = crop
    graph.update({
        '11': {'class_type': 'ImageCrop', 'inputs': {'image': ['10', 0], 'x': x, 'y': y, 'width': width, 'height': height}},
        RESULT_NODE: {'class_type': 'PreviewImage', 'inputs': {'images': ['11', 0]}},
    })
    return graph


def append_upscale(graph, model_name):
    preview = graph[RESULT_NODE]['inputs']
    graph['12'] = {'class_type': 'UpscaleModelLoader', 'inputs': {'model_name': model_name}}
    graph['13'] = {'class_type': 'ImageUpscaleWithModel',
                   'inputs': {'image': preview['images'], 'upscale_model': ['12', 0]}}
    preview['images'] = ['13', 0]
    return graph


def standalone_upscale_graph(filename, model_name):
    graph = {
        '4': {'class_type': 'LoadImage', 'inputs': {'image': filename}},
        RESULT_NODE: {'class_type': 'PreviewImage', 'inputs': {'images': ['4', 0]}},
    }
    return append_upscale(graph, model_name)


def flux2_graph(models, filename, size, prompt, seed):
    width, height = size
    graph = {}

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    add(1, 'UNETLoader', unet_name=models['diffusion'], weight_dtype='default')
    add(2, 'CLIPLoader', clip_name=models['text'], type='flux2', device='default')
    add(3, 'VAELoader', vae_name=models['vae'])
    add(4, 'LoadImage', image=filename)
    add(5, 'CLIPTextEncode', clip=['2', 0], text=prompt)
    add(6, 'CLIPTextEncode', clip=['2', 0], text='')
    add(7, 'VAEEncode', pixels=['4', 0], vae=['3', 0])
    add(8, 'ReferenceLatent', conditioning=['5', 0], latent=['7', 0])
    add(15, 'ReferenceLatent', conditioning=['6', 0], latent=['7', 0])
    add(16, 'EmptyFlux2LatentImage', width=width, height=height, batch_size=1)
    add(17, 'Flux2Scheduler', steps=4, width=width, height=height)
    add(18, 'KSamplerSelect', sampler_name='euler')
    add(19, 'RandomNoise', noise_seed=seed)
    add(20, 'CFGGuider', model=['1', 0], positive=['8', 0], negative=['15', 0], cfg=1.0)
    add(9, 'SamplerCustomAdvanced', noise=['19', 0], guider=['20', 0], sampler=['18', 0],
        sigmas=['17', 0], latent_image=['16', 0])
    add(10, 'VAEDecode', samples=['9', 0], vae=['3', 0])
    return graph
