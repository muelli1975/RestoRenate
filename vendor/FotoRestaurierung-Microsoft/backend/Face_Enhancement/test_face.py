# Copyright (c) Microsoft Corporation

import torchvision.transforms as T

from .data import create_dataloader
from .models.pix2pix_model import Pix2PixModel
from .options.test_options import TestOptions

tensor2image = T.ToPILImage()


def test_face(face_images: list, args: dict) -> list:
    gpu_ids = ','.join(str(index) for index in args['gpu_ids']) or '-1'
    opt = TestOptions().parse(['--gpu_ids', gpu_ids])
    for K, V in args.items():
        setattr(opt, K, V)

    opt.semantic_nc = opt.label_nc + int(opt.contain_dontcare_label) + int(not opt.no_instance)
    dataloader = create_dataloader(opt, face_images)
    images = []

    model = Pix2PixModel(opt)
    model.eval()

    for i, data_i in enumerate(dataloader):
        if i * opt.batchSize >= opt.how_many:
            break

        generated = model(data_i, mode="inference")

        for b in range(generated.shape[0]):
            images.append(tensor2image((generated[b] + 1) / 2))

    return images
