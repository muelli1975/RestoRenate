"""Text editing commands and English prompt snippets."""
import tkinter as tk


# Imperative edits adapted from the Lightroom, Qwen, FLUX and Fibo examples.
# Each entry is (German label, English label, English edit instruction).
CATEGORIES = (
    ('Restaurierung und Retusche', 'Restoration and retouching', (
        ('Rote Augen entfernen', 'Remove red-eye',
         'Correct red-eye reflections and retain the natural iris color and shape.'),
        ('Staub und Kratzer entfernen', 'Remove dust and scratches',
         'Clean up dust spots and scratches while retaining fine photographic detail.'),
        ('Flecken und Knicke entfernen', 'Remove stains and creases',
         'Remove stains and crease marks and blend the repaired areas with the surrounding tones.'),
        ('Risse und Fehlstellen reparieren', 'Repair tears and missing areas',
         'Repair tears and fill missing areas using nearby intact details as a guide.'),
        ('Rauschen reduzieren', 'Reduce noise',
         'Reduce visible image noise while retaining natural texture and sharp edges.'),
        ('JPEG-Artefakte reduzieren', 'Reduce JPEG artifacts',
         'Clean up JPEG blocking and compression artifacts while retaining image detail.'),
        ('Unschärfe vorsichtig reduzieren', 'Reduce blur gently',
         'Gently reduce blur and recover clear edges while keeping the photo natural.'),
        ('Gesichtsdetails dezent wiederherstellen', 'Restore facial details gently',
         "Subtly restore facial detail and retain each person's features and expression."),
    )),
    ('Farbe und Ton', 'Color and tone', (
        ('Natürlich kolorieren', 'Colorize naturally',
         'Colorize the photograph with plausible skin tones and colors appropriate to the scene and period.'),
        ('Farbstich korrigieren', 'Correct color cast',
         'Correct the color cast and restore a neutral white balance with natural skin tones.'),
        ('Verblasste Farben auffrischen', 'Restore faded colors',
         'Restore faded colors with moderate saturation and natural tonal transitions.'),
        ('Belichtung ausgleichen', 'Balance exposure',
         'Balance exposure and recover detail in bright highlights and dark shadows.'),
        ('Kontrast sanft erhöhen', 'Increase contrast gently',
         'Add gentle contrast while retaining detail at both ends of the tonal range.'),
        ('In Schwarzweiß umwandeln', 'Convert to black and white',
         'Convert the photo to black and white with rich midtones and clear shadow detail.'),
        ('Warmes Sepia', 'Warm sepia',
         'Give the photograph a warm sepia tone with soft highlights and deep brown shadows.'),
    )),
    ('Licht und Stimmung', 'Light and mood', (
        ('Weiches Tageslicht', 'Soft daylight',
         'Relight the scene with soft, diffused daylight and gentle shadows.'),
        ('Weiches Studiolicht', 'Soft studio light',
         'Use a soft studio key light with subtle fill and natural skin tones.'),
        ('Goldene Stunde', 'Golden hour',
         'Relight the scene with warm golden-hour light and soft, elongated shadows.'),
        ('Low-Key-Beleuchtung', 'Low-key lighting',
         'Create low-key lighting with a directional key light and deep, detailed shadows.'),
        ('Kühle Abendstimmung', 'Cool evening light',
         'Give the scene cool evening light with subdued colors and soft shadows.'),
        ('Filmische Lichtstimmung', 'Cinematic lighting',
         'Use directional cinematic lighting with controlled highlights and soft falloff.'),
    )),
    ('Bildstil', 'Image style', (
        ('35-mm-Analogfilm', '35 mm film',
         'Give the photo the look of 35 mm color negative film with fine grain and soft contrast.'),
        ('Historisches Atelierporträt', 'Vintage studio portrait',
         'Give the image the look of a mid-century studio portrait with soft tonal transitions and fine film grain.'),
        ('Dokumentarische Fotografie', 'Documentary photography',
         'Use a candid documentary photography look with natural light, muted colors and visible texture.'),
        ('Magazinporträt', 'Editorial portrait',
         'Give the photo an editorial portrait look with restrained colors and carefully shaped light.'),
        ('Film Noir', 'Film noir',
         'Apply a film noir look with high-contrast monochrome tones and directional lighting.'),
        ('Aquarell', 'Watercolor',
         'Render the scene as a watercolor painting with translucent washes and visible paper texture.'),
        ('Ölgemälde', 'Oil painting',
         'Render the scene as an oil painting with visible brushwork and layered color.'),
        ('Bleistiftzeichnung', 'Pencil drawing',
         'Render the image as a graphite pencil drawing with fine lines and cross-hatched shading.'),
    )),
    ('Bildaufbau', 'Composition', (
        ('Enger Porträtausschnitt', 'Tight portrait crop',
         'Reframe as a close head-and-shoulders portrait with the eyes clearly visible.'),
        ('Mehr Umgebung zeigen', 'Show more surroundings',
         'Widen the framing to show more of the surroundings while keeping the main subject clearly visible.'),
        ('Motiv zentrieren', 'Center the subject',
         'Place the main subject in the center of the composition with balanced space around it.'),
        ('Drittelregel anwenden', 'Use the rule of thirds',
         'Recompose the image using the rule of thirds with the main subject near a grid intersection.'),
        ('Horizont geraderichten', 'Straighten the horizon',
         'Straighten the horizon while retaining the original subject proportions.'),
    )),
    ('Hintergrund', 'Background', (
        ('Hintergrund weichzeichnen', 'Soften the background',
         'Soften the background with shallow depth of field while keeping the main subject sharp.'),
        ('Neutraler Studiohintergrund', 'Neutral studio background',
         'Replace the background with a plain neutral studio backdrop while retaining the subject and pose.'),
        ('Störendes im Hintergrund entfernen', 'Remove background distractions',
         'Remove distracting objects from the background and reconstruct the surrounding scene naturally.'),
        ('Hintergrund abdunkeln', 'Darken the background',
         'Darken the background gently while retaining its details and keeping the subject well lit.'),
    )),
    ('Originaldetails erhalten', 'Preserve original details', (
        ('Gesichter und Ausdruck erhalten', 'Preserve faces and expressions',
         "Preserve each person's identity, facial features and expression."),
        ('Hautstruktur erhalten', 'Preserve skin texture',
         'Retain natural skin texture, pores and fine facial detail.'),
        ('Kleidung und Hintergrund erhalten', 'Preserve clothing and background',
         'Preserve the original clothing, accessories and background details.'),
        ('Ausschnitt und Perspektive erhalten', 'Preserve framing and perspective',
         'Keep the original framing, camera angle, perspective and subject proportions.'),
        ('Schrift und Beschriftungen erhalten', 'Preserve lettering',
         'Keep the original lettering legible with its existing spelling, placement and style.'),
        ('Filmkorn und Bildtextur erhalten', 'Preserve film grain and texture',
         'Retain the original film grain and photographic texture.'),
        ('Originalfarben erhalten', 'Preserve original colors',
         'Preserve the original color palette and tonal character of the photograph.'),
    )),
)

EDIT_ACTIONS = (
    ('Ausschneiden', 'Cut', '<<Cut>>'),
    ('Kopieren', 'Copy', '<<Copy>>'),
    ('Einfügen', 'Paste', '<<Paste>>'),
)


class PromptMenu:
    def __init__(self, field, snippets_button, colors, language):
        self.field = field
        english = language == 'en'
        menu = self.menu = tk.Menu(field, **colors)
        for german, label, event in EDIT_ACTIONS:
            menu.add_command(label=label if english else german,
                             command=lambda event=event: field.event_generate(event))
        menu.add_command(label='Select all' if english else 'Alles auswählen',
                         command=lambda: field.tag_add('sel', '1.0', 'end-1c'))
        blocks = tk.Menu(snippets_button, **colors)
        for german, label, entries in CATEGORIES:
            category = tk.Menu(blocks, **colors)
            for name_de, name_en, sentence in entries:
                category.add_command(label=name_en if english else name_de,
                                     command=lambda sentence=sentence: self.append(sentence))
            blocks.add_cascade(label=label if english else german, menu=category)
        snippets_button.configure(menu=blocks)
        field.bind('<Button-3>', self.popup)
        field.bind('<Shift-F10>', self.popup_at_cursor)

    def append(self, sentence):
        if self.field.cget('state') == 'disabled':
            return
        current = self.field.get('1.0', 'end-1c')
        separator = '\n' if current and not current.endswith('\n') else ''
        self.field.edit_separator()
        self.field.insert('end-1c', separator + sentence)
        self.field.edit_separator()
        self.field.tag_remove('sel', '1.0', 'end')
        self.field.mark_set('insert', 'end-1c')
        self.field.see('insert')
        self.field.focus_set()

    def popup(self, event):
        return self.show(event.x_root, event.y_root)

    def popup_at_cursor(self, event):
        x, y, _, height = self.field.bbox('insert') or (0, 0, 0, 0)
        return self.show(self.field.winfo_rootx() + x, self.field.winfo_rooty() + y + height)

    def show(self, x, y):
        editable = self.field.cget('state') != 'disabled'
        selected = bool(self.field.tag_ranges('sel'))
        self.menu.entryconfigure(0, state='normal' if editable and selected else 'disabled')
        self.menu.entryconfigure(1, state='normal' if selected else 'disabled')
        self.menu.entryconfigure(2, state='normal' if editable else 'disabled')
        self.field.focus_set()
        try:
            self.menu.tk_popup(x, y)
        finally:
            self.menu.grab_release()
        return 'break'
