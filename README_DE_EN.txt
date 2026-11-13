RestoRenate 0.2.80
Windows x64 · Portable

DEUTSCH

Start und Update

Die gesamte ZIP in einen kurzen, beschreibbaren Pfad entpacken, etwa
D:\RestoRenate, und Start.cmd öffnen. Für ein Update RestoRenate beenden
und den Inhalt des Ordners RestoRenate aus der ZIP in den bestehenden
Programmordner neben Start.cmd kopieren. Die Programmdateien ersetzen.
Modelle, Einstellungen und eigene Presets lassen sich weiterverwenden.

Ein Bild oder einen Ordner, den Ausgabeordner und ein Verfahren auswählen.
Die Eingabe unterstützt JPEG, PNG, TIFF, WebP, BMP und AVIF. „Beschnitt …“
öffnet einen Rahmen mit Drittelraster. Zum Verschieben innerhalb des Rahmens
ziehen, zur Größenänderung an den Griffen. „Frei“, ein festes Seitenverhältnis
oder „Benutzerdefiniert …“ für ein Verhältnis wie 7:5 wählen. In einem Ordner lässt sich
jedes Bild einzeln auswählen und beschneiden. „Übernehmen“ zeigt das ausgewählte
Bild in der Hauptansicht. „Drehen“ dreht das dort angezeigte Eingabebild um
90° nach links oder rechts oder um 180°. Ein bestehender Beschnitt dreht mit.
Die App dreht vor dem Beschnitt und der Bearbeitung. Die Originaldatei bleibt
erhalten. Die Menüsprache folgt beim ersten Start der Systemsprache.

„Zweites Bild hinzufügen …“ steht für Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B,
Qwen Image Edit 2509 und 2511 einschließlich Nunchaku sowie FireRed Image
Edit 1.1 zur Verfügung. Das zweite Bild lässt sich ersetzen oder entfernen.
Bei einem Ordner gilt es für alle Eingabebilder. Im Prompt lässt sich etwa
beschreiben, welche Inhalte aus Bild 2 in Bild 1 übernommen werden sollen.
Für Fibo die Platzhalter `<image_1>` und `<image_2>` verwenden.

Prompts und Presets

„Satzbausteine“ neben „Prompt speichern …“ öffnet oberhalb des Buttons die
vorhandenen Kategorien. Ein Baustein hängt einen englischen Satz an den
Prompt an. Rechtsklick im Textfeld öffnet das Textmenü. „Prompt speichern …“
legt den eigenen Text in der gemeinsamen Promptliste ab.
Die Modelle mit Texteingabe übernehmen beim Wechsel den aktuellen Prompt.
„Restaurieren und kolorieren 1“ und „Restaurieren und kolorieren 2“ stammen
aus den Beispielworkflows von Weird Wonderful AI Art. Der Modellname bei
einem Prompt kennzeichnet das dafür empfohlene Verfahren.

Unter „Presets“ lassen sich das Verfahren, der Prompt, die Varianten und
die zugehörigen Ausgabe- und Modelleinstellungen speichern. Eingabe und Ausgabeordner
bleiben beim Laden ausgewählt. Die Startvorgabe und „Standard“ verwenden
Fibo 2.0 Edit Turbo, „Restaurieren und kolorieren 1“ und Nomos2 HQ MoSR 4×.
Gespeicherte Einstellungen haben beim Start Vorrang.

Start berechnet und speichert das Ergebnis. Bei Verfahren mit Prompt unter
„Varianten pro Bild“ eine Zahl von 1 bis 100 eintippen oder mit den Pfeilen
einstellen. Bei einer Ordnerauswahl gilt die Anzahl für jedes Bild.
Bei leerem Seed-Feld wählt die App Zufallswerte. Einen festen Seed eintippen,
mit „Letzten übernehmen“ aus dem zuletzt berechneten Ergebnis übernehmen
oder mit „Aus PNG übernehmen …“ aus den ComfyUI-Metadaten einer PNG-Datei
lesen. Bei mehreren Varianten zählt die App vom festen Seed aus pro Bild
jeweils um eins hoch. Während eines Auftrags lässt sich
der Prompt für den nächsten Auftrag bearbeiten. „Abbrechen“ beendet den
laufenden Auftrag. „Nach Bild stoppen“ beziehungsweise „Nach Variante
stoppen“ lässt das aktuelle Ergebnis fertig werden. Nach einem erfolgreich
abgeschlossenen Auftrag ertönt der Abschlusston.

Verfahren und Hardware

- Fibo 2.0 Edit Turbo arbeitet mit vier Schritten und einer zum Bild passenden
  Arbeitsfläche um 1 MP. Modell und Textencoder benötigen zusätzlich 13,3 GB.
  Der Bilddecoder wird mit FLUX.2 geteilt. Die Fibo-Gewichte stehen unter
  CC BY-NC 4.0.
- FLUX.2 [klein] 4B skaliert das Bild proportional auf etwa 1 MP und arbeitet
  mit vier Schritten. Die Gewichte stehen unter Apache 2.0.
- Qwen Image Edit 2509 · Nunchaku INT4 skaliert proportional auf etwa 1 MP.
  Das Modell verwendet R32 mit vier integrierten Lightning-Schritten und
  CPU-Offload. Es braucht eine NVIDIA RTX 30 oder 40 mit einem Treiber für
  CUDA 13. Das Verfahren steht nur bei passender NVIDIA-Hardware zur Wahl.
- Qwen Image Edit 2509 und 2511 bieten Lightning mit vier Schritten sowie
  „Ohne Lightning“ in den Modi NVIDIA, CPU und AMD (ROCm).
  Ohne Lightning verwendet 2509 20 Schritte, 2511 40 Schritte, jeweils mit
  CFG 4. Pro Modell teilen sich diese Varianten dieselbe Q4_K_M-Datei.
  Je Lightning-LoRA kommen rund 850 MB hinzu.
- FireRed Image Edit 1.1 bietet Lightning mit acht Schritten und
  „Ohne Lightning“ mit 40 Schritten bei CFG 4. Beide Varianten nutzen
  dieselbe Q4_K_M-Datei. Für Lightning kommen rund 850 MB für die LoRA hinzu.
  FireRed und die Qwen-Verfahren teilen sich Textencoder und VAE. Die GGUF-Verfahren
  wählen eine Arbeitsfläche um 1 MP. Ergänzte Ränder entfernt die App
  anschließend. Die Gewichte stehen unter Apache 2.0.
- Microsoft · Bringing Old Photos Back to Life restauriert mit bis zu
  2048 px an der langen Seite und liefert ein Ergebnis pro Bild. Es gibt
  separate Optionen für Kratzer und Gesichter. Die Gesichtsverbesserung
  lädt zusätzliche Dateien und nutzt Gesichtspunkte aus iBUG 300-W
  (nicht kommerziell).
- DDColor, DDColor Artistic, DeOldify Stable und DeOldify Artistic
  kolorieren auf der CPU. Sie kombinieren die geschätzten Farben mit der
  Helligkeitsstruktur des Originals. „Ohne Nachskalierung“ ist voreingestellt.

Unter „Berechnung“ NVIDIA, CPU oder AMD (ROCm) wählen. Ein Wechsel gilt
nach einem Neustart. Bei einem NVIDIA-Startfehler bietet die App für geeignete
Verfahren einen CPU-Wechsel für diese Sitzung an. Für CPU-Bearbeitung eignen
sich besonders Microsoft · Bringing Old Photos Back to Life, die Kolorierung
und Lanczos. Die großen Edit-Modelle können auf der CPU sehr lange laufen
und viel Arbeitsspeicher beanspruchen. Auch KI-Upscaling benötigt Rechenzeit.
Bei GPU-Verfahren hängt die Eignung für 8 GB VRAM von Modell, Bild sowie
verfügbarem Grafik- und Arbeitsspeicher ab.

AMD (ROCm) ist experimentell. Die App verwendet das offizielle portable
ComfyUI-Paket v0.45.0 für AMD mit ROCm 7.2 und prüft bei der Einrichtung einen
GPU-Rechenvorgang. Vorausgesetzt sind Windows 11, eine unterstützte Radeon
und ein passender Treiber. Die GPU-Prüfung bestätigt die Funktion der Laufzeit. Die
Modellkompatibilität hängt auch von der Karte und den verwendeten Operationen ab.
Die Kompatibilitätsliste steht unter
https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html

Ausgabe und Vorschau

„Zielgröße“ zeigt die berechneten Maße für das aktuelle Bild. 1080 px und
2160 px beziehen sich auf die Bildhöhe. „Lange Seite“ und „Kurze Seite“
verwenden eine eingegebene Seitenlänge. Die App hält das Seitenverhältnis.
„Ohne Nachskalierung“ speichert in Arbeitsauflösung. „Nur hochskalieren“
arbeitet mit dem Eingabebild. KI-Upscaling wird beim Vergrößern verwendet.
Real-ESRGAN wählt ein 2×- oder 4×-Modell. Lanczos passt auf die exakte
Zielgröße an. Für Restaurierung und „Nur hochskalieren“ sind 2160 px Bildhöhe
und Nomos2 HQ MoSR 4× voreingestellt.

Die Vorschau zeigt die gespeicherte Datei. Zum Vergleichen die Trennlinie
ziehen. Das Mausrad zoomt, die rechte Maustaste verschiebt die Ansicht.
„Ansicht einpassen“ setzt den Zoom zurück. Unter „Ergebnisse“ mit „Zurück“
und „Weiter“ durch fertige Bilder und Varianten blättern. „Ergebnis
weiterbearbeiten“ übernimmt das angezeigte Ergebnis als Eingabebild.
Der Status zeigt den Verarbeitungsschritt, das verwendete Gerät und die
verstrichene Zeit pro Ergebnis.

PNG ist voreingestellt. JPEG verwendet Qualität 95 und 4:4:4. TIFF wird als
RGB mit 8 Bit je Kanal und LZW gespeichert. TIFF übernimmt geeignete EXIF-
und GPS-Daten. JPEG übernimmt auch passende IPTC- und XMP-Daten. TIFF und
JPEG enthalten ein sRGB-Profil und aktualisierte Angaben zu Ausrichtung und
Größe. JPEG speichert die Bearbeitungseinstellungen in XMP-fr:Settings.
PNG enthält bei ComfyUI-Bearbeitung Prompt und Workflow. Beim erneuten
Ausführen in ComfyUI können Eingabeaufbereitung und Randbehandlung abweichen.
Bei Kolorierung mit KI-Upscaling beschreibt der Workflow das Upscaling mit
dem bereits kolorierten Bild als Eingabe.

Dateinamen enthalten Eingabename, fortlaufende Nummer und die verwendeten
Modelle. Die Nummer läuft pro Eingabename und Ausgabeordner über die
Ausgabeformate und Verfahren hinweg. Beispiel: Bild_01_Fibo-2.0_Nomos2-MoSR.png.
Bei Qwen 2509 und 2511 steht die Schrittzahl im Modellzusatz, etwa
`Qwen-2509-4step` oder `Qwen-2511-40step`. Die Nunchaku-Variante verwendet
`Qwen-2509-Nunchaku`.
FireRed verwendet `FireRed-1.1-8step` oder `FireRed-1.1-40step`.

Downloads und Verlauf

Beim ersten Einsatz fragt die App vor dem Download fehlender Komponenten.
„Berechnung → Modelle vorab laden …“ richtet mehrere Verfahren und Upscaler
in einem Durchgang ein. Gemeinsame Dateien werden einmal geladen. Ein
Abbruch lässt fortsetzbare Downloads erhalten. Nach der Einrichtung läuft
die Verarbeitung lokal und offline.

NVIDIA und CPU teilen sich das portable ComfyUI v0.44.0. AMD verwendet das
separate v0.45.0-Archiv. Die Modelldateien werden gemeinsam genutzt. Bei einem
fehlgeschlagenen Download kann das passende ComfyUI-Archiv manuell unter
downloads abgelegt werden. RestoRenate prüft es vor dem Entpacken. Quellen
und Lizenzen stehen in THIRD_PARTY.txt.

logs/jobs.jsonl verknüpft die Ergebnisse, Beschnitte und Drehungen mit ihrer
Eingabe. Bei erneuter Auswahl eines Bilds oder Ordners lädt die App
dessen verfügbare Ergebnisse. „Verlauf löschen …“ entfernt diese Zuordnung
nach Bestätigung. Die exportierten Bilder bleiben auf der Festplatte.
Technische Logs werden ab 2 MiB rotiert und beim Start nach 30 Tagen
bereinigt. logs/backend.log enthält auch die verwendete CPU-Threadzahl.
RESTORENATE_CPU_THREADS setzt für Vergleiche eine feste Threadzahl.


ENGLISH

Start and update

Extract the entire ZIP to a short, writable path such as D:\RestoRenate and
open Start.cmd. To update, close RestoRenate and copy the contents of the
RestoRenate folder in the ZIP into the existing program folder alongside
Start.cmd. Replace the program files. Models, settings and custom presets
can be reused.

Choose an image or folder, an output folder and a method. Input formats
include JPEG, PNG, TIFF, WebP, BMP and AVIF. “Crop …” opens a frame with a
rule-of-thirds grid. Drag inside the frame to move it or drag a handle to
resize it. Choose “Free,” a fixed ratio or “Custom …” for a ratio such as
7:5. Each image in a folder can be selected and cropped individually. “Apply”
shows the selected image in the main view. “Rotate” turns the input shown there
90° left or right or 180°. An existing crop rotates with it. Rotation takes
place before cropping and processing. The original file is preserved. The
app initially uses the system display language.

“Add second image …” is available for Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B,
Qwen Image Edit 2509 and 2511 including Nunchaku, and FireRed Image Edit 1.1.
The second image can be replaced or removed. For a folder, it applies to all
inputs. The prompt can describe which content to transfer from image 2 into
image 1. In Fibo prompts, use the placeholders `<image_1>` and `<image_2>`.

Prompts and presets

“Prompt snippets” beside “Save prompt …” opens the existing categories
above the button. Choosing a snippet appends an English sentence. Right-click
the field for text editing commands. “Save prompt …” adds the current text
to the shared prompt list. The current prompt carries over when switching
between methods with text input. “Restore and colorize 1” and “Restore and colorize
2” come from the Weird Wonderful AI Art example workflows. A model name in a
prompt label indicates the recommended method for that prompt.

Use “Presets” to save the method, prompt, variants and applicable output
and model settings. Loading a preset keeps the selected input and output
folder. The startup defaults and “Standard” use Fibo 2.0 Edit Turbo,
“Restore and colorize 1” and Nomos2 HQ MoSR 4×. Saved settings take
precedence at startup.

Start processes and saves the result. For prompt-based methods, type a number
from 1 to 100 in “Variants per image” or use the arrows. The count applies to
each image in a folder. Leaving the seed field blank uses random seeds. A
fixed seed can be entered, copied from the last result with “Use last seed,”
or read from a PNG's ComfyUI metadata with “Import from PNG …”. For multiple
variants, the fixed seed is incremented by one per variant for each image.
The prompt for the next job can be edited while
the current job runs.
“Cancel” ends the current job. “Stop after image” or “Stop after variant”
lets the current result finish. A completion sound plays after a successful job.

Methods and hardware

- Fibo 2.0 Edit Turbo uses four steps and a working canvas around one
  megapixel. The model and text encoder add a 13.3 GB download. It shares the
  image decoder with FLUX.2. The Fibo weights are licensed under CC BY-NC 4.0.
- FLUX.2 [klein] 4B uses four steps and resizes the image proportionally to
  about one megapixel. The weights are licensed under Apache 2.0.
- Qwen Image Edit 2509 · Nunchaku INT4 resizes proportionally to about one
  megapixel. It uses R32 with four integrated Lightning steps and CPU
  offloading. It requires a NVIDIA RTX 30 or 40 series GPU with a CUDA 13
  compatible driver. The method is shown on compatible NVIDIA hardware.
- Qwen Image Edit 2509 and 2511 offer four-step Lightning and
  “Without Lightning” in NVIDIA, CPU and AMD (ROCm) modes. Without
  Lightning, 2509 uses 20 steps and 2511 uses 40 steps, both at CFG 4.
  These variants share one Q4_K_M file per model. Each Lightning LoRA
  adds about 850 MB.
- FireRed Image Edit 1.1 offers eight-step Lightning and “Without Lightning”
  with 40 steps at CFG 4. Both variants share the same Q4_K_M file.
  The Lightning LoRA adds about 850 MB. FireRed and the Qwen methods share
  the text encoder and VAE. The GGUF methods use a working canvas around
  one megapixel. RestoRenate removes any added padding after processing.
  The weights are licensed under Apache 2.0.
- Microsoft · Bringing Old Photos Back to Life restores images at up to
  2048 px on the long edge and produces one result per image. Scratch repair
  and face enhancement are separate options. Face enhancement downloads
  additional files and uses iBUG 300-W facial landmarks (non-commercial).
- DDColor, DDColor Artistic, DeOldify Stable and DeOldify Artistic colorize
  on the CPU. They combine estimated colors with the original luminance.
  “No resizing” is the default.

Use “Compute” to choose NVIDIA, CPU or AMD (ROCm). The change takes effect
after restarting. If NVIDIA fails to start, the app offers a switch to CPU
for the current session when the method allows it. Microsoft · Bringing Old
Photos Back to Life, colorization and Lanczos are the practical CPU starting
points. Large edit models can take a long time and use substantial RAM on
the CPU. AI upscaling also takes processing time. Suitability for 8 GB of
VRAM depends on the model, the image and available GPU and system memory.

AMD (ROCm) is experimental. RestoRenate uses the official ComfyUI v0.45.0
AMD portable package with ROCm 7.2 and checks a GPU operation during setup.
It requires Windows 11, a supported Radeon GPU and a compatible driver.
The GPU check verifies the runtime. Model compatibility also depends on
the card and the operations used. See AMD’s compatibility list at
https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html

Output and preview

“Output size” shows the calculated dimensions for the current image.
The 1080 px and 2160 px options set image height. “Long edge” and “Short
edge” use the entered side length. RestoRenate preserves the aspect ratio.
“No resizing” exports at the working size. “Upscale only” starts with the
input image. AI upscaling applies when enlarging the image. Real-ESRGAN
selects its 2× or 4× model. Lanczos resizes to the exact output dimensions.
Restoration and “Upscale only” default to 2160 px height and Nomos2 HQ MoSR 4×.

The preview uses the saved file. Drag the divider to compare. Use the wheel
to zoom and drag with the right mouse button to pan. “Fit view” resets the
zoom. Under “Results,” use “Previous” and “Next” to browse saved images and
variants. “Use result as input” opens the displayed result as a new input.
The status shows the processing stage, the device used and the elapsed time
for each result.

PNG is the default. JPEG uses quality 95 and 4:4:4. TIFF uses 8-bit RGB and
LZW compression. TIFF retains compatible EXIF and GPS data. JPEG also
retains compatible IPTC and XMP data. TIFF and JPEG include an sRGB profile
and updated orientation and size. JPEG writes processing settings to
XMP-fr:Settings. PNG stores the ComfyUI prompt and workflow when applicable.
Input preparation and padding may differ when rerunning the workflow in
ComfyUI. When colorization is followed by AI upscaling, the workflow starts
with the already colorized image.

File names include the input stem, a sequence number and the models used.
The sequence is per input stem and output folder across formats and methods.
For example, Image_01_Fibo-2.0_Nomos2-MoSR.png.
Qwen 2509 and 2511 labels include the step count, for example
`Qwen-2509-4step` or `Qwen-2511-40step`. The Nunchaku variant uses
`Qwen-2509-Nunchaku`.
FireRed uses `FireRed-1.1-8step` or `FireRed-1.1-40step`.

Downloads and history

On first use, the app asks before downloading missing components.
“Compute → Download models in advance …” sets up several methods and
upscalers in one pass. Shared files are downloaded once. Cancelling keeps
resumable downloads. After setup, processing runs locally and offline.

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
