# Local transcription

Local audio/video transcription with Whisper large-v3, speaker diarization, and an agent skill for substantive proofreading. Produces comparable raw and proofread TXT/SRT files without sending audio to a hosted service.

The CLI runs the media and speech models locally. The invoking agent reads the resulting text, proposes corrections, and uses the CLI to apply them to both formats. This is **not** an autonomous local language-model proofreader: the agent may be cloud-hosted and the transcript becomes part of its context.

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and FFmpeg/FFprobe. The locked environment is tested on Linux with Python 3.13; the default is CPU int8 inference. Allow approximately 4 GB for models plus the Python environment and working audio. Long recordings can take substantial CPU time.

A repository checkout is optional. Download the packaged release into a new empty directory and install its CLI with the locked runtime constraints:

```bash
gh release download v0.1.0 --repo ihoru/local-transcription \
  --pattern 'local_transcription-0.1.0-*.whl' \
  --pattern 'runtime-constraints.txt' \
  --pattern 'local-transcription-skill.zip' --pattern 'SHA256SUMS'
sha256sum --check SHA256SUMS
uv tool install --python 3.13 --constraints runtime-constraints.txt \
  ./local_transcription-0.1.0-py3-none-any.whl
uv tool update-shell
local-transcription models install
local-transcription doctor --verify
```

The repository and releases are private: another user needs GitHub access before downloading. The wheel installs the Python CLI and dependencies, without tests or Git history. It requires Python and FFmpeg; it is not a standalone native binary. See the [installation guide](skills/local-transcription/references/install.md) for shell setup and skill installation.

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

- [CLI and troubleshooting](skills/local-transcription/references/usage.md)
- [Architecture and offline boundary](docs/architecture.md)
- [Review schema and editorial policy](skills/local-transcription/references/proofreading.md)
- [Model sources and third-party notices](docs/models.md)
- [Validation and observed limitations](docs/validation.md)

## Development

```bash
gh repo clone ihoru/local-transcription
cd local-transcription
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
```

Run the development CLI with `uv run --locked local-transcription`. See [release packaging](docs/releases.md) to build the installable wheel and portable skill.

CI runs deterministic tests with synthetic media. Real speech evaluations run locally; personal recordings, transcripts, and model weights are excluded from the repository. This private repository does not grant a public license to the project code. Third-party components retain their own licenses.
