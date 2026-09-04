# CLI usage and troubleshooting

After release installation, run `local-transcription` directly. For development, run commands from a checkout with `uv run --locked local-transcription`, or from anywhere with `uv run --locked --project /absolute/repo/path local-transcription`. `uv sync --locked` installs the console entry point into the repository environment. The CLI itself is usable without an agent; the skill supplies the editorial pass.

## Media and output selection

FFprobe inspects streams even when the file extension is absent or incorrect. Attached cover art does not make an audio file a video. If several audio streams exist, the default-marked audio stream is selected, otherwise the first audio stream. Use `--audio-stream INDEX` to choose an absolute FFprobe stream index.

`convert` saves extracted audio beside the source, or in `--output-dir`. Common codecs are copied into compatible containers; unsupported copy formats fall back to lossless FLAC. FLAC cannot restore quality already lost in the source. Existing audio files are preserved and output names are incremented.

`transcribe` saves extracted audio when its input has video. Both video and audio inputs are decoded to mono 16 kHz PCM in `work/audio.wav` for model inference. The original channels and codec remain available in the input and extracted audio. Input is always treated as a file path, not a shell command or remote URL.

All runs are full-length. For an explicitly requested trial, prepare a separate clip with FFmpeg and pass that clip as the input. No five-minute or two-speaker assumptions are built in.

## Speaker analysis

Automatic mode uses Pyannote segmentation and WeSpeaker embeddings through Sherpa-ONNX. Its automatic cluster threshold is 0.5; `--speaker-threshold` overrides it. A lower threshold tends to produce more speakers. `--speakers N` sets a known count instead, while `--no-diarization` bypasses model loading and assignment entirely.

Speaker numbering follows the first assigned spoken word. A label describes a voice cluster, not a verified identity. Energy-weighted temporal overlap assigns recognized words to turns. Competing assignments remain unknown; short unknown gaps may be joined only when bounded by the same voice. Overlapping voices are not separated into independent audio sources.

For difficult recordings with known samples, create a reference file:

```json
{
  "speakers": [
    {"intervals": [[10.0, 16.0], [35.0, 41.0]]},
    {"intervals": [[90.0, 97.0]]}
  ]
}
```

Each array entry is one distinct speaker. Intervals use seconds in the full recording, last at least one second, and should contain clean speech by that speaker. Use `--speaker-references references.json`. This replaces automatic clustering with local voice matching; it does not transcribe only those intervals. It never assumes everything before or after a reference belongs to that voice. Matching uses three-second windows, a half-second step, minimum cosine similarity 0.60, and a 0.04 margin between candidates. Inspect results because samples and channel quality affect accuracy.

## Runtime and recovery

- CPU int8 is the default. `--threads` defaults to 8 and `--batch-size` to 4. Use lower values if memory is constrained.
- `--device cuda` explicitly requests GPU recognition with float16. It requires a compatible CTranslate2/CUDA runtime. Speaker analysis stays on CPU. An unavailable GPU fails visibly; it does not silently change the requested hardware.
- `work/run.json` records `processing`, `failed`, `awaiting_review`, or `reviewed`. Interrupted recognition checkpoints remain in `work/recognition.partial.json`. Automatic resume is not implemented; a retry creates a new run and preserves the failed one.
- `recheck` accepts seconds, `MM:SS`, or `HH:MM:SS`, and saves a uniquely named result under `work/rechecks/`. It does not modify recognized words or subtitle files.
- Silence yields empty speech outputs rather than fabricated transcript text. Check the recording if speech was expected.

## Common problems

**FFmpeg/FFprobe missing:** these tools normally install with the CLI. Run `doctor` to see the selected paths. Reinstall the CLI with platform wheels enabled if the packaged files are absent. Unsupported platforms can use a system FFmpeg installation. No administrator access or PATH changes are needed for packaged tools.

**Missing model assets:** use `models install`, optionally with `--from-dir`. Setting `--models-dir` on setup alone does not change the default for later commands; use the same option or set `LOCAL_TRANSCRIPTION_MODELS`.

**Download interrupted:** retry `models install`. Partial downloads are resumed when the server confirms the byte range. A checksum mismatch removes the partial file and fails rather than installing it.

**Too many or too few speakers:** inspect the actual dialogue, supply a known count or reference samples if available, and keep uncertain labels unknown. Automatic labels are not evidence that another person spoke.

**Proofread outputs already exist:** they are protected. Preserve or intentionally remove that generated pair before applying a revised review. Originals and the canonical raw transcript are never rewritten by `apply-review`.

**Review rejected:** verify the canonical transcript hash, word IDs, exact expected text, and non-overlapping spans. A correction crossing speaker boundaries requires smaller edits or a justified speaker correction first.
