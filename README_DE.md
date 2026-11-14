# RestoRenate 1.0

[Downloads](https://github.com/muelli1975/RestoRenate/releases/tag/v1.0) · [English](README.md) · [Ausführliche Anleitung](README_DE_EN.txt)

RestoRenate restauriert, koloriert und vergrößert Fotos lokal auf dem Rechner. Mit unterstützten Modellen lassen sich Bilder auch per Prompt bearbeiten oder anhand eines zweiten Fotos verändern. Die Oberfläche ist auf Deutsch und Englisch verfügbar.

Die App fragt vor dem Download fehlender Modelle und Laufzeitdateien nach. Nach der Einrichtung funktioniert die Bildbearbeitung offline.

## Voraussetzungen und Start

| Plattform | Paket und Voraussetzungen |
| --- | --- |
| Windows x64 | Die [portable ZIP](https://github.com/muelli1975/RestoRenate/releases/download/v1.0/RestoRenate_1.0_Windows_x64.zip) in einen kurzen, beschreibbaren Pfad wie `D:\RestoRenate` entpacken und `RestoRenate.exe` öffnen. Python und ExifTool sind enthalten. |
| Ubuntu 24.04 x86-64 | Die Linux-Vorschau wird mit [GitHub Actions](https://github.com/muelli1975/RestoRenate/actions/workflows/linux.yml) gebaut und geprüft. `python3.12-venv`, `python3-tk`, `git` und `libimage-exiftool-perl` installieren, das `.tar.gz` in einen beschreibbaren Ordner entpacken und `./Start.sh` aufrufen. Das Skript legt die Python-Umgebung im Programmordner an. |

Unter Windows stehen CPU und NVIDIA sowie AMD ROCm als experimentelle Option zur Wahl. Die Linux-Vorschau startet standardmäßig auf der CPU und bietet NVIDIA mit einem CUDA-13-tauglichen Treiber als experimentelle Option an. Nunchaku INT4 ist auf unterstützten NVIDIA-Systemen unter Windows verfügbar. macOS-Pakete sind geplant.

Für ein Windows-Update RestoRenate schließen und das neue Paket in einen sauberen Ordner entpacken. Zum Übernehmen der bestehenden Einrichtung können `models`, `backend`, `downloads`, `settings` sowie die benötigten Laufzeit-Unterordner und Download-Prüfbelege übernommen werden. `_internal`, `assets` und `tools` gehören zum neuen Paket.

## Schnellstart

1. Ein Foto oder einen Ordner öffnen. Die Eingabe bei Bedarf beschneiden oder drehen.
2. Ausgabeordner, Format und Größe wählen, dann ein Verfahren auswählen. Bei Modellen mit Texteingabe den Prompt bearbeiten.
3. **Start** wählen. Über **Modelle vorab laden …** lassen sich mehrere Verfahren gemeinsam einrichten. Optionale Lightning-LoRAs stehen unter ihrem Basismodell.
4. Das gespeicherte Ergebnis mit dem Vorher-Nachher-Regler vergleichen. **Strg+1** zeigt 100 %, **Esc** passt die Ansicht ein. **Bild↑ / Bild↓** blättern durch die Ergebnisse.

## Modelle und Ausgabe

- **Restaurierung und Bearbeitung:** Microsoft Bringing Old Photos Back to Life, Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B, Qwen Image Edit 2509/2511 und FireRed Image Edit 1.1. Unterstützte Edit-Modelle können ein separat drehbares zweites Bild nutzen.
- **Kolorierung:** DDColor ModelScope, Paper, Artistic und Tiny sowie DeOldify Stable und Artistic. Die Kolorierung läuft auf der CPU. DDColor Paper ist ein optionaler Download.
- **Hochskalieren:** Lanczos und mehrere KI-Upscaler, darunter Nomos2 HQ MoSR, Real-ESRGAN und FaceUpDAT für Porträts.
- **Export:** PNG, JPEG mit Qualität 95 und 4:4:4 sowie TIFF mit LZW-Kompression. JPEG und TIFF übernehmen geeignete Metadaten. PNG speichert bei ComfyUI-Verarbeitung den Workflow.

## Quellcode und Builds

Der Quellcode enthält die Anwendung, Downloadlisten und ComfyUI-Adapter. Die Builds und Tests stehen unter [GitHub Actions](https://github.com/muelli1975/RestoRenate/actions). Das portable Windows-Paket enthält den Starter, die Python-Umgebung und die Exportwerkzeuge.

## Lizenz

RestoRenates eigener Code steht unter der [MIT-Lizenz](LICENSE). Die Lizenzen für Fremdkomponenten und Modelle stehen in [THIRD_PARTY.txt](THIRD_PARTY.txt).
