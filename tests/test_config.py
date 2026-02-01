from pathlib import Path

from tts_extension.config import AppConfig


def test_load_defaults(tmp_path: Path) -> None:
    config = AppConfig.load()
    assert config.shortcut == "<fn>"
    assert config.hotkey_mode == "hold"
    assert config.trigger_mode == "hotkey"
    assert config.input_device is None
    assert config.duck_audio is False
    assert config.duck_volume == 20
    assert config.audio_trigger_threshold == 0.01
    assert config.audio_trigger_start_seconds == 0.1
    assert config.audio_trigger_silence_seconds == 0.6
    assert config.model_name == "small.en"


def test_load_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "shortcut: '<cmd>+d'\ninput_device: External Mic\nmodel_name: base\nlog_path: logs/output.log\n",
        encoding="utf-8",
    )
    config = AppConfig.load(config_path)
    assert config.shortcut == "<cmd>+d"
    assert config.input_device == "External Mic"
    assert config.model_name == "base"
    assert config.log_path == Path("logs/output.log")


def test_load_yaml_input_device_index(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("input_device: 3\n", encoding="utf-8")
    config = AppConfig.load(config_path)
    assert config.input_device == 3


def test_load_yaml_shortcut_list(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "shortcut:\n  - '<fn>'\n  - '<num_lock>'\n", encoding="utf-8"
    )
    config = AppConfig.load(config_path)
    assert config.shortcut == ["<fn>", "<num_lock>"]
