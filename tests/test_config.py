from pathlib import Path

from tts_extension.config import AppConfig


def test_load_defaults(tmp_path: Path) -> None:
    config = AppConfig.load()
    assert config.shortcut == "<cmd>+<shift>+;"
    assert config.model_name == "tiny.en"


def test_load_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "shortcut: '<cmd>+d'\nmodel_name: base\nlog_path: logs/output.log\n", encoding="utf-8"
    )
    config = AppConfig.load(config_path)
    assert config.shortcut == "<cmd>+d"
    assert config.model_name == "base"
    assert config.log_path == Path("logs/output.log")
