from __future__ import annotations

import logging
import threading

import numpy as np

from .actions import OutputActions
from .audio import AudioRecorder, SystemAudioDucker, SystemSoundPlayer
from .config import AppConfig
from .transcription import WhisperTranscriber

logger = logging.getLogger(__name__)


class DictationWorkflow:
    """Coordinates recording and transcription when the hotkey triggers."""

    def __init__(
        self,
        config: AppConfig,
        recorder: AudioRecorder,
        transcriber: WhisperTranscriber,
        actions: OutputActions,
        sound_player: SystemSoundPlayer | None = None,
        audio_ducker: SystemAudioDucker | None = None,
    ) -> None:
        self.config = config
        self.recorder = recorder
        self.transcriber = transcriber
        self.actions = actions
        self.sound_player = sound_player
        self.audio_ducker = audio_ducker
        self._lock = threading.Lock()
        self._is_recording = False

    def start_recording(self) -> None:
        with self._lock:
            if self._is_recording:
                return
            self._start()

    def stop_recording(self) -> None:
        with self._lock:
            if not self._is_recording:
                return
            self._complete()

    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording

    def toggle_recording(self) -> None:
        with self._lock:
            if not self._is_recording:
                self._start()
            else:
                self._complete()

    def _start(self) -> None:
        logger.info("Recording started — speak now")
        self.recorder.start()
        if self.audio_ducker:
            self.audio_ducker.duck(self.config.duck_volume)
        if self.sound_player:
            self.sound_player.play_toggle()
        self._is_recording = True

    def _complete(self) -> None:
        logger.info("Recording stopped — transcribing...")
        audio = self.recorder.stop()
        self._is_recording = False
        if self.audio_ducker:
            self.audio_ducker.restore()
        if audio.size == 0:
            logger.warning("No audio captured; skipping transcription")
            return
        if self.sound_player:
            self.sound_player.play_transcribe()
        text = self.transcriber.transcribe(audio, self.config.sample_rate)
        self.actions.deliver(text)

    def stop_if_needed(self) -> None:
        if not self._is_recording:
            return
        duration = self.recorder.duration()
        if duration > self.config.max_recording_seconds:
            logger.info("Recording reached maximum duration, stopping automatically")
            self._complete()
