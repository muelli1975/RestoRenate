"""ComfyUI adapters for Microsoft's Bringing Old Photos Back to Life."""
from pathlib import Path

import numpy as np
import torch
from PIL import Image

import comfy.model_management
from comfy.utils import ProgressBar
import folder_paths


def model_directory():
    return Path(folder_paths.models_dir) / 'microsoft' / 'checkpoints'


def device_index():
    device = comfy.model_management.get_torch_device()
    return (device.index or 0) if device.type == 'cuda' else -1


def to_image(tensor):
    return Image.fromarray(tensor[0].detach().cpu().mul(255).clamp(0, 255).byte().numpy(), 'RGB')


def to_tensor(image):
    return torch.from_numpy(np.array(image.convert('RGB'), dtype=np.float32) / 255.0).unsqueeze(0)


class RestoreOldPhoto:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',), 'scratches': ('BOOLEAN', {'default': True})}}

    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'restore'
    CATEGORY = 'image/restoration'

    @torch.inference_mode()
    def restore(self, image, scratches):
        from .backend.Global.test import global_test

        photo = to_image(image)
        models = model_directory()
        device = device_index()
        progress = ProgressBar(2 if scratches else 1)
        mask = None
        args = ['--test_mode', 'Full', '--gpu_ids', str(device)]
        if scratches:
            from .backend.Global.detection import global_detection

            mask, photo = global_detection(photo, device, 'full_size', models / 'detection/FT_Epoch_latest.pt')
            mask = mask.convert('RGB')
            args.append('--Scratch_and_Quality_restore')
            if max(photo.size) > 768:
                args.append('--HR')
            progress.update(1)
        else:
            args.append('--Quality_restore')
        result = global_test(str(models / 'restoration'), args, photo.convert('RGB'), mask)
        progress.update(1)
        return (to_tensor(result),)


class RestoreFaces:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',)}}

    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'restore'
    CATEGORY = 'image/restoration'

    @torch.inference_mode()
    def restore(self, image):
        from .backend.Face_Detection.align_warp_back_multiple_dlib import align_warp
        from .backend.Face_Detection.detect_all_dlib import detect
        from .backend.Face_Enhancement.test_face import test_face

        photo = to_image(image)
        models = model_directory()
        landmark = str(models / 'shape_predictor_68_face_landmarks.dat')
        progress = ProgressBar(2)
        faces = detect(photo, landmark)
        progress.update(1)
        if not faces:
            progress.update(1)
            return (image,)
        result = test_face(faces, {
            'checkpoints_dir': str(models / 'faces'), 'name': 'Setting_9_epoch_100',
            'gpu_ids': [device_index()] if device_index() >= 0 else [],
            'load_size': 256, 'label_nc': 18, 'no_instance': True, 'preprocess_mode': 'resize',
            'batchSize': 4, 'no_parsing_map': True, 'serial_batches': True,
        })
        photo = align_warp(photo, result, landmark)
        progress.update(1)
        return (to_tensor(photo),)


NODE_CLASS_MAPPINGS = {'FotoRestaurierungMicrosoft': RestoreOldPhoto, 'FotoRestaurierungGesichter': RestoreFaces}
