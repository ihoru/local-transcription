# Architecture

The package separates media handling, explicit model setup, speech inference, review validation, and rendering. The skill is the agent-facing workflow; it invokes the package rather than carrying its own processing scripts.

```text
local media -> FFprobe -> optional audio extraction -> mono PCM
    -> Whisper large-v3 -> timed words
    -> optional speaker analysis -> canonical transcript
    -> raw TXT + raw SRT + review handoff
    -> agent reads all text and proposes span edits
    -> validated review -> proofread TXT + proofread SRT
    -> user-confirmed Markdown summary
```

## Offline boundary

`models install` is the only package command that requests model downloads. It verifies pinned SHA-256 hashes and can reuse already downloaded assets. Dependency installation is a separate `uv sync` operation.

Whisper is loaded by absolute local path with `local_files_only=True`; Hugging Face offline mode and telemetry disabling are set before model loading. Speaker models load from explicit ONNX paths. No audio is uploaded. The invoking agent reads transcript text for proofreading and optional summarization; that text may be processed by the agent's provider. The package does not contain a hosted proofreading integration or a local generative language model.

## Canonical data

`work/transcript.json` has schema version 1, duration, language, title/stem, diarization status, output hashes, and an ordered `words` array. Each word has an immutable ID, original recognized text, start/end seconds, original paragraph group, probability, and a speaker label or null. The raw recognition with its original model timing is preserved separately. Canonical timing clamps any model overlap to the previous word's end, within recording bounds.

`work/review-source.txt` exposes word IDs and times for the agent. `work/review.template.json` carries the canonical file hash. An empty review is valid after an actual editorial pass; creating an empty review without reading the recording's text is not completion of the skill.

Review transformations generate new timed units in memory. Both proofread renderers consume those units. Original words and files stay unchanged. Text edits require exact expected content and cannot span multiple speakers unless the agent first provides justified speaker corrections. Reviews fail before output creation when validation fails.

## Rendering

TXT keeps original paragraph groups and joins incomplete sentences across short gaps when the speaker agrees. The agent can correct supported unknown-speaker assignments to allow fragmented sentences to join. Rendering alone does not guess a person's identity from capitalization.

SRT normally groups up to seven seconds and roughly 100 characters. A marked replacement phrase is kept together so its braces remain balanced; its timing comes from the replaced passage. Keep edits narrowly scoped. These subtitles are human-readable review artifacts, not broadcast-spec caption mastering.

The renderer verifies that both views contain the same spoken text and correction markers, ignoring whitespace. Ordinary speaker labels and timestamp syntax are presentation metadata.

## Repository boundaries

Source code, the canonical skill, documentation, lockfile, and synthetic tests are versioned. Media, model weights, local environments, transcripts, reviews, and evaluation outputs stay outside Git. Previous one-off experiments remain historical local artifacts; their fixed file paths, speaker samples, and handwritten corrections are not runtime defaults.
