# Repository Guidelines

## Project Structure & Module Organization
Keep user-facing code under `tts_extension/`, with submodules for `config.py`, `hotkey.py`, `audio.py`, `transcription.py`, `actions.py`, `workflow.py`, and CLI entrypoints (`cli.py`, `__main__.py`). Store sample configs in `configs/`, helper scripts in `scripts/`, and tests plus fixtures inside `tests/`. Documentation lives in `README.md` and this file. Avoid ad-hoc files in the root; everything should flow through these directories so automation can find it.

## Build, Test, and Development Commands
- `uv init --app --package tts-extension`: bootstrap a CLI-ready project in the current directory (replace flags if you need a library layout).
- `uv add whisper torch sounddevice pynput pyperclip pytest`: install runtime and dev dependencies; add `--dev` for test-only packages.
- `uv run tts-extension listen`: start the hotkey listener and transcription workflow locally; useful for manual verification.
- `uv run pytest`: execute automated tests, including config parsing, audio mocks, and transcription adapters.
- `uv tree` / `uv lock --upgrade`: inspect dependency graph and refresh lockfiles as needed.
Keep helper scripts under `scripts/` and document complex workflows in `README.md`.

## uv Lifecycle Commands
Use uv for the entire release flow:
- `uv build`: build the packageable project artifacts.
- `uv publish`: push the package to PyPI (requires configured credentials).
- `uv version --bump <major|minor|rc|stable>`: bump semantic versions; combine with qualifiers (`--bump minor --bump beta`) when shipping previews.

## Coding Style & Naming Conventions
Use Python 3.11+, PEP 8 style, 4-space indentation, and descriptive snake_case for functions and variables. Modules should map to responsibilities (e.g., `audio.py` for mic capture). Keep comments short and informative; prefer docstrings for public functions. Run `ruff` or `black` if added later, and avoid introducing non-ASCII characters unless necessary for tests.

## Testing Guidelines
Tests live in `tests/` mirroring the module names (`test_config.py`, `test_transcription.py`, etc.). Use pytest fixtures for audio samples and mock Whisper where practical. Aim for coverage on configuration validation, workflow orchestration, and failure paths (e.g., device errors). Integration tests that hit real microphones should be opt-in and clearly skipped by default.

## Commit & Pull Request Guidelines
Follow conventional, descriptive commit messages (`feat: add hotkey listener`, `fix: handle clipboard failures`). Each pull request should summarize changes, list manual test steps (e.g., `poetry run tts-extension listen`), and reference related issues if available. Include screenshots or logs when touching UX-facing behavior. Ensure CI passes before requesting review and keep diffs focused on a single concern.
