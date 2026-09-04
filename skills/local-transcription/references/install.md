# Install or locate the CLI

Install `local-transcription` from PyPI without a source checkout. Python 3.11+ and uv are required; FFmpeg/FFprobe install automatically with the CLI on supported platforms; Linux with Python 3.13 is the tested platform. The package provides a console command in an isolated Python environment, not a standalone native binary. Allow about 4 GB for model files plus the environment and working audio.

## Existing installation

If `local-transcription --version` works, use that console command. Version 0.1.2 is the release for this skill. Check `--help` for the required commands if another version is installed.

For an existing developer checkout, resolve the skill symlink and check whether two directories above the skill directory contains this project's `pyproject.toml`. If so, use `uv run --locked --project /absolute/repo/path local-transcription`; run `uv sync --locked --project /absolute/repo/path` if necessary. This is an optional reuse path, not a requirement to clone.

## Install from PyPI

```bash
uv tool install --python 3.13 local-transcription==0.1.2
uv tool update-shell
```

If the current shell has not picked up the tool directory, run the executable inside the directory printed by `uv tool dir --bin`. No GitHub account or repository access is needed. If the version is unavailable, report the actual installation failure and use the matching public GitHub release if available; do not silently install an unrelated package or invent a substitute implementation.

Standard PyPI installation uses the dependency versions allowed by the package metadata. For the exact tested runtime versions, use the constraints included in the matching GitHub release.

## Exact runtime installation and portable skill

Download these files from the public release at https://github.com/ihoru/local-transcription/releases/tag/v0.1.2 into a new empty directory: `local_transcription-0.1.2-py3-none-any.whl`, `runtime-constraints.txt`, `local-transcription-skill.zip`, and `SHA256SUMS`. Browser downloads require no sign-in. If an authenticated GitHub CLI is already available, the equivalent command is:

```bash
gh release download v0.1.2 --repo ihoru/local-transcription \
  --pattern 'local_transcription-0.1.2-*.whl' \
  --pattern 'runtime-constraints.txt' \
  --pattern 'local-transcription-skill.zip' --pattern 'SHA256SUMS'
sha256sum --check --ignore-missing SHA256SUMS
uv tool install --python 3.13 --constraints runtime-constraints.txt \
  ./local_transcription-0.1.2-py3-none-any.whl
```

Verify all three downloaded assets report OK before using them. The checksum file also lists the optional source archive; `--ignore-missing` permits omitting that archive. Extract the verified skill ZIP into `~/.agents/skills/`; it contains a `local-transcription/` folder with all reference documents. Inspect an existing destination before replacing it. A developer may instead retain the symlink to the canonical skill in their checkout. Downloaded setup assets are not needed at runtime.

## Prepare models and verify

Run `local-transcription doctor`, then `local-transcription models install` for missing weights, and `local-transcription doctor --verify`. Reuse existing weights with `models install --from-dir /path/to/models`. Inference never downloads models implicitly. The default cache is `~/.cache/local-transcription/models` (or `$XDG_CACHE_HOME/local-transcription/models`); `LOCAL_TRANSCRIPTION_MODELS` or `--models-dir` overrides it.

For a broken PyPI installation, repeat `uv tool install --reinstall --python 3.13 local-transcription==0.1.2`. For an exact-runtime installation, repeat installation with the same constraints and wheel. For a developer checkout, use `uv sync --locked`.

## Packaged FFmpeg support

The `ffmpeg-binaries-compat` dependency supplies FFmpeg and FFprobe in platform wheels for Linux x86-64, Windows x86-64, and macOS (the upstream wheel is tagged universal2). Linux x86-64 is locally tested. The CLI uses existing system executables when present, otherwise the packaged paths, and performs no binary downloads during processing. `doctor` reports the actual selected paths. On platforms without a compatible binary wheel, or when installation disables platform wheels, system FFmpeg is still required. Do not run the dependency's downloader as a fallback.
