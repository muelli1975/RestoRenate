# RestoRenate 1.0

[Windows download](https://github.com/muelli1975/RestoRenate/releases/tag/v1.0) · [Linux preview](https://github.com/muelli1975/RestoRenate/releases/tag/v1.0-linux-preview) · [Deutsch](README_DE.md) · [Detailed guide](README_DE_EN.txt)

RestoRenate is a local desktop tool for restoring, colorizing and upscaling photos. With text prompts and supported models, it can also edit an image or use a second photo as a reference. The interface is available in English and German.

The app asks before downloading missing models and the processing runtime. After setup, image processing runs locally and offline.

## Requirements and installation

| Platform | Package and requirements |
| --- | --- |
| Windows x64 | Extract the [portable ZIP](https://github.com/muelli1975/RestoRenate/releases/download/v1.0/RestoRenate_1.0_Windows_x64.zip) to a short, writable path such as `D:\RestoRenate` and open `RestoRenate.exe`. Python and ExifTool are included. |
| Ubuntu 24.04 x86-64 | The Linux preview is built and tested in [GitHub Actions](https://github.com/muelli1975/RestoRenate/actions/workflows/linux.yml). Install `python3.12-venv`, `python3-tk`, `git` and `libimage-exiftool-perl`, extract the `.tar.gz` into a writable folder and run `./Start.sh`. The script creates a Python environment inside that folder. |

Windows offers CPU and NVIDIA modes, plus experimental AMD ROCm. The Linux preview defaults to CPU and offers an experimental NVIDIA mode with a CUDA 13-compatible driver. Nunchaku INT4 is available on supported Windows NVIDIA systems. macOS packages are planned.

When updating Windows, close RestoRenate and extract the package into a clean folder. To keep an existing setup, copy `models`, `backend`, `downloads`, `settings` and the existing runtime subfolders and download receipts as needed. Extract the new package in full to keep its `_internal`, `assets` and `tools` together.

## Quick start

1. Open a photo or folder. Crop or rotate the input if needed.
2. Choose an output folder, file format and size, then select a method. Edit the prompt for models that accept text.
3. Select **Start**. Use **Download models …** to prepare multiple methods in one pass. Optional Lightning LoRAs are listed beneath their base models.
4. Compare the saved result with the before-and-after slider. Use **Ctrl+1** for 100%, **Esc** to fit the view, and **Page Up / Page Down** to browse results.

## Models and output

- **Restoration and editing:** Microsoft Bringing Old Photos Back to Life, Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B, Qwen Image Edit 2509/2511 and FireRed Image Edit 1.1. Some edit models support a separately rotatable second input.
- **Colorization:** DDColor ModelScope, Paper, Artistic and Tiny, plus DeOldify Stable and Artistic. Colorization runs on the CPU. DDColor Paper is an optional model download.
- **Upscaling:** Lanczos and several AI upscalers, including Nomos2 HQ MoSR, Real-ESRGAN and FaceUpDAT for portraits.
- **Export:** PNG, JPEG quality 95 with 4:4:4 chroma and TIFF with LZW compression. JPEG and TIFF copy compatible source metadata. PNG stores a ComfyUI workflow when applicable.

## Source and builds

The source includes the desktop app, download manifests and ComfyUI adapters. [GitHub Actions](https://github.com/muelli1975/RestoRenate/actions) records builds and tests. The portable Windows release includes its launcher, Python environment and export tools.

## License

RestoRenate's own code uses the [MIT License](LICENSE). See [THIRD_PARTY.txt](THIRD_PARTY.txt) for component and model licenses.
