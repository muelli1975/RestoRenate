# RestoRenate 1.0

[Windows-Download](https://github.com/muelli1975/RestoRenate/releases/tag/v1.0) · [Linux-Vorschau](https://github.com/muelli1975/RestoRenate/releases/tag/v1.0-linux-preview) · [macOS-Vorschau](https://github.com/muelli1975/RestoRenate/releases/tag/v1.0-macos-preview) · [English](README.md) · [Ausführliche Anleitung](README_DE_EN.txt)

RestoRenate restauriert, koloriert und vergrößert Fotos lokal auf dem Rechner. Mit unterstützten Modellen lassen sich Bilder auch per Prompt bearbeiten oder anhand eines zweiten Fotos verändern. Die Oberfläche ist auf Deutsch und Englisch verfügbar.

Die App fragt vor dem Download fehlender Modelle und Laufzeitdateien nach. Nach der Einrichtung funktioniert die Bildbearbeitung offline.

## Voraussetzungen und Start

| Plattform | Paket und Voraussetzungen |
| --- | --- |
| Windows x64 | Die [portable ZIP](https://github.com/muelli1975/RestoRenate/releases/download/v1.0/RestoRenate_1.0_Windows_x64.zip) in einen kurzen, beschreibbaren Pfad wie `D:\RestoRenate` entpacken und `RestoRenate.exe` öffnen. Python und ExifTool sind enthalten. |
| Ubuntu 24.04 x86-64 | Portable Vorschau. Das `.tar.gz` in einen beschreibbaren Ordner entpacken und `./Start.sh` in einer grafischen Sitzung starten. |
| macOS 15 oder neuer, Apple Silicon | Portable Vorschau. Die ZIP in einen beschreibbaren Ordner entpacken und `RestoRenate.app` aus diesem Ordner öffnen. |

Beide Vorschauen enthalten Python, Tk und ExifTool. ExifTool verwendet das Perl des Systems. RestoRenate lädt ausgewählte Modelle und Rechenbibliotheken bei Bedarf in den Programmordner. [Linux-Builds](https://github.com/muelli1975/RestoRenate/actions/workflows/linux.yml) · [macOS-Builds](https://github.com/muelli1975/RestoRenate/actions/workflows/macos.yml)

Unter Windows stehen CPU und NVIDIA sowie AMD ROCm als experimentelle Option zur Wahl. Die Linux-Vorschau startet standardmäßig auf der CPU und bietet experimentelle Modi für NVIDIA (CUDA-13-tauglicher Treiber) und AMD ([mit ROCm 7.2 kompatible Hardware und Treiber](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html)). Die macOS-Vorschau verwendet standardmäßig Apple Metal (MPS) und bietet auch CPU-Berechnung. Nunchaku INT4 ist auf unterstützten NVIDIA-Systemen unter Windows verfügbar.

Für ein Windows-Update RestoRenate schließen und das neue Paket in einen sauberen Ordner entpacken. Zum Übernehmen der bestehenden Einrichtung können `models`, `backend`, `downloads`, `settings` sowie die benötigten Laufzeit-Unterordner und Download-Prüfbelege übernommen werden. `_internal`, `assets` und `tools` gehören zum neuen Paket.

## Schnellstart

1. Ein Foto oder einen Ordner öffnen. Die Eingabe bei Bedarf beschneiden oder drehen.
2. Ausgabeziel prüfen, Format und Größe wählen, dann ein Verfahren auswählen. Bei Modellen mit Texteingabe den Prompt bearbeiten.
3. **Start** wählen. Über **Modelle vorab laden …** lassen sich mehrere Verfahren gemeinsam einrichten. Optionale Lightning-LoRAs stehen unter ihrem Basismodell.
4. Das gespeicherte Ergebnis mit dem Vorher-Nachher-Regler vergleichen. **Strg+1** zeigt 100 %, **Esc** passt die Ansicht ein. **Bild↑ / Bild↓** blättern durch die Ergebnisse.

## Modelle und Ausgabe

Standardmäßig landen die Ergebnisse in `output` neben dem gewählten Bild oder im gewählten Eingabeordner. Mit jeder neuen Eingabe passt sich das Ziel an. **Auswählen …** wechselt zu einem eigenen Ordner und speichert direkt dort. Die App merkt sich den Ausgabemodus und den eigenen Ordner getrennt.

- **Restaurierung und Bearbeitung:** Microsoft Bringing Old Photos Back to Life, Fibo 2.0 Edit Turbo, FLUX.2 [klein] 4B, Qwen Image Edit 2509/2511 und FireRed Image Edit 1.1. Unterstützte Edit-Modelle können ein separat drehbares zweites Bild nutzen.
- **Kolorierung:** DDColor ModelScope, Paper, Artistic und Tiny sowie DeOldify Stable und Artistic. Die Kolorierung läuft auf der CPU. DDColor Paper ist ein optionaler Download.
- **Hochskalieren:** UltraSharp V2 Lite ist die Vorgabe für Restaurierung und Hochskalierung. Zur Auswahl stehen auch Lanczos, Nomos2 HQ MoSR, Real-ESRGAN und FaceUpDAT für Porträts.
- **Export:** PNG, JPEG mit Qualität 95 und 4:4:4 sowie TIFF mit LZW-Kompression. JPEG und TIFF übernehmen geeignete Metadaten. PNG speichert bei ComfyUI-Verarbeitung den Workflow.

## Quellcode und Builds

Der Quellcode enthält die Anwendung, Downloadlisten und ComfyUI-Adapter. Die Builds und Tests stehen unter [GitHub Actions](https://github.com/muelli1975/RestoRenate/actions). Das portable Windows-Paket enthält den Starter, die Python-Umgebung und die Exportwerkzeuge.

## Lizenz

RestoRenates eigener Code steht unter der [MIT-Lizenz](LICENSE). Die Lizenzen für Fremdkomponenten und Modelle stehen in [THIRD_PARTY.txt](THIRD_PARTY.txt).
