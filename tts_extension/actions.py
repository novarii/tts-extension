from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyperclip
from pynput import keyboard

logger = logging.getLogger(__name__)


class OutputActions:
    """Handles how transcripts reach the focused text field or logs."""

    def __init__(
        self,
        use_clipboard: bool = True,
        auto_paste: bool = True,
        type_characters: bool = False,
        log_transcripts: bool = False,
        log_path: Optional[Path] = None,
    ) -> None:
        self.use_clipboard = use_clipboard
        self.auto_paste = auto_paste
        self.type_characters = type_characters
        self.log_transcripts = log_transcripts
        self.log_path = log_path
        self._keyboard = keyboard.Controller()

    def deliver(self, text: str) -> None:
        if not text:
            logger.info("No transcription text to deliver")
            return

        if self.log_transcripts and self.log_path:
            self._write_log(text)

        if self.use_clipboard:
            pyperclip.copy(text)
            logger.debug("Copied transcript to clipboard")
            if self.auto_paste:
                self._send_paste()
        elif self.type_characters:
            self._type_text(text)
        else:
            logger.info("Transcript: %s", text)

    def _write_log(self, text: str) -> None:
        assert self.log_path is not None
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().isoformat()
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] {text}\n")
        logger.debug("Appended transcript to %s", self.log_path)

    def _type_text(self, text: str) -> None:
        for char in text:
            self._keyboard.press(char)
            self._keyboard.release(char)

    def _send_paste(self) -> None:
        with self._keyboard.pressed(keyboard.Key.cmd):
            self._keyboard.press("v")
            self._keyboard.release("v")
        logger.info("Pasted transcript into active field")
