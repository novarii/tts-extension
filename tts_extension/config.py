import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG_PATH = Path("configs/config.yaml")


@dataclass(slots=True)
class AppConfig:
    """Application configuration with sensible defaults for local use."""

    shortcut: str = "<cmd>+<shift>+;"
    sample_rate: int = 16000
    channels: int = 1
    model_name: str = "tiny.en"
    device: str = "auto"
    max_recording_seconds: float = 120.0
    clipboard: bool = True
    auto_paste: bool = True
    type_characters: bool = False
    log_transcripts: bool = False
    log_path: Path = Path("logs/transcripts.log")

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
        if "log_path" in normalized and not isinstance(normalized["log_path"], Path):
            normalized["log_path"] = Path(normalized["log_path"])
        return normalized

    def ensure_log_dir(self) -> None:
        if self.log_transcripts:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
