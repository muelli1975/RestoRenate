# Windows packaging

Build the portable Windows GUI with PyInstaller in onedir, windowed mode, following the existing build workflow. The application EXE owns the GUI window. A separate Python runtime may be used for processing or installing optional dependencies. Run the packaged EXE from a fresh extraction and verify that it opens and closes cleanly. Any change to the Windows packaging system or introduction of a separate GUI launcher requires Christoph's explicit approval before implementation. This applies to test builds and releases.

# Interface conventions

Use StereoFine as the reference for equivalent controls and their German and English names. For signed adjustments, match its centered exposure slider, numeric field and double-click reset. In RestoRenate use Shift + mouse wheel over the track or handle for every image editing slider. Check the dialog, the controls guide and both portable guides together when changing a control.

## Agreed decisions and application startup

Treat Christoph's explicit decisions as requirements for implementation, test builds and releases. Preserve their intent when choosing tools or languages. Before editing, check the relevant agreements. Before building, check the actual diff, entry point and build command against them. If a concrete technical obstacle requires a departure, explain the conflict and obtain Christoph's agreement before implementing it.

Follow the Windows packaging instructions above and the existing `scripts/freeze_windows.py` workflow. Introducing an additional application starter, wrapper or bootstrap process requires Christoph's prior agreement in any language.
