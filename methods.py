"""Restoration methods and their model files."""
from pathlib import Path

FIBO2_TURBO = 'fibo2-edit-turbo'
DEFAULT_METHOD = FIBO2_TURBO
FLUX2 = 'flux2-klein'
FLUX3 = 'flux3-klein'
FLUX_METHODS = (FLUX2, FLUX3)
QWEN2509_NUNCHAKU = 'qwen2509-nunchaku'
QWEN2509_LIGHTNING_4 = 'qwen2509-lightning-4'
QWEN2509_BASE = 'qwen2509-base'
QWEN2511_LIGHTNING_4 = 'qwen2511-lightning-4'
QWEN2511_BASE = 'qwen2511-base'
FIRERED_LIGHTNING = 'firered11-lightning-8'
FIRERED_BASE = 'firered11-base'
QWEN2509_GGUF_METHODS = (QWEN2509_LIGHTNING_4, QWEN2509_BASE)
QWEN2511_GGUF_METHODS = (QWEN2511_LIGHTNING_4, QWEN2511_BASE)
QWEN_METHODS = (QWEN2509_NUNCHAKU, *QWEN2509_GGUF_METHODS, *QWEN2511_GGUF_METHODS)
FIRERED_METHODS = (FIRERED_LIGHTNING, FIRERED_BASE)
TWO_IMAGE_METHODS = (FIBO2_TURBO, *FLUX_METHODS, *QWEN_METHODS, *FIRERED_METHODS)
GGUF_METHODS = (*QWEN2509_GGUF_METHODS, *QWEN2511_GGUF_METHODS, *FIRERED_METHODS)
NUNCHAKU_LOADER = 'NunchakuQwenImageDiTLoader'
MICROSOFT = 'microsoft'
DDCOLOR = 'ddcolor'
DDCOLOR_PAPER = 'ddcolor-paper'
DDCOLOR_ARTISTIC = 'ddcolor-artistic'
DDCOLOR_TINY = 'ddcolor-tiny'
DEOLDIFY_STABLE = 'deoldify-stable'
DEOLDIFY_ARTISTIC = 'deoldify-artistic'
DDCOLOR_METHODS = (DDCOLOR, DDCOLOR_PAPER, DDCOLOR_ARTISTIC, DDCOLOR_TINY)
DEOLDIFY_METHODS = (DEOLDIFY_STABLE, DEOLDIFY_ARTISTIC)
COLORIZATION_METHODS = (*DDCOLOR_METHODS, *DEOLDIFY_METHODS)
UPSCALING = 'upscaling'
NATIVE_METHODS = (*COLORIZATION_METHODS, UPSCALING)
NO_PROMPT = (MICROSOFT, *NATIVE_METHODS)
CPU_METHODS = (FIBO2_TURBO, FLUX2, QWEN2509_LIGHTNING_4, QWEN2511_LIGHTNING_4, *NO_PROMPT)
METHOD_MENU_SECTIONS = (
    ('Bearbeiten', (
        (None, (FIBO2_TURBO,)),
        ('FireRed', FIRERED_METHODS),
        ('FLUX', FLUX_METHODS),
        (None, (MICROSOFT,)),
        ('Qwen', QWEN_METHODS),
    )),
    ('Kolorieren', (
        ('DDColor', DDCOLOR_METHODS),
        ('DeOldify', DEOLDIFY_METHODS),
    )),
)
ULTRASHARP_ORIGINAL = 'UltraSharp 4×'
ULTRASHARP = 'UltraSharp V2'
ULTRASHARP_LITE = 'UltraSharp V2 Lite'
REALESRGAN = 'Real-ESRGAN'
REALESRGAN_ANIME = 'Real-ESRGAN Anime 4×'
ANIMESHARP = 'AnimeSharp 4×'
REMACRI = 'Remacri 4×'
REALWEBPHOTO = 'RealWebPhoto v4'
SIAX = 'NMKD Siax 4×'
CLEARREALITY = 'ClearRealityV1 SPAN 4×'
PUREPHOTO = 'PurePhoto SPAN 4×'
NOMOS2_HQ = 'Nomos2 HQ MoSR 4×'
NOMOS2_DAT2 = 'Nomos2 HQ DAT2 4×'
NOMOS8K_DAT = 'Nomos8kDAT 4×'
FACEUP_DAT = '4× FaceUpDAT'
SWINIR_S = 'SwinIR-S 4×'
LANCZOS = 'Lanczos'
SEEDVR2 = 'SeedVR2 3B INT8'
VOSR2 = 'VOSR 2.0'
VOSR2_BUNDLE = 'VOSR2'
UPSCALE_MENU_SECTIONS = (
    ('Saubere Fotos und Porträts', (CLEARREALITY, PUREPHOTO, NOMOS2_HQ, NOMOS2_DAT2, FACEUP_DAT)),
    ('Detailrekonstruktion', (SEEDVR2, VOSR2)),
    ('Kleine und komprimierte Fotos', (NOMOS8K_DAT, REALWEBPHOTO)),
    ('Allrounder', (REALESRGAN, SIAX, REMACRI, ULTRASHARP_ORIGINAL, ULTRASHARP, ULTRASHARP_LITE, SWINIR_S)),
    ('Zeichnungen und Anime', (REALESRGAN_ANIME, ANIMESHARP)),
)
UPSCALERS = (*(item for _, group in UPSCALE_MENU_SECTIONS for item in group), LANCZOS)
UPSCALE_LICENSES = {
    CLEARREALITY: 'Apache 2.0',
    PUREPHOTO: 'CC BY-SA 4.0',
    ULTRASHARP_ORIGINAL: 'CC BY-NC-SA 4.0',
    ULTRASHARP: 'CC BY-NC-SA 4.0',
    ULTRASHARP_LITE: 'CC BY-NC-SA 4.0',
    REALESRGAN: 'BSD 3-Clause',
    REALESRGAN_ANIME: 'BSD 3-Clause',
    ANIMESHARP: 'CC BY-NC-SA 4.0',
    REMACRI: 'CC BY-NC-SA 4.0',
    REALWEBPHOTO: 'CC BY 4.0',
    SIAX: 'WTFPL',
    NOMOS2_HQ: 'CC BY 4.0',
    NOMOS2_DAT2: 'CC BY 4.0',
    NOMOS8K_DAT: 'CC BY 4.0',
    SEEDVR2: 'Apache 2.0',
    VOSR2: 'Apache 2.0',
    FACEUP_DAT: 'CC BY 4.0',
    SWINIR_S: 'Apache 2.0',
}
METHODS = {
    FIBO2_TURBO: 'Fibo 2.0 Edit Turbo',
    FLUX2: 'FLUX.2 [klein] 4B',
    FLUX3: 'FLUX 3 Image Klein · INT8',
    QWEN2509_NUNCHAKU: 'Qwen Image Edit 2509 · Nunchaku INT4',
    QWEN2509_LIGHTNING_4: 'Qwen Image Edit 2509 · Lightning (4 Schritte)',
    QWEN2509_BASE: 'Qwen Image Edit 2509',
    QWEN2511_LIGHTNING_4: 'Qwen Image Edit 2511 · Lightning (4 Schritte)',
    QWEN2511_BASE: 'Qwen Image Edit 2511',
    FIRERED_LIGHTNING: 'FireRed Image Edit 1.1 · Lightning (8 Schritte)',
    FIRERED_BASE: 'FireRed Image Edit 1.1',
    MICROSOFT: 'Microsoft · Bringing Old Photos Back to Life',
    DDCOLOR: 'Kolorieren · DDColor ModelScope',
    DDCOLOR_PAPER: 'Kolorieren · DDColor Paper',
    DDCOLOR_ARTISTIC: 'Kolorieren · DDColor Artistic',
    DDCOLOR_TINY: 'Kolorieren · DDColor Tiny',
    DEOLDIFY_STABLE: 'Kolorieren · DeOldify Stable',
    DEOLDIFY_ARTISTIC: 'Kolorieren · DeOldify Artistic',
    UPSCALING: 'Nur hochskalieren',
}
COLORIZATION_NAMES = {method: METHODS[method].removeprefix('Kolorieren · ') for method in COLORIZATION_METHODS}
METHOD_FILENAME_LABELS = {
    FIBO2_TURBO: 'Fibo-2.0',
    FLUX2: 'FLUX2-4B',
    FLUX3: 'FLUX3-Klein',
    QWEN2509_NUNCHAKU: 'Qwen-2509-Nunchaku',
    QWEN2509_LIGHTNING_4: 'Qwen-2509-4step',
    QWEN2509_BASE: 'Qwen-2509',
    QWEN2511_LIGHTNING_4: 'Qwen-2511-4step',
    QWEN2511_BASE: 'Qwen-2511',
    FIRERED_LIGHTNING: 'FireRed-1.1-8step',
    FIRERED_BASE: 'FireRed-1.1',
    MICROSOFT: 'Microsoft',
    DDCOLOR: 'DDColor-ModelScope',
    DDCOLOR_PAPER: 'DDColor-Paper',
    DDCOLOR_ARTISTIC: 'DDColor-Artistic',
    DDCOLOR_TINY: 'DDColor-Tiny',
    DEOLDIFY_STABLE: 'DeOldify-Stable',
    DEOLDIFY_ARTISTIC: 'DeOldify-Artistic',
}
UPSCALE_FILENAME_LABELS = {
    CLEARREALITY: 'ClearRealityV1-SPAN-4x',
    PUREPHOTO: 'PurePhoto-SPAN-4x',
    ULTRASHARP_ORIGINAL: 'UltraSharp-4x',
    ULTRASHARP: 'UltraSharp-V2',
    ULTRASHARP_LITE: 'UltraSharp-V2-Lite',
    REALESRGAN_ANIME: 'RealESRGAN-Anime-4x',
    ANIMESHARP: 'AnimeSharp-4x',
    REMACRI: 'Remacri',
    REALWEBPHOTO: 'RealWebPhoto-v4',
    SIAX: 'Siax',
    NOMOS2_HQ: 'Nomos2-MoSR',
    NOMOS2_DAT2: 'Nomos2-DAT2-4x',
    NOMOS8K_DAT: 'Nomos8kDAT-4x',
    SEEDVR2: 'SeedVR2-3B-INT8',
    VOSR2: 'VOSR-2.0',
    FACEUP_DAT: 'FaceUpDAT-4x',
    SWINIR_S: 'SwinIR-S-4x',
}
LICENSES = {
    FIBO2_TURBO: 'CC BY-NC 4.0 · nicht kommerziell',
    FLUX2: 'Apache 2.0',
    FLUX3: 'FLUX Kommunity License v1.0',
    **dict.fromkeys((*QWEN_METHODS, *FIRERED_METHODS), 'Apache 2.0'),
    MICROSOFT: 'MIT-Code',
    UPSCALING: 'siehe gewähltes Modell',
    DDCOLOR: 'Apache 2.0',
    DDCOLOR_PAPER: 'Apache 2.0',
    DDCOLOR_ARTISTIC: 'Apache 2.0',
    DDCOLOR_TINY: 'Apache 2.0',
    DEOLDIFY_STABLE: 'MIT',
    DEOLDIFY_ARTISTIC: 'MIT',
}
UPSCALE = ('UpscaleModelLoader', 'model_name', '4x-UltraSharpV2.safetensors')
UPSCALE_LITE = ('UpscaleModelLoader', 'model_name', '4x-UltraSharpV2_Lite.safetensors')
ESRGAN2 = ('UpscaleModelLoader', 'model_name', 'RealESRGAN_x2plus.pth')
ESRGAN4 = ('UpscaleModelLoader', 'model_name', 'RealESRGAN_x4plus.safetensors')
UPSCALE_FILES = {
    CLEARREALITY: {'upscale': ('UpscaleModelLoader', 'model_name', '4x-ClearRealityV1.safetensors')},
    PUREPHOTO: {'upscale': ('UpscaleModelLoader', 'model_name', '4xPurePhoto-Span.pth')},
    ULTRASHARP_ORIGINAL: {'upscale': ('UpscaleModelLoader', 'model_name', '4x-UltraSharp.safetensors')},
    ULTRASHARP: {'upscale': UPSCALE},
    ULTRASHARP_LITE: {'upscale_lite': UPSCALE_LITE},
    REALESRGAN: {'esrgan2': ESRGAN2, 'esrgan4': ESRGAN4},
    REALESRGAN_ANIME: {'upscale': ('UpscaleModelLoader', 'model_name', 'RealESRGAN_x4plus_anime_6B.pth')},
    ANIMESHARP: {'upscale': ('UpscaleModelLoader', 'model_name', '4x-AnimeSharp.safetensors')},
    REMACRI: {'upscale': ('UpscaleModelLoader', 'model_name', '4x_foolhardy_Remacri.pth')},
    REALWEBPHOTO: {'upscale': ('UpscaleModelLoader', 'model_name', '4xRealWebPhoto_v4_dat2.safetensors')},
    SIAX: {'upscale': ('UpscaleModelLoader', 'model_name', '4x_NMKD-Siax_200k.pth')},
    NOMOS2_HQ: {'upscale': ('UpscaleModelLoader', 'model_name', '4xNomos2_hq_mosr.safetensors')},
    NOMOS2_DAT2: {'upscale': ('UpscaleModelLoader', 'model_name', '4xNomos2_hq_dat2.safetensors')},
    NOMOS8K_DAT: {'upscale': ('UpscaleModelLoader', 'model_name', '4xNomos8kDAT.safetensors')},
    FACEUP_DAT: {'upscale': ('UpscaleModelLoader', 'model_name', '4xFaceUpDAT.safetensors')},
    SWINIR_S: {'upscale': ('UpscaleModelLoader', 'model_name', '002_lightweightSR_DIV2K_s64w8_SwinIR-S_x4.pth')},
    SEEDVR2: {
        'upscale_seedvr2': ('UNETLoader', 'unet_name', 'seedvr2_3b_int8_convrot.safetensors'),
        'upscale_seedvr2_vae': ('VAELoader', 'vae_name', 'seedvr2_ema_vae_fp16.safetensors'),
    },
    VOSR2: {'upscale_vosr2': ('VOSR2ModelLoader', 'model', VOSR2_BUNDLE)},
    LANCZOS: {},
}
UPSCALE_SCALES = {'upscale': 4, 'upscale_lite': 4, 'esrgan2': 2, 'esrgan4': 4}
QWEN_SHARED_FILES = {
    'text': ('CLIPLoader', 'clip_name', 'qwen_2.5_vl_7b_fp8_scaled.safetensors'),
    'vae': ('VAELoader', 'vae_name', 'qwen_image_vae.safetensors'),
}
QWEN2509_GGUF_FILES = {
    'diffusion': ('UnetLoaderGGUF', 'unet_name', 'Qwen-Image-Edit-2509-Q4_K_M.gguf'),
    **QWEN_SHARED_FILES,
}
QWEN2511_GGUF_FILES = {
    'diffusion': ('UnetLoaderGGUF', 'unet_name', 'qwen-image-edit-2511-Q4_K_M.gguf'),
    **QWEN_SHARED_FILES,
}
FIRERED_GGUF_FILES = {
    'diffusion': ('UnetLoaderGGUF', 'unet_name', 'FireRed-Image-Edit-1.1-transformer-q4_k_m.gguf'),
    **QWEN_SHARED_FILES,
}
FLUX_VAE = ('VAELoader', 'vae_name', 'flux2-vae.safetensors')
QWEN3VL_4B = ('CLIPLoader', 'clip_name', 'qwen3vl_4b_int8_convrot.safetensors')
MODEL_FILES = {
    FLUX2: {
        'diffusion': ('UNETLoader', 'unet_name', 'flux-2-klein-4b.safetensors'),
        'text': ('CLIPLoader', 'clip_name', 'qwen_3_4b.safetensors'),
        'vae': FLUX_VAE,
    },
    FLUX3: {
        'diffusion': ('UNETLoader', 'unet_name', 'flux3-image-klein-int8-convrot.safetensors'),
        'text': QWEN3VL_4B,
        'vae': FLUX_VAE,
        'prompt_upsampler': ('CLIPLoader', 'clip_name', 'qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors'),
    },
    FIBO2_TURBO: {
        'diffusion': ('UNETLoader', 'unet_name', 'fibo2_edit_turbo_int8_convrot.safetensors'),
        'text': QWEN3VL_4B,
        'vae': FLUX_VAE,
    },
    QWEN2509_NUNCHAKU: {
        'diffusion': (NUNCHAKU_LOADER, 'model_name',
                      'svdq-int4_r32-qwen-image-edit-2509-lightning-4steps-251115.safetensors'),
        **QWEN_SHARED_FILES,
    },
    QWEN2509_LIGHTNING_4: {
        **QWEN2509_GGUF_FILES,
        'lightning': ('LoraLoaderModelOnly', 'lora_name',
                      'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors'),
    },
    QWEN2509_BASE: QWEN2509_GGUF_FILES,
    QWEN2511_LIGHTNING_4: {
        **QWEN2511_GGUF_FILES,
        'lightning': ('LoraLoaderModelOnly', 'lora_name',
                      'Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors'),
    },
    QWEN2511_BASE: QWEN2511_GGUF_FILES,
    FIRERED_LIGHTNING: {
        **FIRERED_GGUF_FILES,
        'lightning': ('LoraLoaderModelOnly', 'lora_name',
                      'FireRed-Image-Edit-1.1-Lightning-8steps-v1.2.safetensors'),
    },
    FIRERED_BASE: FIRERED_GGUF_FILES,
    MICROSOFT: {},
    **{method: {} for method in NATIVE_METHODS},
}


def available_methods(supports_nunchaku, *, cpu=False):
    if cpu:
        return CPU_METHODS
    return tuple(method for method in METHODS if supports_nunchaku or method != QWEN2509_NUNCHAKU)


def uses_comfy(method, upscaler):
    return method not in NATIVE_METHODS or upscaler != LANCZOS


def resolve_upscaler(method, upscaler=None):
    if upscaler in UPSCALERS:
        return upscaler
    return LANCZOS if method in COLORIZATION_METHODS else NOMOS2_HQ


def model_files(method, upscaler=None):
    return {**MODEL_FILES[method], **UPSCALE_FILES[resolve_upscaler(method, upscaler)]}


def model_specs(manifest, optional, method, faces=False, upscaler=None):
    files = {Path(item['path']).name: item for item in manifest['models']}
    for group in optional.values():
        files.update((Path(item['path']).name, item) for item in group)
    names = [entry[2] for entry in model_files(method, upscaler).values() if entry[2] != VOSR2_BUNDLE]
    if method == MICROSOFT or method in COLORIZATION_METHODS:
        names.extend(Path(item['path']).name for item in optional[method] if faces or not item.get('face_only'))
    specs = [files[name] for name in dict.fromkeys(names)]
    if upscaler == VOSR2:
        specs.extend(optional['vosr2'])
    return specs
