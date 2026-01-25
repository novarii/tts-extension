from __future__ import annotations

import logging
import re
import sys
import threading
from typing import Callable, Literal, TypedDict

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Manage the global shortcut that toggles or holds recording."""

    def __init__(
        self,
        shortcut: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None] | None = None,
        mode: str = "toggle",
    ) -> None:
        if not shortcut:
            raise ValueError("Shortcut cannot be empty")
        if mode not in {"toggle", "hold"}:
            raise ValueError("Hotkey mode must be 'toggle' or 'hold'")
        if mode == "hold" and on_release is None:
            raise ValueError("Hold mode requires an on_release callback")
        self.shortcut = shortcut
        self.on_press = on_press
        self.on_release = on_release
        self.mode = mode
        self._fn_monitor: _FnKeyMonitor | None = None
        self._keycode_monitor: _KeyCodeMonitor | None = None
        special = self._parse_special_shortcut(shortcut)
        if special is not None:
            if sys.platform != "darwin":
                raise ValueError("Special hotkeys are only supported on macOS.")
            if special["kind"] == "fn":
                self._fn_monitor = _FnKeyMonitor(
                    self._handle_press, self._handle_release, mode
                )
            else:
                self._keycode_monitor = _KeyCodeMonitor(
                    special["key_code"],
                    self._handle_press,
                    self._handle_release,
                    mode,
                    special["label"],
                )
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._combo = {
            self._listener.canonical(key) for key in self._parse_shortcut(shortcut)
        }
        if not self._combo:
            raise ValueError("Shortcut cannot be empty")
        self._pressed: set = set()
        self._active = False

    def start(self) -> None:
        logger.info("Listening for hotkey %s", self.shortcut)
        if self._fn_monitor is not None:
            self._fn_monitor.start()
            return
        if self._keycode_monitor is not None:
            self._keycode_monitor.start()
            return
        self._listener.start()

    def join(self) -> None:
        if self._fn_monitor is not None:
            self._fn_monitor.join()
            return
        if self._keycode_monitor is not None:
            self._keycode_monitor.join()
            return
        self._listener.join()

    def stop(self) -> None:
        if self._fn_monitor is not None:
            self._fn_monitor.stop()
            return
        if self._keycode_monitor is not None:
            self._keycode_monitor.stop()
            return
        self._listener.stop()

    def _handle_press(self) -> None:
        logger.debug("Hotkey %s pressed", self.shortcut)
        self.on_press()

    def _handle_release(self) -> None:
        if self.on_release is None:
            return
        logger.debug("Hotkey %s released", self.shortcut)
        self.on_release()

    def _on_press(self, key, injected: bool | None = None) -> None:
        if injected:
            return
        canonical = self._listener.canonical(key)
        if canonical not in self._combo:
            return
        self._pressed.add(canonical)
        if not self._active and self._combo.issubset(self._pressed):
            self._active = True
            self._handle_press()

    def _on_release(self, key, injected: bool | None = None) -> None:
        if injected:
            return
        canonical = self._listener.canonical(key)
        if canonical not in self._combo:
            return
        self._pressed.discard(canonical)
        if self._active:
            self._active = False
            if self.mode == "hold":
                self._handle_release()

    @staticmethod
    def _parse_shortcut(shortcut: str) -> set:
        return set(keyboard.HotKey.parse(shortcut))

    @staticmethod
    def _parse_special_shortcut(shortcut: str) -> "SpecialShortcut | None":
        normalized = shortcut.strip().lower()
        if normalized in {"<fn>", "fn", "<function>"}:
            return {"kind": "fn", "label": "fn"}
        if normalized in {"<num_lock>", "<numlock>", "num_lock", "numlock"}:
            return {"kind": "keycode", "key_code": 71, "label": "num_lock"}
        match = re.match(r"<(?:keycode|key_code|vk)\s*:\s*(\d+)\s*>", normalized)
        if match:
            return {
                "kind": "keycode",
                "key_code": int(match.group(1)),
                "label": f"keycode:{match.group(1)}",
            }
        return None


class SpecialShortcut(TypedDict, total=False):
    kind: Literal["fn", "keycode"]
    label: str
    key_code: int


class _FnKeyMonitor:
    """Listen for Fn key transitions using a Quartz event tap."""

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None] | None,
        mode: str,
    ) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self.mode = mode
        self._pressed = False
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._thread: threading.Thread | None = None
        self._event_tap = None
        self._run_loop_source = None
        self._callback = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()
        if self._error is not None:
            raise self._error

    def join(self) -> None:
        if self._thread is None:
            self._stop_event.wait()
            return
        self._thread.join()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        try:
            import Quartz
        except Exception as exc:
            self._error = RuntimeError(
                "Fn-only hotkey requires the Quartz framework (pyobjc)."
            )
            self._error.__cause__ = exc
            self._ready.set()
            return
        event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
        self._callback = self._handle_event
        self._event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            event_mask,
            self._callback,
            None,
        )
        if not self._event_tap:
            self._error = RuntimeError(
                "Unable to create event tap for Fn. "
                "Enable Input Monitoring and Accessibility permissions."
            )
            self._ready.set()
            return
        self._run_loop_source = Quartz.CFMachPortCreateRunLoopSource(
            None, self._event_tap, 0
        )
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            self._run_loop_source,
            Quartz.kCFRunLoopCommonModes,
        )
        Quartz.CGEventTapEnable(self._event_tap, True)
        self._ready.set()
        while not self._stop_event.is_set():
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.2, False)
        if self._run_loop_source is not None:
            Quartz.CFRunLoopRemoveSource(
                Quartz.CFRunLoopGetCurrent(),
                self._run_loop_source,
                Quartz.kCFRunLoopCommonModes,
            )

    def _handle_event(self, proxy, event_type, event, refcon):
        import Quartz

        if event_type == Quartz.kCGEventTapDisabledByTimeout and self._event_tap:
            Quartz.CGEventTapEnable(self._event_tap, True)
            return event
        if event_type != Quartz.kCGEventFlagsChanged:
            return event
        flags = Quartz.CGEventGetFlags(event)
        fn_down = bool(flags & Quartz.kCGEventFlagMaskSecondaryFn)
        if fn_down and not self._pressed:
            self._pressed = True
            try:
                self.on_press()
            except Exception:
                logger.exception("Fn hotkey press handler failed")
        elif not fn_down and self._pressed:
            self._pressed = False
            if self.mode == "hold" and self.on_release is not None:
                try:
                    self.on_release()
                except Exception:
                    logger.exception("Fn hotkey release handler failed")
        return event


class _KeyCodeMonitor:
    """Listen for a specific keycode using a Quartz event tap."""

    def __init__(
        self,
        key_code: int,
        on_press: Callable[[], None],
        on_release: Callable[[], None] | None,
        mode: str,
        label: str,
    ) -> None:
        self.key_code = key_code
        self.on_press = on_press
        self.on_release = on_release
        self.mode = mode
        self.label = label
        self._pressed = False
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._thread: threading.Thread | None = None
        self._event_tap = None
        self._run_loop_source = None
        self._callback = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()
        if self._error is not None:
            raise self._error

    def join(self) -> None:
        if self._thread is None:
            self._stop_event.wait()
            return
        self._thread.join()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        try:
            import Quartz
        except Exception as exc:
            self._error = RuntimeError(
                "Special hotkeys require the Quartz framework (pyobjc)."
            )
            self._error.__cause__ = exc
            self._ready.set()
            return
        event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) | Quartz.CGEventMaskBit(
            Quartz.kCGEventKeyUp
        )
        self._callback = self._handle_event
        self._event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            event_mask,
            self._callback,
            None,
        )
        if not self._event_tap:
            self._error = RuntimeError(
                f"Unable to create event tap for {self.label}. "
                "Enable Input Monitoring and Accessibility permissions."
            )
            self._ready.set()
            return
        self._run_loop_source = Quartz.CFMachPortCreateRunLoopSource(
            None, self._event_tap, 0
        )
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            self._run_loop_source,
            Quartz.kCFRunLoopCommonModes,
        )
        Quartz.CGEventTapEnable(self._event_tap, True)
        self._ready.set()
        while not self._stop_event.is_set():
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.2, False)
        if self._run_loop_source is not None:
            Quartz.CFRunLoopRemoveSource(
                Quartz.CFRunLoopGetCurrent(),
                self._run_loop_source,
                Quartz.kCFRunLoopCommonModes,
            )

    def _handle_event(self, proxy, event_type, event, refcon):
        import Quartz

        if event_type == Quartz.kCGEventTapDisabledByTimeout and self._event_tap:
            Quartz.CGEventTapEnable(self._event_tap, True)
            return event
        if event_type not in {Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp}:
            return event
        keycode = Quartz.CGEventGetIntegerValueField(
            event, Quartz.kCGKeyboardEventKeycode
        )
        if keycode != self.key_code:
            return event
        if event_type == Quartz.kCGEventKeyDown:
            autorepeat = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventAutorepeat
            )
            if autorepeat:
                return event
            if not self._pressed:
                self._pressed = True
                try:
                    self.on_press()
                except Exception:
                    logger.exception("%s hotkey press handler failed", self.label)
        else:
            if self._pressed:
                self._pressed = False
                if self.mode == "hold" and self.on_release is not None:
                    try:
                        self.on_release()
                    except Exception:
                        logger.exception("%s hotkey release handler failed", self.label)
        return event


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
