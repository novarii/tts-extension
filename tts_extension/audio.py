from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow import DictationWorkflow

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
        device: str | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.device = device
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
            device=self.device,
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


class SystemAudioDucker:
    """Reduce system output volume while recording on macOS."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = (
            enabled
            and sys.platform == "darwin"
            and shutil.which("osascript") is not None
        )
        self._previous_volume: int | None = None
        if not self.enabled:
            logger.debug("System audio ducking disabled or unsupported platform")

    def duck(self, target_volume: int) -> None:
        if not self.enabled or self._previous_volume is not None:
            return
        current = self._get_volume()
        if current is None:
            return
        self._previous_volume = current
        self._set_volume(self._clamp(target_volume))

    def restore(self) -> None:
        if not self.enabled or self._previous_volume is None:
            return
        self._set_volume(self._previous_volume)
        self._previous_volume = None

    @staticmethod
    def _clamp(volume: int) -> int:
        return max(0, min(100, volume))

    def _get_volume(self) -> int | None:
        try:
            result = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            logger.debug("Failed to read system volume", exc_info=True)
            return None
        if result.returncode != 0:
            logger.debug("osascript returned non-zero while reading volume")
            return None
        output = (result.stdout or "").strip()
        try:
            return int(output)
        except ValueError:
            logger.debug("Unexpected volume output: %s", output)
            return None

    def _set_volume(self, volume: int) -> None:
        try:
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {volume}"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.debug("Failed to set system volume", exc_info=True)


class AudioTriggerMonitor(threading.Thread):
    """Monitor input volume and start/stop dictation based on audio activity."""

    def __init__(
        self,
        workflow: "DictationWorkflow",
        sample_rate: int,
        channels: int,
        device: str | None,
        threshold: float,
        start_seconds: float,
        silence_seconds: float,
    ) -> None:
        super().__init__(daemon=True)
        self.workflow = workflow
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.threshold = threshold
        self.start_seconds = start_seconds
        self.silence_seconds = silence_seconds
        self._start_grace_seconds = min(0.2, silence_seconds)
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._last_signal_time: float | None = None
        self._signal_start_time: float | None = None

    def start(self) -> None:
        super().start()
        self._ready.wait()
        if self._error is not None:
            raise self._error

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=self.device,
                callback=self._on_audio,
            )
            self._stream.start()
        except Exception as exc:
            self._error = exc
            self._ready.set()
            return
        self._ready.set()
        while not self._stop_event.is_set():
            now = time.monotonic()
            with self._lock:
                last_signal_time = self._last_signal_time
                signal_start_time = self._signal_start_time
            signal_recent = (
                last_signal_time is not None
                and now - last_signal_time <= self.silence_seconds
            )
            signal_recent_for_start = (
                last_signal_time is not None
                and now - last_signal_time <= self._start_grace_seconds
            )
            if (
                signal_recent_for_start
                and signal_start_time is not None
                and now - signal_start_time >= self.start_seconds
                and not self.workflow.is_recording()
            ):
                self.workflow.start_recording()
            if (
                not signal_recent
                and self.workflow.is_recording()
                and last_signal_time is not None
                and now - last_signal_time >= self.silence_seconds
            ):
                self.workflow.stop_recording()
                self._clear_signal_state()
            self._stop_event.wait(0.05)
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _on_audio(self, indata: np.ndarray, frames: int, _time, status) -> None:
        if status:
            logger.debug("Audio trigger status: %s", status)
        rms = float(np.sqrt(np.mean(np.square(indata, dtype=np.float64))))
        now = time.monotonic()
        with self._lock:
            if rms >= self.threshold:
                if self._signal_start_time is None:
                    self._signal_start_time = now
                self._last_signal_time = now
            else:
                if (
                    self._last_signal_time is not None
                    and now - self._last_signal_time >= self.silence_seconds
                ):
                    self._signal_start_time = None

    def _clear_signal_state(self) -> None:
        with self._lock:
            self._last_signal_time = None
            self._signal_start_time = None
