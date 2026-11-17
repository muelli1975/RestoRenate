"""ComfyUI graphs for single-photo restoration."""
from methods import (FIRERED_BASE, NUNCHAKU_LOADER, QWEN2509_BASE, QWEN2509_GGUF_METHODS,
                     QWEN2509_LIGHTNING_4, QWEN2509_NUNCHAKU,
                     QWEN2511_BASE, QWEN2511_GGUF_METHODS, QWEN2511_LIGHTNING_4)

RESULT_NODE = '14'

FLUX3_EDIT_SYSTEM_PROMPT = (
    "Expand the user's request into one detailed English image-editing instruction. "
    "The first input is the photo to edit. If a second input is present, use it only as directed "
    "and say which details come from each image. Describe the intended result and relevant existing "
    "details, keeping the requested edit, composition, faces, text, textures and photographic character. "
    "Leave any content outside the requested changes intact. Avoid adding details that are absent or "
    "unrequested. Output only the instruction, without Markdown or extra commentary."
)


def qwen_graph(models, filename, prompt, seed, method, *, second_image=None):
    graph = {}

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    nunchaku = method == QWEN2509_NUNCHAKU
    qwen2511 = method in QWEN2511_GGUF_METHODS
    four_steps = method in (QWEN2509_NUNCHAKU, QWEN2509_LIGHTNING_4, QWEN2511_LIGHTNING_4)
    shift = 3.0 if method in (QWEN2509_NUNCHAKU, *QWEN2509_GGUF_METHODS) else 3.1
    if nunchaku:
        # Keep one transformer block resident to leave room for activations on smaller GPUs.
        add(1, NUNCHAKU_LOADER, model_name=models['diffusion'], cpu_offload='enable',
            num_blocks_on_gpu=1, use_pin_memory='disable')
    else:
        add(1, 'UnetLoaderGGUF', unet_name=models['diffusion'])
    add(2, 'CLIPLoader', clip_name=models['text'], type='qwen_image', device='default')
    add(3, 'VAELoader', vae_name=models['vae'])
    add(4, 'LoadImage', image=filename)
    if second_image:
        add(30, 'LoadImage', image=second_image)
    sampling_model = ['1', 0]
    if 'lightning' in models and not qwen2511:
        # These ComfyUI templates apply Lightning before sampling patches.
        add(16, 'LoraLoaderModelOnly', model=sampling_model, lora_name=models['lightning'], strength_model=1.0)
        sampling_model = ['16', 0]
    add(5, 'ModelSamplingAuraFlow', model=sampling_model, shift=shift)
    add(6, 'TextEncodeQwenImageEditPlus', clip=['2', 0], vae=['3', 0], prompt=prompt, image1=['4', 0])
    add(7, 'TextEncodeQwenImageEditPlus', clip=['2', 0], vae=['3', 0], prompt='', image1=['4', 0])
    if second_image:
        for node in ('6', '7'):
            graph[node]['inputs']['image2'] = ['30', 0]
    add(8, 'VAEEncode', pixels=['4', 0], vae=['3', 0])
    add(15, 'CFGNorm', model=['5', 0], strength=1.0)
    model, positive, negative = ['15', 0], ['6', 0], ['7', 0]
    if qwen2511:
        if 'lightning' in models:
            add(16, 'LoraLoaderModelOnly', model=model, lora_name=models['lightning'], strength_model=1.0)
            model = ['16', 0]
        add(17, 'FluxKontextMultiReferenceLatentMethod', conditioning=positive, reference_latents_method='index_timestep_zero')
        add(18, 'FluxKontextMultiReferenceLatentMethod', conditioning=negative, reference_latents_method='index_timestep_zero')
        positive, negative = ['17', 0], ['18', 0]
    base_steps = {QWEN2509_BASE: 20, QWEN2511_BASE: 40, FIRERED_BASE: 40}.get(method)
    steps = base_steps or (4 if four_steps else 8)
    add(9, 'KSampler', model=model, positive=positive, negative=negative, latent_image=['8', 0],
        seed=seed, steps=steps, cfg=4.0 if base_steps else 1.0,
        sampler_name='euler', scheduler='simple', denoise=1.0)
    add(10, 'VAEDecode', samples=['9', 0], vae=['3', 0])
    return graph


def fibo2_graph(models, filename, size, prompt, seed, *, second_image=None):
    width, height = size
    graph = {}

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    add(1, 'UNETLoader', unet_name=models['diffusion'], weight_dtype='default')
    add(2, 'CLIPLoader', clip_name=models['text'], type='fibo2', device='default')
    add(3, 'VAELoader', vae_name=models['vae'])
    add(4, 'LoadImage', image=filename)
    if second_image:
        add(30, 'LoadImage', image=second_image)
    add(6, 'TextEncodeFibo2', clip=['2', 0], vae=['3', 0], prompt=prompt, negative_prompt='',
        width=width, height=height, batch_size=1, **{'images.image_1': ['4', 0]})
    if second_image:
        graph['6']['inputs']['images.image_2'] = ['30', 0]
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


def append_seedvr2(graph, models, size, seed):
    preview = graph[RESULT_NODE]['inputs']
    # SeedVR2 crops to even dimensions. Round up before the common export resize.
    width, height = (max(16, edge + edge % 2) for edge in size)
    tiles = dict(tile_size=512, overlap=128, temporal_size=4096, temporal_overlap=8)

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    add(40, 'ImageScale', image=preview['images'], upscale_method='lanczos',
        width=width, height=height, crop='disabled')
    add(41, 'SeedVR2Preprocess', resized_images=['40', 0])
    add(42, 'VAELoader', vae_name=models['upscale_seedvr2_vae'])
    add(43, 'UNETLoader', unet_name=models['upscale_seedvr2'], weight_dtype='default')
    add(44, 'VAEEncodeTiled', vae=['42', 0], pixels=['41', 0], **tiles)
    add(45, 'SeedVR2Conditioning', model=['43', 0], vae_conditioning=['44', 0])
    add(46, 'KSampler', model=['43', 0], positive=['45', 0], negative=['45', 1],
        latent_image=['44', 0], seed=seed, steps=1, cfg=1.0, sampler_name='euler',
        scheduler='simple', denoise=1.0)
    add(47, 'VAEDecodeTiled', vae=['42', 0], samples=['46', 0], **tiles)
    add(48, 'SeedVR2PostProcessing', images=['47', 0], original_resized_images=['40', 0],
        color_correction_method='none')
    preview['images'] = ['48', 0]


def append_vosr2(graph, bundle, scale, seed):
    preview = graph[RESULT_NODE]['inputs']
    graph['40'] = {'class_type': 'VOSR2ModelLoader', 'inputs': {'model': bundle, 'dtype': 'default'}}
    graph['41'] = {'class_type': 'VOSR2Upscale', 'inputs': {
        'model': ['40', 0], 'image': preview['images'], 'upscale': scale, 'seed': seed % (2**63),
        'color_alignment': 'wavelet', 'tile_size': 512, 'tile_overlap': 64,
        'vae_tile_size': 1024, 'vae_tile_overlap': 128,
    }}
    preview['images'] = ['41', 0]


def standalone_upscale_graph(filename):
    return {
        '4': {'class_type': 'LoadImage', 'inputs': {'image': filename}},
        RESULT_NODE: {'class_type': 'PreviewImage', 'inputs': {'images': ['4', 0]}},
    }


def flux2_graph(models, filename, size, prompt, seed, *, second_image=None):
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
    positive, negative = ['8', 0], ['15', 0]
    if second_image:
        add(30, 'LoadImage', image=second_image)
        add(31, 'VAEEncode', pixels=['30', 0], vae=['3', 0])
        add(32, 'ReferenceLatent', conditioning=positive, latent=['31', 0])
        add(33, 'ReferenceLatent', conditioning=negative, latent=['31', 0])
        positive, negative = ['32', 0], ['33', 0]
    add(20, 'CFGGuider', model=['1', 0], positive=positive, negative=negative, cfg=1.0)
    add(9, 'SamplerCustomAdvanced', noise=['19', 0], guider=['20', 0], sampler=['18', 0],
        sigmas=['17', 0], latent_image=['16', 0])
    add(10, 'VAEDecode', samples=['9', 0], vae=['3', 0])
    return graph


def flux3_graph(models, filename, size, prompt, seed, *, second_image=None):
    width, height = size
    graph = {}

    def add(number, kind, **inputs):
        graph[str(number)] = {'class_type': kind, 'inputs': inputs}

    add(1, 'UNETLoader', unet_name=models['diffusion'], weight_dtype='default')
    add(2, 'CLIPLoader', clip_name=models['text'], type='flux3', device='default')
    add(3, 'VAELoader', vae_name=models['vae'])
    add(4, 'LoadImage', image=filename)
    images = {'images.image1': ['4', 0]}
    references = {'images.image0': ['4', 0]}
    if second_image:
        add(30, 'LoadImage', image=second_image)
        images['images.image2'] = ['30', 0]
        references['images.image1'] = ['30', 0]
    add(5, 'CLIPLoader', clip_name=models['prompt_upsampler'], type='flux3', device='default')
    add(21, 'PrimitiveStringMultiline', value=FLUX3_EDIT_SYSTEM_PROMPT)
    add(6, 'TextGenerateV2', clip=['5', 0], prompt=prompt, max_length=3584, sampling_mode='on',
        thinking=False, use_default_template=True, mtp='off', system_prompt=['21', 0],
        **{'sampling_mode.temperature': 1.0, 'sampling_mode.top_k': 1, 'sampling_mode.top_p': 0.95,
           'sampling_mode.min_p': 0.0, 'sampling_mode.repetition_penalty': 1.05,
           'sampling_mode.presence_penalty': 0.0, 'sampling_mode.seed': seed, **images})
    add(7, 'CLIPTextEncode', clip=['2', 0], text=['6', 0])
    add(15, 'ConditioningZeroOut', conditioning=['7', 0])
    add(8, 'ReferenceMultiLatent', positive=['7', 0], negative=['15', 0], vae=['3', 0],
        resolution='keep resolution', **references)
    add(16, 'EmptyFlux2LatentImage', width=width, height=height, batch_size=1)
    add(9, 'KSampler', model=['1', 0], positive=['8', 0], negative=['8', 1], latent_image=['16', 0],
        seed=seed, steps=16, cfg=1.0, sampler_name='euler', scheduler='simple', denoise=1.0)
    add(10, 'VAEDecode', samples=['9', 0], vae=['3', 0])
    return graph
