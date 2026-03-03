from __future__ import annotations

import logging
from typing import Literal

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


DeviceLiteral = Literal["cpu", "cuda"]


class WhisperTranscriber:
    """Wrapper around faster-whisper with device auto-selection."""

    def __init__(self, model_name: str = "small.en", device: str = "auto") -> None:
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self._compute_type = "float16" if self.device == "cuda" else "int8"
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self._compute_type,
        )
        logger.info(
            "Loaded Whisper model %s on %s (%s)",
            model_name,
            self.device,
            self._compute_type,
        )

    def transcribe(
        self, audio: np.ndarray, sample_rate: int, initial_prompt: str | None = None
    ) -> str:
        if audio.size == 0:
            return ""

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        segments, _info = self._model.transcribe(
            audio,
            language="en",
            beam_size=5,
            temperature=0.0,
            initial_prompt=initial_prompt,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        logger.info("Transcription complete (%d samples)", audio.size)
        return text

    @staticmethod
    def _resolve_device(device: str) -> DeviceLiteral:
        if device == "auto":
            try:
                import ctranslate2

                if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
                    return "cuda"
            except Exception:
                pass
            return "cpu"
        if device in ("mps", "cpu"):
            return "cpu"
        return device  # type: ignore[return-value]
