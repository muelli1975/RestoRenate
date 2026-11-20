# Windows packaging

Build the portable Windows GUI with PyInstaller in onedir, windowed mode, following the existing build workflow. The application EXE owns the GUI window. A separate Python runtime may be used for processing or installing optional dependencies. Run the packaged EXE from a fresh extraction and verify that it opens and closes cleanly. Any change to the Windows packaging system or introduction of a separate GUI launcher requires Christoph's explicit approval before implementation. This applies to test builds and releases.
