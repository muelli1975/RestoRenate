"""Check the reference panel layout and the local remove icon."""
from PIL import ImageTk

from theme import SECONDARY_BG


def check_reference_controls(gui, image_path):
    window = gui.window
    row = gui.second_row
    remove = gui.remove_second_button

    def bounds(widget):
        return widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_width(), widget.winfo_height()

    window.update()
    initial = [bounds(widget) for widget in (row, gui.second_preview, gui.second_name)]
    assert row.winfo_viewable() and not remove.winfo_ismapped()
    assert str(remove.cget('compound')) == 'image'
    with ImageTk.getimage(gui.reference_remove_icon) as icon:
        assert icon.size == (22, 22)
        dark = tuple(bytes.fromhex(SECONDARY_BG[1:]))
        assert icon.getpixel((11, 11)) == (*dark, 255)
        assert icon.getpixel((0, 0))[3] == 0

    for _ in range(2):
        gui.set_second_image(image_path)
        window.update()
        assert [bounds(widget) for widget in (row, gui.second_preview, gui.second_name)] == initial
        x, y, width, _ = bounds(remove)
        assert row.winfo_rootx() + row.winfo_width() - x - width == 7
        assert y - row.winfo_rooty() == 5
        assert remove.winfo_viewable() and not remove.instate(['disabled'])
        remove.invoke()
        window.update()
        assert gui.second_image is None and gui.second_rotation == 0
        assert not remove.winfo_ismapped()
        assert [bounds(widget) for widget in (row, gui.second_preview, gui.second_name)] == initial
