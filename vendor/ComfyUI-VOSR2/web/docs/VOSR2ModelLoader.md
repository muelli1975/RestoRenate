# VOSR 2.0 Model Loader

Load the VOSR 2.0 image upscaler together with its matched Qwen-Image 2D VAE and DINOv2-L encoder. RestoRenate installs and verifies the bundle under `models/vosr2/VOSR2`. The loader uses those local files.

The **dtype** setting applies to the diffusion model and vision encoder. The VAE runs in FP32.
