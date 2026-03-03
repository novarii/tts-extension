import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG_PATH = Path("configs/config.yaml")


@dataclass(slots=True)
class AppConfig:
    """Application configuration with sensible defaults for local use."""

    shortcut: str | list[str] = "<fn>"
    hotkey_mode: str = "hold"
    trigger_mode: str = "hotkey"
    input_device: str | int | None = None
    audio_trigger_threshold: float = 0.01
    audio_trigger_start_seconds: float = 0.1
    audio_trigger_silence_seconds: float = 0.6
    sample_rate: int = 16000
    channels: int = 1
    model_name: str = "small.en"
    device: str = "auto"
    max_recording_seconds: float = 300.0
    clipboard: bool = True
    auto_paste: bool = True
    type_characters: bool = False
    duck_audio: bool = False
    duck_volume: int = 20
    log_transcripts: bool = False
    log_path: Path = Path("logs/transcripts.log")
    prompt_vocabulary: list[str] = field(default_factory=list)
    dictionary: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AppConfig":
        """Load configuration from YAML/TOML/JSON file or return defaults."""

        if config_path is None:
            if DEFAULT_CONFIG_PATH.exists():
                config_path = DEFAULT_CONFIG_PATH
        if config_path is None:
            return cls()

        if not config_path.exists():
            raise FileNotFoundError(f"Config path {config_path} does not exist")

        data = cls._load_raw_data(config_path)
        processed = cls._normalize_data(data)
        return cls(**processed)

    @staticmethod
    def _load_raw_data(path: Path) -> Dict[str, Any]:
        if path.suffix in {".yaml", ".yml"}:
            return yaml.safe_load(path.read_text()) or {}
        if path.suffix == ".json":
            return json.loads(path.read_text())
        if path.suffix in {".toml", ".tml"}:
            import tomllib  # Python 3.11+

            return tomllib.loads(path.read_text())
        raise ValueError(f"Unsupported config format: {path.suffix}")

    @staticmethod
    def _normalize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in data.items():
            normalized[key] = value
        if "shortcut" in normalized:
            shortcut_value = normalized["shortcut"]
            if isinstance(shortcut_value, list):
                normalized["shortcut"] = [
                    str(item).strip() for item in shortcut_value if str(item).strip()
                ]
            elif isinstance(shortcut_value, str):
                normalized["shortcut"] = shortcut_value.strip()
        if "trigger_mode" in normalized:
            normalized["trigger_mode"] = str(normalized["trigger_mode"]).strip().lower()
        if "input_device" in normalized:
            value = normalized["input_device"]
            if value is None:
                normalized["input_device"] = None
            elif isinstance(value, int):
                normalized["input_device"] = value
            else:
                text = str(value).strip()
                if text.isdigit():
                    normalized["input_device"] = int(text)
                else:
                    normalized["input_device"] = text or None
        if "log_path" in normalized and not isinstance(normalized["log_path"], Path):
            normalized["log_path"] = Path(normalized["log_path"])
        if "duck_volume" in normalized and not isinstance(normalized["duck_volume"], int):
            try:
                normalized["duck_volume"] = int(normalized["duck_volume"])
            except (TypeError, ValueError):
                pass
        for key in (
            "audio_trigger_threshold",
            "audio_trigger_start_seconds",
            "audio_trigger_silence_seconds",
        ):
            if key in normalized and not isinstance(normalized[key], float):
                try:
                    normalized[key] = float(normalized[key])
                except (TypeError, ValueError):
                    pass
        if "dictionary" in normalized:
            value = normalized["dictionary"]
            if not isinstance(value, dict):
                normalized["dictionary"] = {}
        return normalized

    def ensure_log_dir(self) -> None:
        if self.log_transcripts:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
