## TTS Extension

Push-to-talk speech-to-text helper for macOS that records locally, runs OpenAI Whisper on-device, and pastes the transcript into the focused text field.

### Requirements
- Python 3.12+
- Microphone + accessibility permissions (pynput needs access to control the keyboard)
- [uv](https://docs.astral.sh/uv/) for dependency management

### Setup
```bash
uv init --app --package tts-extension  # only needed the first time in a new repo
uv sync                               # create/update the virtual environment
```

Install runtime + dev dependencies:
```bash
uv add whisper torch sounddevice pynput pyperclip pyyaml typer numpy soundfile
uv add --dev pytest
```

### Running Locally
```bash
uv run tts-extension listen --verbose
```
Hold `cmd+shift+;` (configurable) to start recording, release to transcribe, and the text will paste where your cursor is. Use `Ctrl+C` to exit.

### Configuration
Create `configs/config.yaml` to override defaults:
```yaml
shortcut: "<cmd>+<shift>+;"
model_name: "small.en"
device: "auto"
clipboard: true
auto_paste: true
sample_rate: 16000
channels: 1
max_recording_seconds: 45
log_transcripts: false
log_path: "~/Library/Logs/tts-extension/transcripts.log"
```
Run with `uv run tts-extension listen -c configs/config.yaml`.

### Permissions & Tips
- On first run, macOS will request microphone access; grant it via System Settings → Privacy & Security → Microphone.
- To allow simulated keystrokes/Command+V, add your terminal (or packaged app) under Accessibility → Input Monitoring.
- Whisper runs entirely locally; choose larger models for accuracy at the cost of speed and CPU/GPU usage.
