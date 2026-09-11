import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "melissa_tts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("melissa_tts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_voices_cover_required_langs():
    mod = load_module()
    required = {"zh-CN", "es-MX", "en-US", "ja-JP"}
    assert required.issubset(mod.VOICES.keys())
    assert all(voice.endswith("Neural") for voice in mod.VOICES.values())


def test_detect_lang_spanish():
    mod = load_module()
    assert mod.detect_lang("Hola Arturo, ¿cómo estás?") == "es-MX"


def test_detect_lang_chinese():
    mod = load_module()
    assert mod.detect_lang("你好世界") == "zh-CN"


def test_detect_lang_japanese():
    mod = load_module()
    assert mod.detect_lang("こんにちは") == "ja-JP"


def test_detect_lang_english_fallback():
    mod = load_module()
    assert mod.detect_lang("Hello Arturo") == "en-US"


def test_build_ssml_contains_voices():
    mod = load_module()
    ssml = mod.build_ssml({"es-MX": "Hola", "zh-CN": "你好"})
    assert "es-MX-DaliaNeural" in ssml
    assert "zh-CN-XiaoxiaoNeural" in ssml
    assert ssml.startswith("<speak")
