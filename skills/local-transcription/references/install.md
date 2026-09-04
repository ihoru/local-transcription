# Install or locate the CLI

Install `local-transcription` from PyPI without a source checkout. Python 3.11+ and uv are required; FFmpeg/FFprobe install automatically with the CLI on supported platforms; CI tests Python 3.13 on Linux x86-64 and macOS 15 on Apple Silicon and Intel. macOS wheels target macOS 13+ and need neither Homebrew nor Rosetta; inference uses CPU int8, without Apple GPU acceleration. The package provides a console command in an isolated Python environment, not a standalone native binary. Allow about 4 GB for model files plus the environment and working audio.

## Existing installation

If `local-transcription --version` works, use that console command. Version 0.1.3 is the release for this skill. Check `--help` for the required commands if another version is installed.

For an existing developer checkout, resolve the skill symlink and check whether two directories above the skill directory contains this project's `pyproject.toml`. If so, use `uv run --locked --project /absolute/repo/path local-transcription`; run `uv sync --locked --project /absolute/repo/path` if necessary. This is an optional reuse path, not a requirement to clone.

## Install from PyPI

```bash
uv tool install --python 3.13 local-transcription==0.1.3
uv tool update-shell
```

If the current shell has not picked up the tool directory, run the executable inside the directory printed by `uv tool dir --bin`. No GitHub account or repository access is needed. If the version is unavailable, report the actual installation failure and use the matching public GitHub release if available; do not silently install an unrelated package or invent a substitute implementation.

Standard PyPI installation uses the dependency versions allowed by the package metadata. For the exact tested runtime versions, use the constraints included in the matching GitHub release.

## Exact runtime installation and portable skill

Download `runtime-constraints.txt`, `local-transcription-skill.zip`, and `SHA256SUMS` from https://github.com/ihoru/local-transcription/releases/tag/v0.1.3 into a new empty directory. Verify each downloaded asset against its entry in `SHA256SUMS` using Python's hashlib (available on every supported setup). Install the CLI from PyPI, letting the installer select the native wheel:

```bash
uv tool install --python 3.13 --constraints runtime-constraints.txt local-transcription==0.1.3
```

Extract the verified skill ZIP into `~/.agents/skills/`; it contains a `local-transcription/` folder with all reference documents. Inspect an existing destination before replacing it. A developer may instead retain the symlink to the canonical skill in their checkout. Downloaded setup assets are not needed at runtime.

For offline package transfer, the release also includes separate macOS arm64 and x86_64 wheels, plus the generic wheel used on Linux/Windows. Choose the matching Mac wheel; do not manually install the generic wheel on a Mac. Normal PyPI installation makes this selection automatically.

## Prepare models and verify

Run `local-transcription doctor`, then `local-transcription models install` for missing weights, and `local-transcription doctor --verify`. Reuse existing weights with `models install --from-dir /path/to/models`. Inference never downloads models implicitly. The default cache is `~/.cache/local-transcription/models` (or `$XDG_CACHE_HOME/local-transcription/models`); `LOCAL_TRANSCRIPTION_MODELS` or `--models-dir` overrides it.

For a broken PyPI installation, repeat `uv tool install --reinstall --python 3.13 local-transcription==0.1.3`. For an exact-runtime installation, repeat installation with the same constraints and wheel. For a developer checkout, use `uv sync --locked`.

## Packaged FFmpeg support

macOS wheels contain native FFmpeg and FFprobe compiled from checksum-pinned upstream source, with their license, source archive, and build recipe. The other supported platforms use `ffmpeg-binaries-compat`. The CLI prefers system executables and otherwise uses packaged paths, with no downloads during processing. `doctor` actually executes both tools and reports their selected paths. On an unsupported platform, provide system FFmpeg.

Mac source/editable installs require Xcode command line tools and download/compile FFmpeg during package setup. Prefer a normal PyPI wheel installation for end users.
