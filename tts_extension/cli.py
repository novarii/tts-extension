from __future__ import annotations

import logging
from pathlib import Path

import typer

from .actions import OutputActions
from .audio import AudioRecorder, SystemSoundPlayer
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
    hotkey = HotkeyListener(app_config.shortcut, workflow.toggle_recording)
    monitor = PeriodicMonitor(1.0, workflow.stop_if_needed)

    monitor.start()
    hotkey.start()
    typer.echo(f"Press {app_config.shortcut} to dictate. Ctrl+C to exit.")

    try:
        hotkey.join()
    except KeyboardInterrupt:
        typer.echo("Stopping...")
    finally:
        monitor.stop()
        hotkey.stop()


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def _build_workflow(config: AppConfig) -> DictationWorkflow:
    recorder = AudioRecorder(sample_rate=config.sample_rate, channels=config.channels)
    transcriber = WhisperTranscriber(model_name=config.model_name, device=config.device)
    sound_player = SystemSoundPlayer()
    actions = OutputActions(
        use_clipboard=config.clipboard,
        auto_paste=config.auto_paste,
        type_characters=config.type_characters,
        log_transcripts=config.log_transcripts,
        log_path=config.log_path,
    )
    return DictationWorkflow(config, recorder, transcriber, actions, sound_player=sound_player)


def run() -> None:
    app()
