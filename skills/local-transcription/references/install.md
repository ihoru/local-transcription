# Install or locate the CLI

The release contains an installable Python wheel, locked runtime version constraints, and this self-contained skill. Python 3.11+, uv, and system FFmpeg/FFprobe are required; Linux with Python 3.13 is the tested platform. The wheel is not a standalone native binary: uv installs it and its dependencies into an isolated tool environment. Allow about 4 GB for model files plus the environment and working audio.

## Existing installation

If `local-transcription --version` works, use that console command. Version 0.1.0 is the release for this skill. Check `--help` for the required commands if another version is installed.

For an existing developer checkout, resolve the skill symlink and check whether two directories above the skill directory contains this project's `pyproject.toml`. If so, use `uv run --locked --project /absolute/repo/path local-transcription`; run `uv sync --locked --project /absolute/repo/path` if necessary. This is an optional reuse path, not a requirement to clone.

## Release installation without a checkout

Use the private GitHub release `ihoru/local-transcription`, tag `v0.1.0`. The user needs repository access and authenticated `gh`; an unauthenticated or unauthorized user cannot download these private assets. Authentication or access failures need the user to resolve access. Do not clone the source as a workaround or put tokens in commands.

Download the release wheel, dependency constraints, skill archive, and checksums into a new empty temporary directory. From that directory:

```bash
gh release download v0.1.0 --repo ihoru/local-transcription \
  --pattern 'local_transcription-0.1.0-*.whl' \
  --pattern 'runtime-constraints.txt' \
  --pattern 'local-transcription-skill.zip' --pattern 'SHA256SUMS'
sha256sum --check SHA256SUMS
uv tool install --python 3.13 --constraints runtime-constraints.txt \
  ./local_transcription-0.1.0-py3-none-any.whl
uv tool update-shell
```

If the current shell has not picked up the tool directory, run the executable at the path printed by `uv tool dir --bin`. The downloaded assets can be removed after installation; they are not a runtime checkout. A future upgrade should use a new release's wheel and constraints together.

If installing this skill for the first time, extract `local-transcription-skill.zip` into `~/.agents/skills/`; it contains a `local-transcription/` folder with this file and all review references. Inspect an existing destination before replacing it. A developer may instead retain a symlink to the canonical skill in their checkout.

Run `local-transcription doctor`, then `local-transcription models install` for missing weights, and `local-transcription doctor --verify`. Existing weights may be reused with `models install --from-dir /path/to/models`. Inference never downloads models implicitly. The default cache is `~/.cache/local-transcription/models` (or `$XDG_CACHE_HOME/local-transcription/models`); `LOCAL_TRANSCRIPTION_MODELS` or `--models-dir` overrides it.

For a broken release installation, repeat the verified installation with `uv tool install --reinstall` and the same constraints and wheel. For a developer checkout, use `uv sync --locked`.
