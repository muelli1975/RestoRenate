# RestoRenate 1.3

Portable edition

## Start and update

Extract the entire ZIP to a short, writable path such as D:\RestoRenate and
open RestoRenate.exe. To update, close RestoRenate and copy the contents of the
RestoRenate folder in the ZIP into the existing program folder. Replace the
program files. Models can be reused. The settings and custom presets are in
settings.json at the top level of the program folder.

Linux: Extract the archive and run ./Start.sh in a graphical desktop session.
macOS 15+: Extract the ZIP and open RestoRenate.app from its folder.
Gatekeeper may display an alert when opening the ad hoc signed app for the first time.
See [Apple Support](https://support.apple.com/en-us/102445) for details.
Python, Tk and ExifTool are included. ExifTool uses the system Perl.

Open an image or folder and choose a method. Input formats
include JPEG, PNG, TIFF, WebP, BMP and AVIF. “Crop …” opens a frame with a
rule-of-thirds grid. Drag inside the frame to move it or drag a handle to
resize it. Choose “Free,” a fixed ratio or “Custom …” for a ratio such as
7:5. Each image in a folder can be selected and cropped individually. “Apply”
shows the selected image in the main view. Use “Horizon” and “Perspective”
to align the image to a 9 × 9 grid. You can enter either value directly. Shift + mouse wheel over the track or handle adjusts the slider by one step.
Double-click an image editing slider to reset it to its default (Horizon 0°, Perspective 0). With focus in the crop preview, the arrow keys move the crop by one pixel. Hold Ctrl to move it by five pixels.
Shift + ← / → rotates the image 0.1° counterclockwise / clockwise. Shift + ↑ / ↓ widens the
top / bottom edge. Enter applies the cut, Esc discards it and F1 opens Controls.
“Fit within image” trims the selection to valid image pixels.
The before side of the result comparison shows the straightened crop. “Rotate” turns the input shown there
90° left or right or 180°. An existing crop rotates with it. Rotation takes
place before cropping and processing. The original file is preserved. The
app initially uses the system display language. The interface language can
be switched in place while keeping the comparison view, zoom and slider position.

“Second image” below the input is available for Fibo 2.0 Edit Turbo, FLUX.2
[klein] 4B, FLUX 3 Image Klein, Qwen Image Edit 2509 and 2511 including Nunchaku,
and FireRed Image Edit 1.1. “Image …” loads the second image into the preview. It can be cropped
and rotated independently, replaced or removed. For a folder, it applies to all
inputs. The prompt can describe which content to transfer from image 2 into
image 1. In Fibo prompts, use the placeholders `<image_1>` and `<image_2>`.

## Prompts and presets

“Prompt snippets” beside “Save prompt …” opens the existing categories
above the button. Choosing a snippet appends an English sentence. Right-click
the field for text editing commands. “Save prompt …” adds the current text
to the shared prompt list. “General-purpose restoration” is the default for
new settings. The current prompt carries over when switching
between methods with text input. “Restore and colorize 1” and “Restore and colorize
2” come from the Weird Wonderful AI Art example workflows. A model name in a
prompt label indicates the recommended method for that prompt.

Use “Presets” to save the method, prompt, variants and applicable output
and model settings. Loading a preset keeps the selected input and output
folder. The GPU startup settings and the GPU “Default” preset use Fibo 2.0 Edit Turbo,
“General-purpose restoration” and ClearRealityV1 SPAN 4×. “Detail reconstruction”
is available in the same menu in GPU mode and uses VOSR 2.0 with the
same processing settings. Saved settings take precedence at startup.

Start processes and saves the result. For prompt-based methods, type a number
from 1 to 100 in “Variants per image” or use the arrows. The count applies to
each image in a folder. The seed field starts blank and the app uses random
seeds. A fixed seed for the current session can be entered, copied from the last result with “Use last seed,”
or read from a PNG's ComfyUI metadata with “Import from PNG …”. For multiple
variants, the fixed seed is incremented by one per variant for each image.
The prompt for the next job can be edited while
the current job runs.
“Cancel” ends the current job. “Stop after image” or “Stop after variant”
lets the current result finish. A completion sound plays after a successful job.

## Methods and hardware

- Fibo 2.0 Edit Turbo uses four steps and a working canvas around one
  megapixel. The model and text encoder add a 13.3 GB download. It shares the
  image decoder with FLUX.2. The Fibo weights are licensed under CC BY-NC 4.0.
- FLUX.2 [klein] 4B uses four steps and resizes the image proportionally to
  about one megapixel. The weights are licensed under Apache 2.0.
- Qwen Image Edit 2509 · Nunchaku INT4 resizes proportionally to about one
  megapixel. It uses R32 with four integrated Lightning steps and CPU
  offloading. It requires a NVIDIA RTX 30 or 40 series GPU with a CUDA 13
  compatible driver. The method is shown on compatible NVIDIA hardware.
- Qwen Image Edit 2509 and 2511 offer base and four-step Lightning
  variants. CPU mode offers the Lightning variants. The base variants use
  20 steps for 2509 and 40 steps for 2511, both at CFG 4.
  These variants share one Q4_K_M file per model. Each Lightning LoRA
  adds about 850 MB.
- FireRed Image Edit 1.1 offers a base variant with 40 steps at CFG 4
  and eight-step Lightning. Both require a GPU and share the same Q4_K_M file.
  The Lightning LoRA adds about 850 MB. FireRed and the Qwen methods share
  the text encoder and VAE. The GGUF methods use a working canvas around
  one megapixel. RestoRenate removes any added padding after processing.
  The weights are licensed under Apache 2.0.
- Microsoft · Bringing Old Photos Back to Life restores images at up to
  2048 px on the long edge and produces one result per image. Scratch repair
  and face enhancement are separate options. Face enhancement downloads
  additional files and uses iBUG 300-W facial landmarks (non-commercial).
- DDColor ModelScope, Paper, Artistic and Tiny, along with DeOldify Stable and Artistic,
  colorize on the CPU. They combine estimated colors with the original luminance.
  ONNX Runtime selects the number of CPU threads.
  “No resizing” is the default.

Use “Compute” to choose NVIDIA, CPU or AMD (ROCm). The change takes effect
after restarting. The app remembers the method and scaling settings separately
for CPU and GPU. The CPU default is Microsoft · Bringing Old Photos Back to Life
with “No resizing”. If NVIDIA fails to start, the app offers to continue the
same job on the CPU for this session when the method supports it.
Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B and the two Qwen Lightning
variants are the four-step edit models available in CPU mode. They can take
a long time and use substantial RAM. AI upscaling also takes processing time. Suitability for 8 GB of
VRAM depends on the model, the image and available GPU and system memory.

AMD (ROCm) is experimental. RestoRenate uses the official ComfyUI v0.45.0
AMD portable package with ROCm 7.2 and checks a GPU operation during setup.
It requires Windows 11, a supported Radeon GPU and a compatible driver.
The GPU check verifies the runtime. Model compatibility also depends on
the card and the operations used. See AMD’s compatibility list at
https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html

## Output and preview

“Use a subfolder inside the input folder” is enabled by default. The
destination is output next to the selected image or inside the selected
input folder. Selecting a new input updates the destination.
“Browse …” switches to a custom folder. Results go directly there.
The custom path and output mode are saved separately.

“Output size” shows the calculated dimensions for the current image.
The 1080 px and 2160 px options set image height. “Long edge” and “Short
edge” use the entered side length. RestoRenate preserves the aspect ratio.
“No resizing” exports at the working size. “Upscale only” starts with the
input image. AI upscaling applies when enlarging the image. Real-ESRGAN
selects its 2× or 4× model. Lanczos resizes to the exact output dimensions.
The GPU restoration default is Fibo 2.0 Edit Turbo with a height of 2160 px
and ClearRealityV1 SPAN 4×. “Upscale only” defaults to 2160 px and Nomos2 HQ MoSR 4×.
4× FaceUpDAT is designed for portraits with clean source images.
The upscaler menu groups models by use. Nomos2 HQ MoSR 4× is designed for clean photos. The small and compressed photos group includes
Nomos8kDAT 4×, RealWebPhoto v4 and NomosUni SPAN MultiJPG 4×. MultiJPG handles JPEG-compressed and previously resized images. SeedVR2 3B INT8 and VOSR 2.0 reconstruct detail locally
and are downloaded on demand.
Real-ESRGAN Anime 4× and AnimeSharp 4× are intended for drawings and illustrations.
All classic upscaler weights are bundled in `models/upscale_models`, including both Real-ESRGAN scales. The app verifies the local weights on first use and sets up the processing runtime if needed.

The preview uses the saved file. Drag the divider to compare. Use the wheel
to zoom and drag with the right mouse button to pan. “100 %” or Ctrl+1 shows
the result at actual pixel size, or the input before a result is available.
Esc and Ctrl+0 fit the view. Under “Results,” use “Previous”, “Next”, Page Up
or Page Down to browse saved images and variants. Results from the same input
with the same crop and rotation keep the current zoom and visible area.
"Use result as input" opens the displayed
result as a new input.
The status shows the processing stage, the device used and the elapsed time
for each result.

PNG is the default. JPEG uses quality 95 and 4:4:4. TIFF uses 8-bit RGB and
LZW compression. TIFF retains compatible EXIF and GPS data. JPEG also
retains compatible IPTC and XMP data. TIFF and JPEG include an sRGB profile
and updated orientation and size. JPEG writes processing settings to
XMP-restorenate:Settings. PNG stores the ComfyUI prompt and workflow when applicable.
Input preparation and padding may differ when rerunning the workflow in
ComfyUI. When colorization is followed by AI upscaling, the workflow starts
with the already colorized image.

File names include the input stem, a sequence number and the models used.
The sequence is per input stem and output folder across formats and methods.
For example, Image_01_Fibo-2.0_Nomos2-MoSR.png.
The base variants use `Qwen-2509`, `Qwen-2511`, and `FireRed-1.1` in file
names. Lightning adds `-4step` for Qwen and `-8step` for FireRed. Qwen 2509
with Nunchaku uses `Qwen-2509-Nunchaku`.

## Downloads and history

On first use, the app asks before downloading missing components.
“Download models …” next to “Method” sets up several methods and
upscalers in one pass. Lightning LoRAs appear under their base models.
Shared files are downloaded once. You can keep working with ready-to-use
methods during downloads. Runtime installation waits for the current job.
The Model downloads window shows progress and can be hidden. Cancelling
keeps resumable downloads. After setup, processing runs locally and offline.

NVIDIA and CPU share ComfyUI portable v0.44.0. AMD uses the separate
v0.45.0 archive. Model files are shared. If a ComfyUI download fails, put the
corresponding archive in downloads. RestoRenate verifies it before extraction.
See THIRD_PARTY.txt for sources and licenses.

logs/jobs.jsonl links results, crops, and rotations to their inputs. Selecting
an image or folder again restores its available results. “Clear history …”
removes these links after confirmation. The exported images stay on disk.
Technical logs rotate at 2 MiB and are cleaned up at startup after 30 days.
logs/backend.log also records the CPU thread count. Set
RESTORENATE_CPU_THREADS to use a fixed thread count for comparisons.

## New in 1.2

FLUX 3 Image Klein INT8 uses 16 steps and a local prompt upsampler. It is
available under “Download models …” in GPU modes. See `THIRD_PARTY.txt` for sources and licensing.

## New in 1.1

The second image can be cropped and rotated independently. Image 1 determines
the output crop. The prompt menu includes two compositing presets and
additional reusable instructions.

Choose from 50 StereoFine LUTs. **C** shows the look on the right.
Hold **C** with the left or right arrow to choose a look, or with the
up or down arrow to change its strength. **Apply LUT** adds the look to the next
model run. **Create LUT variant** saves the selected input or result as a new
numbered file. Double-click the LUT strength slider to reset it to its default of 100%. **F1** opens Controls.

JPEG and TIFF retain compatible source EXIF data and store RestoRenate settings
in XMP. PNG uses ComfyUI prompt and workflow metadata. See
the LUT sources and licenses in `assets/luts/CREDITS.md`.
