from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path
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


class SystemSoundPlayer:
    """Lightweight player for macOS system alert sounds."""

    _SOUND_DIR = Path("/System/Library/Sounds")

    def __init__(
        self,
        toggle_sound: str = "Morse",
        transcribe_sound: str = "Morse",
        enabled: bool = True,
    ) -> None:
        self.toggle_sound = toggle_sound
        self.transcribe_sound = transcribe_sound
        self.enabled = (
            enabled
            and shutil.which("afplay") is not None
            and self._SOUND_DIR.exists()
        )
        if not self.enabled:
            logger.debug("System sounds disabled (afplay missing or unsupported platform)")

    def play_toggle(self) -> None:
        self._play(self.toggle_sound)

    def play_transcribe(self) -> None:
        self._play(self.transcribe_sound)

    def _play(self, sound_name: str) -> None:
        if not self.enabled:
            return
        path = self._SOUND_DIR / f"{sound_name}.aiff"
        if not path.exists():
            logger.debug("System sound file %s not found", path)
            return
        threading.Thread(target=self._run_player, args=(path,), daemon=True).start()

    @staticmethod
    def _run_player(path: Path) -> None:
        try:
            subprocess.run(
                ["afplay", str(path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.debug("Failed to play system sound %s", path, exc_info=True)
