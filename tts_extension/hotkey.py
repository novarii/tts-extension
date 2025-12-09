from __future__ import annotations

import logging
import threading
from typing import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Manage the global shortcut that toggles recording."""

    def __init__(self, shortcut: str, on_activate: Callable[[], None]) -> None:
        if not shortcut:
            raise ValueError("Shortcut cannot be empty")
        self.shortcut = shortcut
        self.on_activate = on_activate
        self._listener = keyboard.GlobalHotKeys({shortcut: self._handle})

    def start(self) -> None:
        logger.info("Listening for hotkey %s", self.shortcut)
        self._listener.start()

    def join(self) -> None:
        self._listener.join()

    def stop(self) -> None:
        self._listener.stop()

    def _handle(self) -> None:
        logger.debug("Hotkey %s triggered", self.shortcut)
        self.on_activate()


class PeriodicMonitor(threading.Thread):
    """Runs a callback on an interval until stopped."""

    def __init__(self, interval_seconds: float, callback: Callable[[], None]) -> None:
        super().__init__(daemon=True)
        self.interval = interval_seconds
        self.callback = callback
        self._stop_event = threading.Event()

    def run(self) -> None:
        while not self._stop_event.is_set():
            self.callback()
            self._stop_event.wait(self.interval)

    def stop(self) -> None:
        self._stop_event.set()
