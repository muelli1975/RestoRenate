import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "_internal"))

import app
import bootstrap

settings = root / "settings.json"
legacy = root / "settings" / "settings.json"
assert app.ROOT == bootstrap.ROOT == root
assert app.SETTINGS == settings
assert not legacy.parent.exists() and not settings.exists()
legacy.parent.mkdir()
legacy.write_text('{"language":"de"}', encoding="utf-8")
assert app.read_settings() == {}
with patch.object(bootstrap.subprocess, "Popen", side_effect=OSError("smoke test")), \
     patch.object(bootstrap, "configure_language") as language, \
     patch("tkinter.messagebox.showerror"):
    assert bootstrap.launch() == 1
    language.assert_called_once_with(None)

def value(data):
    return SimpleNamespace(get=lambda: data)

stub = SimpleNamespace(
    remember_prompt=lambda: None, remember_scaling=lambda: None,
    remember_compute_processing=lambda: None, microsoft_colorization_settings=lambda: {},
    input_folder="", output=value(""), custom_output=value(""), output_in_source=value(True),
    output_format=value("PNG"), seed="", compute=value("CPU"), current_method="test",
    draft="", custom={}, language="en", processing_presets={"sample": {"method": "test"}},
    processing_by_compute={}, variant_count=1, scaling={}, scratches=value(False), faces=value(False),
    look_controls=SimpleNamespace(look=lambda: SimpleNamespace(strength=100)),
)
assert app.Application.save_settings(stub) is not False
saved = app.read_settings()
assert saved["language"] == "en" and saved["processing_presets"] == stub.processing_presets
assert json.loads(settings.read_text(encoding="utf-8")) == saved
assert legacy.read_text(encoding="utf-8") == '{"language":"de"}'
assert not settings.with_suffix(".tmp").exists()
with patch.object(bootstrap.subprocess, "Popen", side_effect=OSError("smoke test")), \
     patch.object(bootstrap, "configure_language") as language, \
     patch("tkinter.messagebox.showerror"):
    assert bootstrap.launch() == 1
    language.assert_called_once_with("en")
print(f"Read, write and launcher language verified with Python {sys.version.split()[0]}")
