# Local transcription

Local audio/video transcription with Whisper large-v3, speaker diarization, and an agent skill for substantive proofreading. Produces comparable raw and proofread TXT/SRT files without sending audio to a hosted service.

The CLI runs the media and speech models locally. The invoking agent reads the resulting text, proposes corrections, and uses the CLI to apply them to both formats. This is **not** an autonomous local language-model proofreader: the agent may be cloud-hosted and the transcript becomes part of its context.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). FFmpeg and FFprobe are installed automatically as a Python dependency on supported platforms. The locked environment is tested on Linux with Python 3.13; the default is CPU int8 inference. Allow approximately 4 GB for models plus the Python environment and working audio. Long recordings can take substantial CPU time.

Install the CLI from PyPI without cloning the repository:

```bash
uv tool install --python 3.13 local-transcription==0.1.2
uv tool update-shell
local-transcription models install
local-transcription doctor --verify
```

If your current shell cannot find the command yet, reopen it or use the executable inside the directory printed by `uv tool dir --bin`. Python dependencies include ready-to-run FFmpeg and FFprobe binaries. The CLI prefers existing system tools and otherwise uses the packaged binaries without changing PATH or requiring administrator access. Model weights are installed separately. The package provides an executable CLI command, not a standalone native binary.

The repository and GitHub release downloads are public. See the [installation guide](https://github.com/ihoru/local-transcription/blob/main/skills/local-transcription/references/install.md) for the portable skill archive and an alternative installation with exact runtime constraints. Standard PyPI installation resolves dependencies from package metadata; the release constraints reproduce the versions in our lockfile.

To reuse an existing model directory instead of downloading the same weights:

```bash
local-transcription models install --from-dir /path/to/existing/models
```

The default cache is `$XDG_CACHE_HOME/local-transcription/models`, or `~/.cache/local-transcription/models`. Override it using `--models-dir` or `LOCAL_TRANSCRIPTION_MODELS`. Setup verifies SHA-256 checksums; `doctor --verify` can verify them again. Downloads occur only through `models install`.

## Use

```bash
# Full recording, automatic language and speaker count
local-transcription transcribe /path/to/meeting.webm

# Audio input; disable speaker analysis
local-transcription transcribe /path/to/interview.mp3 --no-diarization

# Known language and speaker count
local-transcription transcribe /path/to/meeting.mkv --language ru --speakers 2

# Extract audio alone, detecting the source format by its contents
local-transcription convert /path/to/video.bin

# Recheck a difficult passage without changing the transcript
local-transcription recheck /path/to/meeting.transcription --start 05:55 --end 06:15

# Apply agent-reviewed, word-specific corrections
local-transcription apply-review /path/to/meeting.transcription /path/to/edits.json
```

`transcribe` creates a new `<stem>.transcription` folder next to the input. Repeated runs use `-2`, `-3`, etc. `--output-dir` changes the requested folder, with the same collision protection. The input and previous results remain unchanged.

| Artifact | Produced by |
|---|---|
| `<stem>.audio.<extension>` | Video audio extraction; stream copy when supported, FLAC fallback |
| `<stem>.txt`, `<stem>.srt` | Local transcription and optional speaker analysis |
| `<stem>.proofread.txt`, `<stem>.proofread.srt` | Agent review followed by `apply-review` |
| `<stem>.summary.md` | Skill, only after the user requests or confirms a summary |
| `work/` | PCM audio, canonical words, model output, review handoff, diagnostics |

Text remains in the spoken language. Speaker labels and tooling are in English. With diarization disabled, output omits speaker labels rather than calling every speaker “unknown.” Diagnostics never appear as a transcript appendix.

## Install the skill

The release archive `local-transcription-skill.zip` contains the skill and all its reference documents. Extract it into `~/.agents/skills/` after checksum verification. Inspect any existing `local-transcription` destination before replacing it.

For development, keep the canonical skill in this repository and install an absolute symlink from the checkout:

```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)/skills/local-transcription" ~/.agents/skills/local-transcription
```

Invoke the skill by name or ask the agent to transcribe a local recording with proofread subtitles. It uses an installed CLI or an existing development environment, completes all four transcript files, then asks about a summary. If the CLI is missing, the skill installs the packaged release without cloning the repository.

## Documentation

- [CLI and troubleshooting](https://github.com/ihoru/local-transcription/blob/main/skills/local-transcription/references/usage.md)
- [Architecture and offline boundary](https://github.com/ihoru/local-transcription/blob/main/docs/architecture.md)
- [Review schema and editorial policy](https://github.com/ihoru/local-transcription/blob/main/skills/local-transcription/references/proofreading.md)
- [Model sources and third-party notices](https://github.com/ihoru/local-transcription/blob/main/docs/models.md)
- [Validation and observed limitations](https://github.com/ihoru/local-transcription/blob/main/docs/validation.md)

## Development

```bash
gh repo clone ihoru/local-transcription
cd local-transcription
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
```

Run the development CLI with `uv run --locked local-transcription`. See [release packaging](https://github.com/ihoru/local-transcription/blob/main/docs/releases.md) to build the installable wheel and portable skill.

CI runs deterministic tests with synthetic media. Real speech evaluations run locally; personal recordings, transcripts, and model weights are excluded from the repository. No open-source license has been selected for the project code. Third-party components retain their own licenses.
