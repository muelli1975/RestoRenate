# RestoRenate

Local image restoration, colorization, and AI-powered editing for Windows.

[Deutsch](#deutsch) · [Detailed guide / Ausführliche Anleitung](README_DE_EN.txt)

RestoRenate can restore damaged images, colorize black-and-white originals,
and edit images using text prompts. It supports individual images and folders,
rotation and cropping before processing, a before-and-after slider, and
optional upscaling. Compatible edit models accept a second image. The seed
can be entered or imported from a PNG containing a ComfyUI workflow.
Processing runs locally and works offline after the selected models and
runtime have been downloaded.

## Windows

Extract the portable Windows x64 package to a short, writable path and open
`Start.cmd`. Choose an image or folder, an output folder, and a method. The app
asks before downloading missing files and shows the download size.

Microsoft · Bringing Old Photos Back to Life, CPU colorization, and Lanczos
are practical starting points for CPU processing. Large prompt-based models
can take substantial time and RAM on the CPU. NVIDIA is the default GPU
mode. AMD (ROCm) is experimental and depends on the Radeon model and driver.
Qwen 2509 Nunchaku requires a compatible NVIDIA RTX 30 or RTX 40 GPU and driver.
Qwen 2509 and 2511 offer four-step Lightning and standard processing in NVIDIA, CPU and AMD (ROCm) modes.

## Source and license

The source tree contains the application, download manifests, and the
ComfyUI adapters. The portable package supplies Python, ExifTool, 7-Zip,
and the bundled dependency wheels. To try changes on Windows, copy the
source files over a separate copy of the matching portable package and
run `Start.cmd` there.

RestoRenate's own code is under the [MIT License](LICENSE). See
[THIRD_PARTY.txt](THIRD_PARTY.txt) for the separate licenses and sources
of third-party components and model weights.

## Deutsch

RestoRenate restauriert beschädigte Bilder, koloriert Schwarzweißbilder
und bearbeitet Bilder per Prompt. Es unterstützt Einzelbilder und Ordner,
Drehen und Beschnitt vor der Bearbeitung, einen Vorher-Nachher-Regler und
optionale Nachskalierung. Kompatible Edit-Modelle können ein zweites Bild
einbeziehen. Der Seed lässt sich eingeben oder aus einer PNG-Datei mit
ComfyUI-Workflow übernehmen. Nach der Einrichtung läuft die Verarbeitung
lokal und offline.

Das portable Windows-x64-Paket in einen kurzen, beschreibbaren Pfad
entpacken und `Start.cmd` öffnen. Ein Bild oder einen Ordner, einen
Ausgabeordner und ein Verfahren auswählen. Vor dem Download fehlender Dateien zeigt die App die
benötigte Downloadmenge an.

Für CPU-Bearbeitung eignen sich besonders Microsoft · Bringing Old Photos
Back to Life, die Kolorierung und Lanczos. Große Modelle mit Texteingabe
können auf der CPU viel Zeit und Arbeitsspeicher benötigen. NVIDIA ist
voreingestellt. AMD (ROCm) ist experimentell und hängt von Grafikkarte und
Treiber ab. Qwen 2509 Nunchaku braucht eine kompatible NVIDIA RTX 30 oder
RTX 40 mit passendem Treiber.
Qwen 2509 und 2511 bieten Lightning mit vier Schritten und die reguläre
Berechnung in den Modi NVIDIA, CPU und AMD (ROCm).

Zum Testen von Quellcodeänderungen die Quelldateien in eine separate Kopie
des passenden portablen Pakets kopieren und dort `Start.cmd` öffnen.
Der eigene RestoRenate-Code steht unter der [MIT-Lizenz](LICENSE). Quellen
und Lizenzen der Fremdkomponenten und Modelle stehen in
[THIRD_PARTY.txt](THIRD_PARTY.txt).
