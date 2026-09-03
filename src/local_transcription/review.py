"""Validated, instance-specific edits. No recording-specific replacements."""

import copy
import difflib

from .common import read_json, save_json, sha256, validate_transcript
from .render import render


def span_indices(change, indices):
    try:
        first, last = indices[change["start_word"]], indices[change["end_word"]]
    except KeyError as exc:
        raise ValueError(f"Missing or unknown word ID: {exc}") from None
    if first > last:
        raise ValueError("Review span is reversed.")
    return first, last


def reviewed_units(data, review):
    validate_transcript(data)
    if review.get("schema_version") != 1:
        raise ValueError("Unsupported review schema.")
    words = copy.deepcopy(data["words"])
    indices = {w["id"]: i for i, w in enumerate(words)}
    occupied = set()
    for assignment in review.get("speaker_edits", []):
        if not data["diarization"]:
            raise ValueError("Speaker edits require diarization.")
        first, last = span_indices(assignment, indices)
        if occupied.intersection(range(first, last + 1)):
            raise ValueError("Overlapping speaker edits.")
        occupied.update(range(first, last + 1))
        if not assignment.get("reason", "").strip():
            raise ValueError("Speaker edits need a reason.")
        expected = assignment.get("expected_speakers")
        if expected != [w["speaker"] for w in words[first:last + 1]]:
            raise ValueError("Speaker edit does not match original assignments.")
        speaker = assignment.get("speaker")
        if speaker is not None and speaker not in {w["speaker"] for w in data["words"]}:
            raise ValueError("Speaker edits must refer to an existing speaker or null.")
        for word in words[first:last + 1]:
            if word["speaker"] != speaker:
                word["speaker_changed"] = True
            word["speaker"] = speaker
    replacements = []
    for change in review.get("edits", []):
        first, last = span_indices(change, indices)
        expected = " ".join(w["text"] for w in words[first:last + 1])
        if change.get("expected_text") != expected:
            raise ValueError(f"Original text mismatch at {change['start_word']}.")
        text = change.get("replacement")
        if not isinstance(text, str) or not text.strip() or any(c in text for c in "{}\n\r"):
            raise ValueError("Replacement must be nonempty text without braces or newlines.")
        if not change.get("reason", "").strip():
            raise ValueError("Each correction needs a reason.")
        if len({w["speaker"] for w in words[first:last + 1]}) > 1:
            raise ValueError("Correction crosses speakers; split it or review speaker assignments first.")
        replacements.append((first, last, text.strip()))
    replacements.sort()
    for a, b in zip(replacements, replacements[1:]):
        if a[1] >= b[0]:
            raise ValueError("Overlapping text corrections.")
    output = []
    cursor = 0
    for first, last, replacement in replacements:
        output.extend(words[cursor:first])
        source = words[first:last + 1]
        old_tokens = [w["text"] for w in source]
        new_tokens = replacement.split()
        opcodes = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False).get_opcodes()
        if any(tag in ("insert", "delete") for tag, *_ in opcodes):
            # A phrase replacement keeps added/removed words visibly marked and
            # borrows a real source span instead of creating zero-duration cues.
            output.append(dict(source[0], text=replacement, start=source[0]["start"],
                               end=source[-1]["end"], changed=True,
                               speaker_changed=any(w.get("speaker_changed") for w in source)))
            cursor = last + 1
            continue
        for tag, a, b, c, d in opcodes:
            if tag == "equal":
                output.extend(source[a:b])
            else:
                region = source[a:b]
                start, end, anchor = region[0]["start"], region[-1]["end"], region[0]
                output.append(dict(anchor, text=" ".join(new_tokens[c:d]), start=start, end=end, changed=True,
                                   speaker_changed=any(w.get("speaker_changed") for w in (region or [anchor]))))
        cursor = last + 1
    output.extend(words[cursor:])
    # A marked phrase is an indivisible timed unit, so a subtitle never contains
    # half an edit or unbalanced braces. Long replacements should be scoped narrowly.
    return output


def apply_review(run, review_path):
    data_path = run / "work/transcript.json"
    data, review = read_json(data_path), read_json(review_path)
    if review.get("transcript_sha256") != sha256(data_path):
        raise ValueError("Review belongs to a different transcript; check transcript_sha256.")
    units = reviewed_units(data, review)
    txt, srt = render(data, units, proofread=True)
    for name in (data["stem"] + ".txt", data["stem"] + ".srt"):
        expected = data.get("original_hashes", {}).get(name)
        if expected and sha256(run / name) != expected:
            raise ValueError(f"Original output changed: {name}")
    targets = [run / (data["stem"] + suffix) for suffix in (".proofread.txt", ".proofread.srt")]
    if any(p.exists() for p in targets):
        raise ValueError("Proofread outputs already exist. Preserve them before applying another review.")
    for path, content in zip(targets, (txt, srt)):
        path.write_text(content, encoding="utf-8")
    save_json(run / "work/review.applied.json", review)
    save_json(run / "work/review.validation.json", dict(
        corrections=len(review.get("edits", [])), speaker_edits=len(review.get("speaker_edits", [])),
        matching_text=True, originals_preserved=True))
    manifest = read_json(run / "work/run.json")
    manifest["status"] = "reviewed"
    save_json(run / "work/run.json", manifest)
    return targets
