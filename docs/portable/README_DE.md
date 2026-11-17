# RestoRenate 1.3

Portable Ausgabe

## Start und Update

Die gesamte ZIP in einen kurzen, beschreibbaren Pfad entpacken, etwa
D:\RestoRenate, und RestoRenate.exe öffnen. Für ein Update RestoRenate beenden
und den Inhalt des Ordners RestoRenate aus der ZIP in den bestehenden
Programmordner kopieren und die Programmdateien ersetzen.
Modelle, Einstellungen und eigene Presets lassen sich weiterverwenden.

Linux: Das Archiv entpacken und ./Start.sh in einer grafischen Sitzung starten.
macOS 15+: Die ZIP entpacken und RestoRenate.app aus dem Ordner öffnen.
Python, Tk und ExifTool sind enthalten. ExifTool verwendet das Perl des Systems.

Ein Bild oder einen Ordner öffnen und ein Verfahren auswählen.
Die Eingabe unterstützt JPEG, PNG, TIFF, WebP, BMP und AVIF. „Beschnitt …“
öffnet einen Rahmen mit Drittelraster. Zum Verschieben innerhalb des Rahmens
ziehen, zur Größenänderung an den Griffen. „Frei“, ein festes Seitenverhältnis
oder „Benutzerdefiniert …“ für ein Verhältnis wie 7:5 wählen. In einem Ordner lässt sich
jedes Bild einzeln auswählen und beschneiden. „Übernehmen“ zeigt das ausgewählte
Bild in der Hauptansicht. „Drehen“ dreht das dort angezeigte Eingabebild um
90° nach links oder rechts oder um 180°. Ein bestehender Beschnitt dreht mit.
Die App dreht vor dem Beschnitt und der Bearbeitung. Die Originaldatei bleibt
erhalten. Die Menüsprache folgt beim ersten Start der Systemsprache und
lässt sich im laufenden Fenster umschalten. Die Vergleichsansicht bleibt
mit Zoom und Reglerposition geöffnet.

„Zweites Bild“ unter der Eingabe steht für Fibo 2.0 Edit Turbo, FLUX.2 [klein]
4B, FLUX 3 Image Klein, Qwen Image Edit 2509 und 2511 einschließlich Nunchaku
sowie FireRed Image Edit 1.1 zur Verfügung. „Bild …“ lädt das zweite Bild in die Vorschau.
Es lässt sich separat beschneiden, drehen, ersetzen oder entfernen.
Bei einem Ordner gilt es für alle Eingabebilder. Im Prompt lässt sich etwa
beschreiben, welche Inhalte aus Bild 2 in Bild 1 übernommen werden sollen.
Für Fibo die Platzhalter `<image_1>` und `<image_2>` verwenden.

## Prompts und Presets

„Satzbausteine“ neben „Prompt speichern …“ öffnet oberhalb des Buttons die
vorhandenen Kategorien. Ein Baustein hängt einen englischen Satz an den
Prompt an. Rechtsklick im Textfeld öffnet das Textmenü. „Prompt speichern …“
legt den eigenen Text in der gemeinsamen Promptliste ab.
„Allround“ ist der Standard für neue Einstellungen.
Die Modelle mit Texteingabe übernehmen beim Wechsel den aktuellen Prompt.
„Restaurieren und kolorieren 1“ und „Restaurieren und kolorieren 2“ stammen
aus den Beispielworkflows von Weird Wonderful AI Art. Der Modellname bei
einem Prompt kennzeichnet das dafür empfohlene Verfahren.

Unter „Presets“ lassen sich das Verfahren, der Prompt, die Varianten und
die zugehörigen Ausgabe- und Modelleinstellungen speichern. Eingabe und Ausgabeordner
bleiben beim Laden ausgewählt. Die GPU-Startvorgabe und „Standard“ im GPU-Modus
verwenden Fibo 2.0 Edit Turbo, „Allround“ und Nomos2 HQ MoSR 4×.
„Detailrekonstruktion“ steht im selben Menü im GPU-Modus zur Auswahl und
verwendet bei denselben Einstellungen VOSR 2.0 als Upscaler.
Gespeicherte Einstellungen haben beim Start Vorrang.

Start berechnet und speichert das Ergebnis. Bei Verfahren mit Prompt unter
„Varianten pro Bild“ eine Zahl von 1 bis 100 eintippen oder mit den Pfeilen
einstellen. Bei einer Ordnerauswahl gilt die Anzahl für jedes Bild.
Beim Programmstart ist das Seed-Feld leer und die App wählt Zufallswerte.
Einen festen Seed für die laufende Sitzung eintippen,
mit „Letzten übernehmen“ aus dem zuletzt berechneten Ergebnis übernehmen
oder mit „Aus PNG übernehmen …“ aus den ComfyUI-Metadaten einer PNG-Datei
lesen. Bei mehreren Varianten zählt die App vom festen Seed aus pro Bild
jeweils um eins hoch. Während eines Auftrags lässt sich
der Prompt für den nächsten Auftrag bearbeiten. „Abbrechen“ beendet den
laufenden Auftrag. „Nach Bild stoppen“ beziehungsweise „Nach Variante
stoppen“ lässt das aktuelle Ergebnis fertig werden. Nach einem erfolgreich
abgeschlossenen Auftrag ertönt der Abschlusston.

## Verfahren und Hardware

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
- Qwen Image Edit 2509 und 2511 sind als Basisvariante und mit Lightning
  (vier Schritte) verfügbar. Im CPU-Modus stehen die Lightning-Varianten zur Wahl.
  In der Basisvariante verwendet 2509 20 Schritte, 2511 40 Schritte, jeweils
  mit CFG 4. Pro Modell teilen sich beide Varianten dieselbe Q4_K_M-Datei.
  Je Lightning-LoRA kommen rund 850 MB hinzu.
- FireRed Image Edit 1.1 bietet eine Basisvariante mit 40 Schritten bei
  CFG 4 und Lightning mit acht Schritten. Beide Varianten benötigen eine GPU und nutzen
  dieselbe Q4_K_M-Datei. Für Lightning kommen rund 850 MB für die LoRA hinzu.
  FireRed und die Qwen-Verfahren teilen sich Textencoder und VAE. Die GGUF-Verfahren
  wählen eine Arbeitsfläche um 1 MP. Ergänzte Ränder entfernt die App
  anschließend. Die Gewichte stehen unter Apache 2.0.
- Microsoft · Bringing Old Photos Back to Life restauriert mit bis zu
  2048 px an der langen Seite und liefert ein Ergebnis pro Bild. Es gibt
  separate Optionen für Kratzer und Gesichter. Die Gesichtsverbesserung
  lädt zusätzliche Dateien und nutzt Gesichtspunkte aus iBUG 300-W
  (nicht kommerziell).
- DDColor ModelScope, Paper, Artistic und Tiny sowie DeOldify Stable und Artistic
  kolorieren auf der CPU. Sie kombinieren die geschätzten Farben mit der
  Helligkeitsstruktur des Originals. ONNX Runtime wählt die CPU-Threadzahl.
  „Ohne Nachskalierung“ ist voreingestellt.

Unter „Berechnung“ NVIDIA, CPU oder AMD (ROCm) wählen. Ein Wechsel gilt
nach einem Neustart. Die App merkt sich Verfahren und Skalierung getrennt für
CPU und GPU. Der CPU-Standard ist Microsoft · Bringing Old Photos Back to Life
mit „Ohne Nachskalierung“. Bei einem NVIDIA-Startfehler bietet die App für
geeignete Verfahren an, denselben Auftrag in dieser Sitzung auf der CPU
fortzusetzen. Bei den Edit-Modellen stehen Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B
und die beiden Qwen-Lightning-Varianten mit je vier Schritten zur Wahl.
Auch diese Modelle können auf der CPU sehr lange laufen
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

## Ausgabe und Vorschau

„Unterordner im Eingabeordner verwenden“ ist voreingestellt. Das Ziel ist
der Ordner output neben dem gewählten Einzelbild oder im gewählten
Eingabeordner. Eine neue Eingabe ändert das Ziel entsprechend.
„Auswählen …“ wechselt zu einem eigenen Ausgabeordner. Die Ergebnisse
landen direkt dort. Der eigene Pfad und der Modus werden getrennt gespeichert.

„Zielgröße“ zeigt die berechneten Maße für das aktuelle Bild. 1080 px und
2160 px beziehen sich auf die Bildhöhe. „Lange Seite“ und „Kurze Seite“
verwenden eine eingegebene Seitenlänge. Die App hält das Seitenverhältnis.
„Ohne Nachskalierung“ speichert in Arbeitsauflösung. „Nur hochskalieren“
arbeitet mit dem Eingabebild. KI-Upscaling wird beim Vergrößern verwendet.
Real-ESRGAN wählt ein 2×- oder 4×-Modell. Lanczos passt auf die exakte
Zielgröße an. Die GPU-Voreinstellung für Restaurierung ist Fibo 2.0 Edit Turbo
mit 2160 px Bildhöhe und Nomos2 HQ MoSR 4×. „Nur hochskalieren“ verwendet
im GPU-Modus dieselbe Voreinstellung für Zielgröße und Upscaler.
4× FaceUpDAT ist für Porträts mit sauberer Vorlage gedacht.
Das Upscaler-Menü gruppiert die Modelle nach Einsatzbereich.
Nomos2 HQ MoSR 4× und Nomos2 HQ DAT2 4× sind für saubere Fotos gedacht. Nomos8kDAT 4× ist für kleine
und komprimierte Fotos gedacht. SeedVR2 3B INT8 und VOSR 2.0 sind
lokale Verfahren zur Detailrekonstruktion und werden bei Bedarf geladen.
Real-ESRGAN Anime 4× und AnimeSharp 4× sind für Zeichnungen und Illustrationen
gedacht. Beide Modelle werden bei Bedarf heruntergeladen.

Die Vorschau zeigt die gespeicherte Datei. Zum Vergleichen die Trennlinie
ziehen. Das Mausrad zoomt, die rechte Maustaste verschiebt die Ansicht.
„100 %“ oder Strg+1 zeigt das Ergebnis in Pixelgröße, vor dem ersten Ergebnis
die Eingabe. Esc und Strg+0 passen die Ansicht ein. Unter „Ergebnisse“ mit
„Zurück“, „Weiter“ oder Bild↑ und Bild↓ durch fertige Bilder und Varianten
blättern. Bei Varianten derselben Eingabe mit gleichem Beschnitt und gleicher Drehung bleiben
Zoom und Bildausschnitt erhalten. "Ergebnis weiterbearbeiten" übernimmt
das angezeigte Ergebnis als Eingabebild.
Der Status zeigt den Verarbeitungsschritt, das verwendete Gerät und die
verstrichene Zeit pro Ergebnis.

PNG ist voreingestellt. JPEG verwendet Qualität 95 und 4:4:4. TIFF wird als
RGB mit 8 Bit je Kanal und LZW gespeichert. TIFF übernimmt geeignete EXIF-
und GPS-Daten. JPEG übernimmt auch passende IPTC- und XMP-Daten. TIFF und
JPEG enthalten ein sRGB-Profil und aktualisierte Angaben zu Ausrichtung und
Größe. JPEG speichert die Bearbeitungseinstellungen in XMP-restorenate:Settings.
PNG enthält bei ComfyUI-Bearbeitung Prompt und Workflow. Beim erneuten
Ausführen in ComfyUI können Eingabeaufbereitung und Randbehandlung abweichen.
Bei Kolorierung mit KI-Upscaling beschreibt der Workflow das Upscaling mit
dem bereits kolorierten Bild als Eingabe.

Dateinamen enthalten Eingabename, fortlaufende Nummer und die verwendeten
Modelle. Die Nummer läuft pro Eingabename und Ausgabeordner über die
Ausgabeformate und Verfahren hinweg. Beispiel: Bild_01_Fibo-2.0_Nomos2-MoSR.png.
Die Basisvarianten heißen im Dateinamen `Qwen-2509`, `Qwen-2511` und
`FireRed-1.1`. Lightning ergänzt bei Qwen `-4step` und bei FireRed
`-8step`. Qwen 2509 mit Nunchaku verwendet `Qwen-2509-Nunchaku`.

## Downloads und Verlauf

Beim ersten Einsatz fragt die App vor dem Download fehlender Komponenten.
„Modelle vorab laden …“ neben „Verfahren“ richtet mehrere Verfahren und Upscaler
in einem Durchgang ein. Lightning-LoRAs stehen unter ihrem Basismodell.
Gemeinsame Dateien werden einmal geladen. Während des Downloads stehen
bereits einsatzbereite Verfahren zur Verfügung. Die Einrichtung einer Laufzeit
wartet auf die laufende Bearbeitung. Das Fenster „Modelldownloads“ zeigt den
Fortschritt und lässt sich ausblenden. Ein Abbruch erhält fortsetzbare
Downloads. Nach der Einrichtung läuft die Verarbeitung lokal und offline.

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

## Neu in 1.2

FLUX 3 Image Klein INT8 arbeitet in 16 Schritten mit einem lokalen
Prompt-Umschreiber. Das Modell ist in den GPU-Modi über „Modelle vorab laden …“
verfügbar. Quellen und Lizenz stehen in `THIRD_PARTY.txt`.

## Neu in 1.1

Bild 2 kann unabhängig beschnitten und gedreht werden. Den Ausgabeausschnitt bestimmt Bild 1. Zwei Montage-Presets und zusätzliche Satzbausteine stehen im Prompt-Menü bereit.

50 StereoFine-LUTs stehen zur Auswahl. **C** zeigt den Look rechts an, **C** mit Links/Rechts wählt den Look und **C** mit Hoch/Runter ändert seine Stärke. **LUT anwenden** nimmt den Look in den nächsten Modelllauf auf. **Variante mit LUT erstellen** speichert die gewählte Eingabe oder das Ergebnis als neue Datei mit Folgenummer. **F1** öffnet die Bedienhilfe.

JPEG und TIFF übernehmen geeignete Original-EXIF-Daten und speichern die RestoRenate-Einstellungen in XMP. PNG verwendet die Prompt- und Workflow-Metadaten von ComfyUI. Die Quellen und Lizenzen sind unter assets/luts/CREDITS.md dokumentiert.
