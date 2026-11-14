"""Check the reference controls before loading, after loading and after clearing."""
from PIL import ImageTk

from theme import DANGER_TEXT, DISABLED


def check_reference_controls(gui, image_path):
    window = gui.window
    remove = gui.remove_second_button

    def bounds():
        window.update()
        return remove.winfo_rootx(), remove.winfo_rooty(), remove.winfo_width(), remove.winfo_height()

    initial_bounds = bounds()
    assert remove.winfo_viewable() and remove.instate(['disabled']), (
        gui.current_method, gui.second_row.winfo_ismapped(), remove.winfo_ismapped(), initial_bounds, remove.state(),
    )
    x, y, width, _ = initial_bounds
    row = gui.second_row
    assert row.winfo_rootx() + row.winfo_width() - x - width == 7
    assert y - row.winfo_rooty() == 5
    assert remove.cget('compound') == 'image'

    for icon, expected in zip(gui.reference_remove_icons, (DANGER_TEXT, DISABLED)):
        with ImageTk.getimage(icon) as image:
            width, height = image.size
            rgb = tuple(bytes.fromhex(expected[1:]))
            opaque = {(x, y) for y in range(height) for x in range(width)
                      if image.getpixel((x, y)) == (*rgb, 255)}
            assert opaque, expected
            assert (width // 2, height // 2) in opaque, opaque
            assert sum(y == height // 2 for _, y in opaque) >= 3, opaque
            left, top = min(x for x, _ in opaque), min(y for _, y in opaque)
            right, bottom = max(x for x, _ in opaque), max(y for _, y in opaque)
            assert left + right == width - 1 and top + bottom == height - 1, opaque

    for _ in range(2):
        gui.set_second_image(image_path)
        assert bounds() == initial_bounds
        assert remove.winfo_viewable() and not remove.instate(['disabled'])
        remove.invoke()
        assert gui.second_image is None and gui.second_rotation == 0
        assert bounds() == initial_bounds and remove.instate(['disabled'])
