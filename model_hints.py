"""Bilingual descriptions for the upscaler menu."""
import tkinter as tk

from methods import CLEARREALITY, MULTIJPG, PUREPHOTO

# Match Scalerina’s wording for models available in both applications.
DESCRIPTIONS = {
    # https://openmodeldb.info/models/4x-ClearRealityV1
    CLEARREALITY: (
        "Für relativ klare Aufnahmen mit wenig Korn, besonders Gesichter, Haare und Naturmotive. Ziel ist ein weiches, natürliches Ergebnis. Bei geringer Schärfentiefe oder Bokeh können Artefakte entstehen.",
        "For fairly clear shots with little grain, especially faces, hair and nature scenes. Aims for a soft, natural look. Shallow depth of field or bokeh can produce artifacts."),
    # https://openmodeldb.info/models/4x-PurePhoto-span
    PUREPHOTO: (
        "Für Amateur- und Profifotos, besonders für Haare und Tierfell. Auch kleine Fotos können gelingen. Als Richtwert nennt der Autor je nach Motiv etwa 300 Pixel an der kürzeren Seite.",
        "For amateur and professional photos, especially hair and fur. Small photos can also work. The author suggests roughly 300 pixels on the shorter side, depending on the subject."),
    # https://openmodeldb.info/models/4x-NomosUni-span-multijpg
    MULTIJPG: (
        "Schneller 4×-Allrounder für JPEG-komprimiertes und bereits skaliertes Bildmaterial. Trainiert mit JPEG-Qualitäten bis hinunter zu 40 und mehreren Verfahren zum Verkleinern und Vergrößern.",
        "Fast general-purpose 4× upscaler for JPEG-compressed and previously resized images. Trained with JPEG quality down to 40 and several downsampling and upsampling methods."),
    # https://openmodeldb.info/models/4x-Nomos2-hq-mosr
    "Nomos2 HQ MoSR 4×": (
        "Für saubere Fotos, trainiert auf Vorlagen ohne künstliche Qualitätsverluste. Bei sichtbaren JPEG-Artefakten empfiehlt der Autor, sie vor dem Vergrößern zu reduzieren.",
        "For clean photos, trained on inputs without added degradation. For visible JPEG artifacts, the author recommends reducing them before enlargement."),
    # https://openmodeldb.info/models/4x-FaceUpDAT
    "4× FaceUpDAT": (
        "Spezialisiert auf Gesichter in Fotos guter Ausgangsqualität. Auf dem FaceUp-Datensatz trainiert.",
        "Specializes in faces in good-quality photos. Trained on the FaceUp dataset."),
    # https://huggingface.co/ByteDance-Seed/SeedVR2-3B
    "SeedVR2 3B INT8": (
        "Generatives Modell zur Restaurierung von Bildern und Videos in einem Diffusionsschritt. Hier kommt die quantisierte 3B-Variante zum Einsatz.",
        "Generative model for restoring images and video in a single diffusion step. This app uses the quantized 3B variant."),
    # https://github.com/cswry/VOSR
    "VOSR 2.0": (
        "Generatives Modell für Einzelbilder. Rekonstruiert feine Strukturen in einem Schritt allein aus der Bildvorlage.",
        "Generative model for still images. Reconstructs fine structures in one step using the image alone."),
    # https://openmodeldb.info/models/4x-Nomos8kDAT
    "Nomos8kDAT 4×": (
        "Für die vierfache Vergrößerung von Fotos. Beim Training wurden JPEG-Kompression, Unschärfe und Größenänderungen kombiniert.",
        "For 4× photo enlargement. Training combined JPEG compression, blur and resizing."),
    # https://openmodeldb.info/models/4x-RealWebPhoto-v4-dat2
    "RealWebPhoto v4": (
        "Für Webfotos, auch nach mehrfachem Verkleinern und erneuter JPEG- oder WebP-Kompression. Berücksichtigt außerdem Rauschen und optische Unschärfe.",
        "For web photos, including repeated resizing and JPEG or WebP recompression. Also addresses noise and lens blur."),
    # https://github.com/xinntao/Real-ESRGAN
    "Real-ESRGAN": (
        "Allrounder für die Restaurierung und Vergrößerung realer Aufnahmen. Auf synthetisch erzeugten Bildstörungen trainiert, darunter Unschärfe, Rauschen und Kompression.",
        "General-purpose restoration and enlargement for real-world imagery. Trained with synthetic degradation, including blur, noise and compression."),
    # https://openmodeldb.info/models/4x-NMKD-Siax-CX
    "NMKD Siax 4×": (
        "Allrounder für saubere oder leicht komprimierte Vorlagen. Für JPEG nennt der Autor eine Qualitätseinstellung ab etwa 75.",
        "General-purpose upscaler for clean or lightly compressed inputs. For JPEG, the author suggests a quality setting of about 75 or higher."),
    # https://openmodeldb.info/models/4x-Remacri
    "Remacri 4×": (
        "Kombiniert mehrere Modelle, darunter Siax und Superscale. Ziel sind mehr Details und weniger Glättung, besonders bei Hautstrukturen.",
        "Blends several models, including Siax and Superscale. Aims for more detail and less smoothing, particularly on skin."),
    # https://openmodeldb.info/models/4x-UltraSharp
    "UltraSharp 4×": (
        "Erzeugt ausgeprägte Details und Texturen. Hauptsächlich auf JPEG-Kompression trainiert, auch für stark komprimierte Vorlagen geeignet.",
        "Produces pronounced detail and texture. Trained mainly on JPEG compression and can also handle heavily compressed inputs."),
    # https://openmodeldb.info/models/4x-UltraSharpV2
    "UltraSharp V2": (
        "Für realistische Motive, Anime, Cartoons, Illustrationen und Kunstwerke. Die Vollversion verwendet DAT2.",
        "For realistic imagery, anime, cartoons, illustrations and artwork. The full model uses DAT2."),
    # https://openmodeldb.info/models/4x-UltraSharpV2
    "UltraSharp V2 Lite": (
        "Lite-Variante der V2-Reihe für realistische Motive, Anime, Cartoons und Illustrationen. Verwendet die kompaktere RealPLKSR-Architektur.",
        "Lite variant of the V2 family for realistic imagery, anime, cartoons and illustrations. Uses the smaller RealPLKSR architecture."),
    # https://github.com/JingyunLiang/SwinIR
    "SwinIR-S 4×": (
        "Leichte SwinIR-Variante für klassische 4×-Vergrößerung. Auf DIV2K trainiert, für bikubisch verkleinerte Vorlagen.",
        "Lightweight SwinIR variant for classical 4× enlargement. Trained on DIV2K for inputs reduced with bicubic downsampling."),
    # https://github.com/xinntao/Real-ESRGAN/blob/master/docs/model_zoo.md
    "Real-ESRGAN Anime 4×": (
        "Für Anime-Illustrationen optimierte 4×-Variante. Verwendet ein kleineres Netz mit sechs Modellblöcken.",
        "A 4× variant optimized for anime illustrations. Uses a smaller network with six model blocks."),
    # https://openmodeldb.info/models/4x-AnimeSharp
    "AnimeSharp 4×": (
        "Für Anime, auch für Schrift einsetzbar. Kombiniert UltraSharp und TextSharp. Laut Autor liegen die Stärken vor allem bei Anime.",
        "For anime, with support for text as well. Blends UltraSharp and TextSharp. The author reports better results on anime than on text."),
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
