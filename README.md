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
Hold `fn` (configurable) to start recording, release to transcribe, and the text will paste where your cursor is. Use `Ctrl+C` to exit. You'll hear the macOS `Morse` cue when recording starts and again when transcription begins (falls back silently if system sounds aren't available).

### Configuration
Create `configs/config.yaml` to override defaults:
```yaml
shortcut:
  - "<fn>"
  - "<num_lock>"
hotkey_mode: "hold"
trigger_mode: "hotkey"
input_device: null
model_name: "small.en"
device: "auto"
clipboard: true
auto_paste: true
sample_rate: 16000
channels: 1
max_recording_seconds: 300
duck_audio: false
duck_volume: 20
audio_trigger_threshold: 0.01
audio_trigger_start_seconds: 0.1
audio_trigger_silence_seconds: 0.6
log_transcripts: false
log_path: "~/Library/Logs/tts-extension/transcripts.log"
```
Run with `uv run tts-extension listen -c configs/config.yaml`.
Set `hotkey_mode` to `hold` (press/release) or `toggle` (press once to start/stop).
Set `trigger_mode` to `audio` to start/stop based on input volume (handy for mic mute toggles).
Set `input_device` to the macOS input name (or index) if you want to lock to an external mic.
List inputs with `uv run tts-extension devices`.

### Permissions & Tips
- On first run, macOS will request microphone access; grant it via System Settings → Privacy & Security → Microphone.
- To allow simulated keystrokes/Command+V, add your terminal (or packaged app) under Accessibility → Input Monitoring.
- Fn-only hotkeys depend on your keyboard driver; if it doesn't trigger, map Fn to F13 (e.g., via Karabiner) and set `shortcut: "<f13>"`.
- External keyboards can use other single keys like `"<num_lock>"` in the shortcut list.
- If a key isn't recognized, you can use `"<keycode:71>"`-style shortcuts on macOS (Num Lock/Clear is often 71); use Karabiner-Elements EventViewer to confirm.
- Set `duck_audio: true` to temporarily lower system output volume while recording (macOS only).
- For `trigger_mode: "audio"`, adjust `audio_trigger_threshold` if your mic starts/stops too easily.
- Whisper runs entirely locally; choose larger models for accuracy at the cost of speed and CPU/GPU usage.
