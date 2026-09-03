import copy
import hashlib
import re

import pytest

from local_transcription.common import save_json, sha256
from local_transcription.render import render
from local_transcription.review import apply_review, reviewed_units


def transcript(text="We escalate tensions. We escalate tensions."):
    words = [dict(id=f"w{i+1:06}", text=t, start=i*2.0, end=i*2.0+1,
                  speaker="Speaker 1", paragraph=i//3)
             for i, t in enumerate(text.split())]
    return dict(schema_version=1, title="Example", stem="Example", language="en",
                duration=words[-1]["end"], diarization=True, words=words)


def edit(data, first, last, replacement):
    return dict(start_word=data["words"][first]["id"], end_word=data["words"][last]["id"],
                expected_text=" ".join(w["text"] for w in data["words"][first:last+1]),
                replacement=replacement, reason="Verified contextual recognition error.")


def review(edits=None, speaker_edits=None):
    return dict(schema_version=1, edits=edits or [], speaker_edits=speaker_edits or [])


def test_repeated_phrase_only_targeted_occurrence_changes():
    data = transcript()
    units = reviewed_units(data, review([edit(data, 3, 5, "We do not escalate tensions.")]))
    txt, srt = render(data, units, True)
    assert "We escalate tensions." in txt
    assert "{We do not escalate tensions.}" in txt
    assert "{We do not escalate tensions.}" in srt
    assert data["words"][3]["text"] == "We"


def test_cross_cue_replacement_is_balanced_and_bounded():
    data = transcript("Please do escalate these unnecessary tensions now.")
    units = reviewed_units(data, review([edit(data, 1, 5, "do not escalate these tensions")]))
    _, srt = render(data, units, True)
    for cue in srt.strip().split("\n\n"):
        assert cue.count("{") == cue.count("}")
    assert "{do not escalate these tensions}" in srt
    assert all(0 <= u["start"] <= u["end"] <= data["duration"] for u in units)


@pytest.mark.parametrize("change", ["wrong_text", "overlap", "unknown_id", "reversed", "empty", "braces", "no_reason"])
def test_invalid_review_rejected(change):
    data = transcript()
    value = edit(data, 0, 2, "We reduce tensions.")
    edits = [value]
    if change == "wrong_text":
        value["expected_text"] = "wrong"
    elif change == "overlap":
        edits.append(copy.deepcopy(value))
    elif change == "unknown_id":
        value["start_word"] = "w999999"
    elif change == "reversed":
        value["start_word"], value["end_word"] = value["end_word"], value["start_word"]
    elif change == "empty":
        value["replacement"] = ""
    elif change == "braces":
        value["replacement"] = "{text}"
    else:
        value["reason"] = ""
    with pytest.raises(ValueError):
        reviewed_units(data, review(edits))


def test_unknown_fragment_can_join_without_merging_a_real_reply():
    data = transcript("I am waiting for your version. Thank you.")
    for i, w in enumerate(data["words"]):
        w.update(start=i*.3, end=(i+1)*.3, paragraph=i,
                 speaker=None if i < 2 else "Speaker 1" if i < 6 else "Speaker 2")
    assignment = dict(start_word="w000001", end_word="w000002", expected_speakers=[None, None],
                      speaker="Speaker 1", reason="Continuation of the same sentence.")
    units = reviewed_units(data, review(speaker_edits=[assignment]))
    txt, _ = render(data, units, True)
    assert "I am waiting for your version." in txt
    assert "{Speaker 1}:" in txt
    assert "Speaker 2:\nThank you." in txt


def test_correction_cannot_cross_unreviewed_speaker_boundary():
    data = transcript()
    data["words"][1]["speaker"] = "Speaker 2"
    with pytest.raises(ValueError, match="crosses speakers"):
        reviewed_units(data, review([edit(data, 0, 2, "We reduce tensions.")]))


def test_disabled_speakers_omit_labels():
    data = transcript()
    data["diarization"] = False
    for w in data["words"]:
        w["speaker"] = None
    for output in render(data):
        assert "Speaker" not in output and "Unknown speaker" not in output


def test_apply_review_preserves_originals_and_rejects_stale_or_existing_outputs(tmp_path):
    data = transcript()
    originals = {}
    for suffix, text in zip((".txt", ".srt"), render(data)):
        path = tmp_path / (data["stem"]+suffix)
        path.write_text(text)
        originals[path.name] = sha256(path)
    data["original_hashes"] = originals
    save_json(tmp_path / "work/transcript.json", data)
    save_json(tmp_path / "work/run.json", {"status": "awaiting_review"})
    value = review([edit(data, 0, 2, "We reduce tensions.")])
    value["transcript_sha256"] = "wrong"
    edits_path = tmp_path / "edits.json"
    save_json(edits_path, value)
    with pytest.raises(ValueError, match="different transcript"):
        apply_review(tmp_path, edits_path)
    assert not (tmp_path / "Example.proofread.txt").exists()
    value["transcript_sha256"] = sha256(tmp_path / "work/transcript.json")
    save_json(edits_path, value)
    outputs = apply_review(tmp_path, edits_path)
    assert all(path.exists() for path in outputs)
    assert all(sha256(tmp_path/name) == digest for name, digest in originals.items())
    with pytest.raises(ValueError, match="already exist"):
        apply_review(tmp_path, edits_path)


def test_empty_review_creates_equivalent_speech():
    data = transcript()
    units = reviewed_units(data, review())
    assert [u["text"] for u in units] == [w["text"] for w in data["words"]]


def test_changed_original_aborts_before_proofread_output(tmp_path):
    data = transcript()
    data["original_hashes"] = {"Example.txt": hashlib.sha256(b"original").hexdigest()}
    (tmp_path / "Example.txt").write_text("changed")
    save_json(tmp_path / "work/transcript.json", data)
    value = review()
    value["transcript_sha256"] = sha256(tmp_path / "work/transcript.json")
    save_json(tmp_path / "edits.json", value)
    with pytest.raises(ValueError, match="Original output changed"):
        apply_review(tmp_path, tmp_path / "edits.json")
    assert not list(tmp_path.glob("*.proofread.*"))


def test_saved_txt_and_srt_have_same_speech(tmp_path):
    data = transcript()
    units = reviewed_units(data, review([edit(data, 0, 2, "We do not escalate tensions.")]))
    txt, srt = render(data, units, True)
    txt_speech = re.findall(r"^\[.*\].*:\n([^\n]+)", txt, re.M)
    srt_speech = [c.splitlines()[2].split(": ", 1)[1] for c in srt.strip().split("\n\n")]
    def normalize(values):
        return re.sub(r"\s+", "", "".join(values))
    assert normalize(txt_speech) == normalize(srt_speech)
