from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

import numpy as np
import torch
import whisper

logger = logging.getLogger(__name__)


DeviceLiteral = Literal["cpu", "cuda", "mps"]


class WhisperTranscriber:
    """Wrapper around OpenAI Whisper with device auto-selection."""

    def __init__(self, model_name: str = "tiny.en", device: str = "auto") -> None:
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self._model = self._load_model()
        logger.info("Loaded Whisper model %s on %s", model_name, self.device)

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        if audio.size == 0:
            return ""

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        result = self._model.transcribe(
            audio,
            language="en",
            fp16=self.device == "cuda",
            temperature=0.0,
        )
        text = (result.get("text") or "").strip()
        logger.info("Transcription complete (%d samples)", audio.size)
        return text

    @staticmethod
    def _resolve_device(device: str) -> DeviceLiteral:
        if device != "auto":
            return device  # type: ignore[return-value]
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"  # type: ignore[return-value]
        return "cpu"

    @lru_cache(maxsize=1)
    def _load_model(self):
        return whisper.load_model(self.model_name, device=self.device)
