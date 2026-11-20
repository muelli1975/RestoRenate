"""Bilingual descriptions keyed by model identity, shared with RestoRenate."""
import tkinter as tk

# Keep the two portable copies identical so descriptions also work offline.
DESCRIPTIONS = {
    "liveaction": (
        "Für Realfilm. Vergrößert um 2× und lässt Filmkorn weitgehend stehen.",
        "For live-action footage. Enlarges by 2× and largely preserves film grain."),
    "clearreality": (
        "Für relativ klare, körnungsarme Fotos trainiert. Gibt Gesichter, Haare und Naturmotive weich und natürlich wieder. Bei unscharfem Hintergrund können Artefakte entstehen.",
        "Trained for relatively clear photos with little grain. Gives faces, hair and nature scenes a soft, natural look. Out-of-focus backgrounds can show artifacts."),
    "purephoto": (
        "Für Fotos mit erkennbaren Details, besonders Haaren und Fell. Sehr kleine Vorlagen sind je nach Motiv weniger geeignet.",
        "For photos with discernible detail, especially hair and fur. Very small inputs may be less suitable, depending on the subject."),
    "nomos": (
        "Für Fotos mit mäßigen JPEG-Artefakten, Rauschen oder Unschärfe. Vergrößert um 4×.",
        "For photos with moderate JPEG artifacts, noise or blur. Enlarges by 4×."),
    "nomos_strong": (
        "Für stärker beeinträchtigte Fotos. Behandelt Kompression, Rauschen und Unschärfe beim Vergrößern um 4×.",
        "For more heavily degraded photos. Addresses compression, noise and blur while enlarging by 4×."),
    "anisd": (
        "Für digital produzierte Anime in SD-Auflösung, etwa von DVD oder aus dem Web. Vergrößert um 2×.",
        "For standard-definition digital anime, including DVD and web sources. Enlarges by 2×."),
    "nomos_uni": (
        "Für eine schnelle Vergrößerung um 2× bei mäßigen JPEG-Artefakten, leichtem Rauschen oder leichter Unschärfe.",
        "For fast 2× enlargement of images with moderate JPEG artifacts, mild noise or slight blur."),
    "lsdir_c3": (
        "Für JPEG-komprimiertes Bildmaterial. Das kompakte Modell reduziert Kompressionsartefakte beim Vergrößern um 4×.",
        "For JPEG-compressed material. This compact model reduces compression artifacts while enlarging by 4×."),
    "real_general": (
        "Kompaktes 4×-Allroundmodell aus Real-ESRGAN. Reduziert Rauschen stärker als die WDN-Variante.",
        "Compact general-purpose 4× model from Real-ESRGAN. Applies stronger denoising than the WDN variant."),
    "real_wdn": (
        "Die schwächer entrauschende Variante von RealESR General v3. Sinnvoll, wenn mehr Textur oder Körnung erhalten bleiben soll.",
        "The weaker-denoising variant of RealESR General v3. Useful when you want to retain more texture or grain."),
    "openproteus": (
        "Kompaktes 2×-Modell für Videomaterial. Geeignet, wenn eine moderate Vergrößerung ausreicht.",
        "Compact 2× model for video footage. Useful when moderate enlargement is enough."),
    "realbasicvsr": (
        "Für niedrig aufgelöste Videos mit realen Bildstörungen. Nutzt mehrere aufeinanderfolgende Videobilder, um Details zu rekonstruieren.",
        "For low-resolution video with real-world degradation. Uses consecutive frames to reconstruct detail."),
    "Nomos2 HQ MoSR 4×": (
        "Für saubere, detailreiche Fotos. Auf hochwertigen Eingaben trainiert, um vorhandene Details beim Vergrößern zu erhalten.",
        "For clean, detailed photos. Trained on high-quality inputs to preserve existing detail during enlargement."),
    "Nomos2 HQ DAT2 4×": (
        "DAT2-Variante für hochwertige Fotos mit wenigen Bildstörungen. Für feine Strukturen in bereits sauberen Vorlagen.",
        "DAT2 variant for high-quality photos with little degradation. Suited to fine structures in already clean inputs."),
    "4× FaceUpDAT": (
        "Für Gesichter in Fotos guter Ausgangsqualität. Auf dem FaceUp-Porträtdatensatz trainiert.",
        "For faces in photos with good input quality. Trained on the FaceUp portrait dataset."),
    "SeedVR2 3B INT8": (
        "Generative Restaurierung. Rekonstruiert auch Details, die in kleinen oder beschädigten Vorlagen nur noch angedeutet sind.",
        "Generative restoration. Reconstructs detail that is only faintly visible in small or degraded inputs."),
    "VOSR 2.0": (
        "Für anspruchsvolle Detailrekonstruktion aus niedrig aufgelösten Vorlagen. Feine Strukturen können neu entstehen.",
        "For detailed reconstruction from low-resolution inputs. Fine structures may be newly generated."),
    "Nomos8kDAT 4×": (
        "Für kleine oder komprimierte Fotos. Verwendet die DAT-Architektur zur Rekonstruktion fotografischer Details.",
        "For small or compressed photos. Uses the DAT architecture to reconstruct photographic detail."),
    "RealWebPhoto v4": (
        "Für niedrig aufgelöste Webfotos mit JPEG-Kompression und anderen Bildstörungen.",
        "For low-resolution web photos with JPEG compression and other degradation."),
    "Real-ESRGAN": (
        "Allrounder für reale Bildstörungen wie Unschärfe, Rauschen und Kompressionsartefakte.",
        "General-purpose restoration for real-world blur, noise and compression artifacts."),
    "NMKD Siax 4×": (
        "Allrounder zum Vergrößern fotografischer Vorlagen und Texturen um 4×.",
        "General-purpose 4× enlargement for photographic images and textures."),
    "Remacri 4×": (
        "Allroundmodell für Fotos, Illustrationen und Texturen. Vergrößert um 4×.",
        "General-purpose model for photos, illustrations and textures. Enlarges by 4×."),
    "UltraSharp 4×": (
        "Für eine betont scharfe Wiedergabe von Kanten und Texturen. Besonders bei bereits nachgeschärften Vorlagen auf Säume achten.",
        "For pronounced edges and textures. Watch for halos on inputs that have already been sharpened."),
    "UltraSharp V2": (
        "Für die detailbetonte Vergrößerung realistischer und gerenderter Bilder. Verwendet das große Modell der V2-Reihe.",
        "For detail-oriented enlargement of realistic and rendered images. Uses the full-sized V2 model."),
    "UltraSharp V2 Lite": (
        "Leichtere RealPLKSR-Variante von UltraSharp V2. Für detailbetonte Vergrößerung bei geringerem Rechenaufwand.",
        "Lighter RealPLKSR variant of UltraSharp V2. For detailed enlargement at lower computational cost."),
    "SwinIR-S 4×": (
        "Kleine SwinIR-Variante für die Vergrößerung um 4×. Rekonstruiert Bildstrukturen mit einem Transformer.",
        "Small SwinIR variant for 4× enlargement. Uses a transformer to reconstruct image structure."),
    "Real-ESRGAN Anime 4×": (
        "Für Anime und Zeichnungen. Das kompakte 6B-Modell ist auf Linien und Farbflächen abgestimmt.",
        "For anime and drawings. The compact 6B model is tuned for linework and areas of flat color."),
    "AnimeSharp 4×": (
        "Für scharf gezeichnete Konturen, Anime und Illustrationen. Vergrößert um 4×.",
        "For crisp linework, anime and illustrations. Enlarges by 4×."),
    "Lanczos": (
        "Klassische Skalierung ohne KI. Interpoliert vorhandene Bildpunkte und eignet sich auch für schnelle Größenanpassungen.",
        "Traditional scaling without AI. Interpolates existing pixels and is useful for quick resizing."),
}


class ModelHints:
    """Show a non-focusable hint beside the highlighted row or selected control."""
    def __init__(self, control, selected, language):
        self.control = control
        self.selected = selected
        self.language = language
        self.timer = self.window = self.key = None
        control.bind("<Enter>", lambda e: self.schedule(self.selected()), add="+")
        for event in ("<Leave>", "<ButtonPress>", "<Unmap>", "<Destroy>"):
            control.bind(event, self.hide, add="+")

    def schedule(self, key):
        if key == self.key:
            return
        self.hide()
        if key in DESCRIPTIONS:
            self.key = key
            self.timer = self.control.after(450, self.show)

    def hide(self, *_):
        self.key = None
        if self.timer is not None:
            self.control.after_cancel(self.timer)
            self.timer = None
        if self.window is not None:
            self.window.destroy()
            self.window = None

    def show(self):
        self.timer = None
        control = self.control
        window = self.window = tk.Toplevel(control)
        window.withdraw()
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        text = DESCRIPTIONS[self.key][int(self.language() == "en")]
        tk.Label(window, text=text, fg="#eee9df", bg="#25231f", padx=10, pady=7,
                 wraplength=325, justify="left").pack()
        window.update_idletasks()
        width, height = window.winfo_reqwidth(), window.winfo_reqheight()
        x = control.winfo_rootx() + control.winfo_width() + 8
        if x + width > control.winfo_screenwidth():
            x = max(0, control.winfo_rootx() - width - 8)
        y = min(control.winfo_pointery() + 18, control.winfo_screenheight() - height)
        window.geometry(f"+{x}+{max(0, y)}")
        window.deiconify()

    def bind_menu(self, menu):
        def active(_event):
            index = menu.index("active")
            key = menu.entrycget(index, "value") if index is not None and menu.type(index) == "radiobutton" else None
            self.schedule(key)
        menu.bind("<<MenuSelect>>", active, add="+")
        for event in ("<Unmap>", "<Leave>", "<ButtonRelease-1>", "<Escape>"):
            menu.bind(event, self.hide, add="+")

    def bind_combobox(self, keys):
        combo = self.control
        popup = combo.tk.call("ttk::combobox::PopdownWindow", str(combo))
        listing = str(popup) + ".f.l"

        def select(index):
            if not int(combo.tk.call("winfo", "ismapped", listing)):
                self.hide()
                return
            values = keys()
            self.schedule(values[int(index)] if str(index).isdigit() and int(index) < len(values) else None)

        def scrolled(y):
            combo.after_idle(lambda: select(combo.tk.call(listing, "nearest", int(y))))

        scroll_cmd = combo.register(scrolled)
        select_cmd = combo.register(select)
        hide_cmd = combo.register(self.hide)
        for event, script in (("<Motion>", f"{select_cmd} [{listing} nearest %y]"),
                              ("<MouseWheel>", f"{scroll_cmd} %y"),
                              ("<KeyRelease>", f"{select_cmd} [{listing} index active]"),
                              ("<Map>", f"{select_cmd} [{listing} curselection]"),
                              ("<Unmap>", hide_cmd), ("<Leave>", hide_cmd)):
            combo.tk.call("bind", listing, event, "+" + script)
