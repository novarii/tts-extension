from __future__ import annotations

import logging
from pathlib import Path

import typer
import sounddevice as sd

from .actions import OutputActions
from .audio import AudioRecorder, AudioTriggerMonitor, SystemAudioDucker, SystemSoundPlayer
from .config import AppConfig
from .hotkey import HotkeyListener, PeriodicMonitor
from .transcription import WhisperTranscriber
from .workflow import DictationWorkflow

app = typer.Typer(help="Hotkey-driven Whisper transcription utility")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML/JSON/TOML config file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs"),
) -> None:
    """Entry point used when running without subcommands."""
    if ctx.invoked_subcommand is not None:
        return
    listen(config=config, verbose=verbose)


@app.command()
def devices() -> None:
    """List input devices available for recording."""
    devices = sd.query_devices()
    default_input, _ = sd.default.device
    found = False
    for index, info in enumerate(devices):
        inputs = int(info.get("max_input_channels", 0))
        if inputs <= 0:
            continue
        found = True
        marker = "*" if default_input == index else " "
        name = info.get("name", "")
        typer.echo(f"{marker} {index}: {name} (inputs={inputs})")
    if not found:
        typer.echo("No input devices found.")
        return
    typer.echo("Set input_device to the name or index above in configs/config.yaml.")


@app.command()
def listen(
    config: Path = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML/JSON/TOML config file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs"),
) -> None:
    """Start the hotkey listener and process dictations indefinitely."""

    _configure_logging(verbose)
    app_config = AppConfig.load(config)

    workflow = _build_workflow(app_config)
    trigger_mode = app_config.trigger_mode.lower()
    if trigger_mode not in {"hotkey", "audio"}:
        raise ValueError("trigger_mode must be 'hotkey' or 'audio'")

    listeners: list[HotkeyListener] = []
    audio_monitor: AudioTriggerMonitor | None = None
    if trigger_mode == "audio":
        if app_config.audio_trigger_threshold <= 0:
            raise ValueError("audio_trigger_threshold must be > 0")
        if app_config.audio_trigger_start_seconds < 0:
            raise ValueError("audio_trigger_start_seconds must be >= 0")
        if app_config.audio_trigger_silence_seconds <= 0:
            raise ValueError("audio_trigger_silence_seconds must be > 0")
        audio_monitor = AudioTriggerMonitor(
            workflow,
            sample_rate=app_config.sample_rate,
            channels=app_config.channels,
            device=app_config.input_device,
            threshold=app_config.audio_trigger_threshold,
            start_seconds=app_config.audio_trigger_start_seconds,
            silence_seconds=app_config.audio_trigger_silence_seconds,
        )
        prompt = (
            "Listening for audio activity. Toggle your mic to start/stop. "
            "Ctrl+C to exit."
        )
    else:
        shortcuts = _normalize_shortcuts(app_config.shortcut)
        if app_config.hotkey_mode == "hold":
            listeners = [
                HotkeyListener(
                    shortcut,
                    workflow.start_recording,
                    workflow.stop_recording,
                    mode="hold",
                )
                for shortcut in shortcuts
            ]
            prompt = (
                f"Hold {_format_shortcuts(shortcuts)} to dictate, release to paste. "
                "Ctrl+C to exit."
            )
        else:
            listeners = [
                HotkeyListener(
                    shortcut,
                    workflow.toggle_recording,
                    mode="toggle",
                )
                for shortcut in shortcuts
            ]
            prompt = (
                f"Press {_format_shortcuts(shortcuts)} to toggle dictation. Ctrl+C to exit."
            )
    monitor = PeriodicMonitor(1.0, workflow.stop_if_needed)

    monitor.start()
    for listener in listeners:
        listener.start()
    if audio_monitor is not None:
        audio_monitor.start()
    typer.echo(prompt)

    try:
        if audio_monitor is not None:
            audio_monitor.join()
        else:
            listeners[0].join()
    except KeyboardInterrupt:
        typer.echo("Stopping...")
    finally:
        monitor.stop()
        for listener in listeners:
            listener.stop()
        if audio_monitor is not None:
            audio_monitor.stop()


def _normalize_shortcuts(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        shortcuts = [value]
    else:
        shortcuts = list(value)
    shortcuts = [shortcut.strip() for shortcut in shortcuts if shortcut.strip()]
    if not shortcuts:
        raise ValueError("At least one shortcut must be configured.")
    return shortcuts


def _format_shortcuts(shortcuts: list[str]) -> str:
    if len(shortcuts) == 1:
        return shortcuts[0]
    if len(shortcuts) == 2:
        return f"{shortcuts[0]} or {shortcuts[1]}"
    return ", ".join(shortcuts[:-1]) + f", or {shortcuts[-1]}"


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def _build_workflow(config: AppConfig) -> DictationWorkflow:
    recorder = AudioRecorder(
        sample_rate=config.sample_rate,
        channels=config.channels,
        device=config.input_device,
    )
    transcriber = WhisperTranscriber(model_name=config.model_name, device=config.device)
    sound_player = SystemSoundPlayer()
    audio_ducker = SystemAudioDucker(enabled=config.duck_audio)
    actions = OutputActions(
        use_clipboard=config.clipboard,
        auto_paste=config.auto_paste,
        type_characters=config.type_characters,
        log_transcripts=config.log_transcripts,
        log_path=config.log_path,
    )
    return DictationWorkflow(
        config,
        recorder,
        transcriber,
        actions,
        sound_player=sound_player,
        audio_ducker=audio_ducker,
    )


def run() -> None:
    app()
