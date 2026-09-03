# Review schema and editorial policy

The agent reads the entire transcript before finalizing a review. Improve substantive recognition errors, not the speaker's style. Preserve repetitions, colloquialisms, ordinary grammatical slips, punctuation, and capitalization unless they are part of the error being corrected. Do not fact-check a speaker's statement into different words they did not say.

Use a local `recheck` for unclear passages, preferably including adjacent context. A second recognition can corroborate a recovery but can also repeat the same mistake. If recovery is unsupported, replace only the damaged span with `unintelligible`. The renderer adds braces.

## Text corrections

Copy `work/review.template.json` and populate it:

```json
{
  "schema_version": 1,
  "transcript_sha256": "copy-the-hash-from-the-template",
  "edits": [
    {
      "start_word": "w000012",
      "end_word": "w000014",
      "expected_text": "do escalate tensions",
      "replacement": "do not escalate tensions",
      "reason": "The surrounding sentence and local recheck support the missing negation."
    }
  ],
  "speaker_edits": []
}
```

Word IDs are inclusive. `expected_text` is exactly the selected original words joined by single spaces. It is not a search expression or a global replacement. `replacement` contains no braces or newlines; the renderer marks modified words or the replacement phrase. Supply a nonempty replacement; represent unrecoverable speech as `unintelligible` rather than silently deleting it.

Each edit needs a short reason. Corrections may not overlap. Do not place the same word in several separate edits; combine its corrections into one. Use separate edits for separate passages even when the original text repeats. The canonical hash ties the review to one exact run.

Pure insertions and removals within a replacement are represented by a marked phrase anchored to the original span, so the change stays visible and has real timing. For omitted speech between recognized words, include an adjacent recognized word in the replacement span and use its source interval as an approximate timing anchor. If timing matters, consult the local recheck timestamps; do not describe generated internal word timing as exact alignment.

## Speaker corrections and sentence continuity

```json
{
  "start_word": "w000020",
  "end_word": "w000021",
  "expected_speakers": [null, null],
  "speaker": "Speaker 2",
  "reason": "This unfinished phrase directly continues the next sentence by Speaker 2."
}
```

Put these objects in `speaker_edits`. `expected_speakers` contains one original assignment per word, including nulls. The replacement label must already exist in the transcript, or be null. The renderer marks changed speaker metadata with braces. When diarization is disabled, speaker edits are invalid.

Use context to reconnect an incomplete sentence split by an unknown assignment, or a clearly spurious short label. Do not merge a reply, interruption, or overlap merely because doing so would produce a smoother paragraph. If speaker identity is uncertain, keep it unknown.

## Completion checks

Run `apply-review RUN EDITS.json`, then inspect the outputs and `work/review.validation.json`. Confirm that the original file hashes are unchanged, both proofread files carry the same corrections, timestamps remain chronological, and braces are balanced in each cue. Read the edited passages in context; syntactic validation cannot establish that a guessed phrase was actually spoken.

A summary is a separate artifact with a separate confirmation step. It may compress and reorganize the dialogue, but must identify synthesized examples and preserve the difference between decisions and unfinished alternatives.
