from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Push-to-talk audio recorder built on top of sounddevice."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._stream: Optional[sd.InputStream] = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None

    def start(self) -> None:
        if self._stream is not None:
            raise RuntimeError("Recorder already running")

        self._frames = []
        self._start_time = time.monotonic()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._on_audio,
        )
        self._stream.start()
        logger.debug("Audio recorder started at %s", self._start_time)

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.empty((0,), dtype=self.dtype)

        self._stream.stop()
        self._stream.close()
        self._stream = None

        with self._lock:
            frames = np.concatenate(self._frames) if self._frames else np.empty((0, self.channels), dtype=self.dtype)
            self._frames = []

        logger.debug("Audio recorder stopped, collected %s frames", len(frames))
        audio = self._to_mono(frames)
        return audio

    def is_running(self) -> bool:
        return self._stream is not None

    def duration(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def _on_audio(self, indata: np.ndarray, frames: int, _time, status) -> None:
        if status:
            logger.warning("Audio input status: %s", status)
        with self._lock:
            self._frames.append(indata.copy())

    def _to_mono(self, frames: np.ndarray) -> np.ndarray:
        if frames.size == 0:
            return frames.reshape(-1)
        if self.channels == 1:
            return frames.reshape(-1)
        return np.mean(frames, axis=1)
