# Validation and observed limitations

Validated on 2026-09-04 on Linux, Python 3.13, CPU int8 recognition. No usable CUDA device was detected. Model assets passed SHA-256 verification.

## Automated checks

35 tests pass. They cover content-based media detection with misleading extensions and Unicode paths, video extraction, audio-only input, missing audio, FLAC fallback, output collisions, disabled diarization, stable speaker numbering, competing voice assignments, local model loading, verified model import, and native runtime availability.

Review tests exercise repeated phrases, edits spanning subtitle boundaries, missing negations, substantive replacements, empty reviewed edits, invalid or overlapping edits, stale canonical hashes, original-file preservation, unknown-speaker sentence continuity, and protection of real replies. Saved TXT/SRT speech is compared independently of layout; edited cues are checked for balanced braces.

Ruff checks and skill frontmatter validation pass. A clean locked environment exposed a missing Sherpa native runtime dependency; `sherpa-onnx-core` is now explicit in the dependency manifest and the doctor checks that its native bindings load.

A final smoke run used the installed repository environment and default model cache, transcribed the full synthetic audio with diarization disabled, reviewed the complete text, and successfully produced all four outputs. The clean installation therefore exercised actual recognition and review, not only imports or mocked tests.

## Packaged installation

The release wheel was installed into a fresh uv tool environment with runtime constraints exported from the lockfile, without an editable install or source checkout on the import path. From outside the repository, its doctor verified the default models and native dependencies, and the CLI completed recognition and review of the full synthetic audio, producing all four files. The standalone skill archive passed validation and every referenced guide was present. Release checksums cover the wheel, constraints, and skill archive. CI also builds and installs the wheel.

## Packaged FFmpeg validation (0.1.2)

With PATH empty and network requests rejected by the test, the actual dependency binaries successfully generated and probed a video, detected its format after a Unicode rename without an extension, extracted its audio, decoded mono 16 kHz PCM, and passed the CLI doctor. The source recording remained unchanged. Separate tests verify system-tool precedence and an actionable error for unsupported or incomplete installations. CI no longer installs FFmpeg with the system package manager. Linux x86-64 is verified; other upstream wheel platforms are documented but have not been exercised locally.

## Skill workflow evaluations

The following three requests were each executed with the skill and with a baseline agent using CLI documentation:

| Case | Required behavior | Result |
|---|---|---|
| Video, no summary | Extract audio, default speaker detection, all four transcript files, no summary | Passed in both runs |
| Audio, speakers disabled, summary requested | Omit speaker labels, all four files, create a practical summary | Passed in both runs |
| Audio, summary preference unspecified | Complete all four files, then offer a summary without creating one | Passed in both runs |

Each run used the complete short English synthetic fixture, read its full transcript, and verified its outputs. The recognized 26-word text was coherent, so empty reviews were appropriate. These cases validate workflow and restraint, not the ability to recover badly recognized natural speech. Nonempty corrections are covered by the automated tests. Both configurations passed all applicable checks, so these small fixtures do not establish a quality advantage for the skill. Timings were concurrent and are not an isolated speed benchmark; agent token use was unavailable.

Generate equivalent fixtures outside the checkout with `python tests/create_speech_fixture.py /path/to/empty/folder` (requires `espeak` and FFmpeg). The three prompts are versioned in the skill's `evals/evals.json`. Local reports, generated media, and the comparison viewer remain outside Git.

## Real dialogue: automatic versus reference-assisted detection

A local seven-minute excerpt was checked with a known single-speaker first five minutes and a second speaker entering around 05:58. The recording itself, reference samples, and detailed results are not committed.

- **Automatic mode:** assigned three clusters within the known single-speaker opening, so it over-split one voice. The second speaker's 05:58–06:10 sample was mainly assigned to another cluster, with a small erroneous assignment to an opening cluster.
- **Reference-assisted mode:** assigned 284 seconds of the first five minutes to the primary reference and 2.5 seconds to the other reference; remaining windows were unassigned. All 12 seconds of the second-speaker sample matched the second reference. This mode did not hard-code the opening as one speaker.

These are diagnostic interval totals, including windows that can contain silence; they are not a formal diarization error rate. Reference matching improved this example but still produced mistakes. Neither approach establishes verified identity or perfect speaker separation. Use known counts or reference samples when available and review uncertain assignments.

The optional `tests/manual_speech.py` checker accepts a local mono 16 kHz WAV, model directory, reference JSON, output JSON, and explicit `--single-interval START END` / `--other-interval START END` expectations. It never makes those interval assumptions in the production pipeline.

## Remaining boundaries

- Language detection and Whisper recognition can miss words or repeat plausible errors, particularly with noise, overlap, or weak audio. Rechecks are evidence for editorial review, not guarantees.
- Replacement phrases inherit approximate timing from the original span. The tool does not perform a second forced-alignment pass on edited text.
- Speaker detection is diarization, not audio-source separation; simultaneous speech remains difficult.
- Proofreading depends on the invoking agent reading all source text and making restrained edits. It is not performed by a local generative language model.
- The full previous 92-minute recording was not rerun as a packaging test. The original full-run artifacts were preserved; new functionality was exercised using bounded local speech checks and synthetic workflow fixtures.

## Native macOS release checks (0.1.4)

The macOS binary dependency in 0.1.2 was mislabeled upstream: its universal2 wheel contained x86_64-only executables. Version 0.1.4 replaces it on macOS with native arm64 and x86_64 wheels built from pinned FFmpeg source. CI now exercises installed wheels on both native Mac architectures and Linux, including an empty-PATH media round trip, AAC/Opus decoding, Mach-O architecture and dynamic-link checks, real executable startup in doctor, CPU int8 availability, and Sherpa native imports. Before publication, both Mac jobs also run large-v3 recognition and automatic diarization on a short generated recording and produce all four transcript files. The full recording and natural-dialogue speaker-quality evaluations above remain Linux evaluations; short generated fixtures do not establish Mac transcription quality or speed on arbitrary recordings.

Fresh model setup in the 0.1.3 release candidate found a 404 in the WeSpeaker download URL. The corrected upstream LM asset in 0.1.4 was downloaded and matched the original trusted checksum byte for byte, so existing model files remain reusable. The failed candidate was withheld from PyPI.
