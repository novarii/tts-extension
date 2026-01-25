from pathlib import Path

from tts_extension.config import AppConfig


def test_load_defaults(tmp_path: Path) -> None:
    config = AppConfig.load()
    assert config.shortcut == "<fn>"
    assert config.hotkey_mode == "hold"
    assert config.duck_audio is False
    assert config.duck_volume == 20
    assert config.model_name == "small.en"


def test_load_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "shortcut: '<cmd>+d'\nmodel_name: base\nlog_path: logs/output.log\n", encoding="utf-8"
    )
    config = AppConfig.load(config_path)
    assert config.shortcut == "<cmd>+d"
    assert config.model_name == "base"
    assert config.log_path == Path("logs/output.log")


def test_load_yaml_shortcut_list(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "shortcut:\n  - '<fn>'\n  - '<num_lock>'\n", encoding="utf-8"
    )
    config = AppConfig.load(config_path)
    assert config.shortcut == ["<fn>", "<num_lock>"]
