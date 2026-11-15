"""Check the fixed two-row reference panel and reference crop lifecycle."""
from crop import CropRegion


def check_reference_controls(gui, image_path):
    window = gui.window
    row = gui.second_row
    remove = gui.remove_second_button

    def bounds(widget):
        return widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_width(), widget.winfo_height()

    window.update()
    controls = (row, gui.second_preview, gui.second_name, gui.second_button,
                remove, gui.second_crop_button, gui.second_rotate_button)
    initial = [bounds(widget) for widget in controls]
    assert row.winfo_viewable() and remove.instate(['disabled'])
    assert gui.second_crop_button.instate(['disabled'])
    assert remove.cget('text') in ('Entfernen', 'Remove')
    for _ in range(2):
        gui.set_second_image(image_path)
        window.update()
        assert [bounds(widget) for widget in controls] == initial
        assert not remove.instate(['disabled'])
        assert not gui.second_crop_button.instate(['disabled'])
        from imaging import photo_size
        width, height = photo_size(image_path)
        crop = CropRegion((width, height), (0, 0, width // 2, height))
        gui.set_second_image(image_path, crop=crop)
        gui.rotate_second_image(1)
        assert gui.second_crop == crop.rotated(1)
        gui.set_second_image(image_path)
        assert gui.second_crop is None
        remove.invoke()
        window.update()
        assert gui.second_image is None and gui.second_rotation == 0
        assert remove.instate(['disabled'])
        assert [bounds(widget) for widget in controls] == initial
