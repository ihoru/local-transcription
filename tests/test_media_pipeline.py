import subprocess

import numpy as np
import pytest

from local_transcription import inference, media, pipeline
from local_transcription.cli import parser, main
from local_transcription.common import new_run, read_json, seconds, validate_transcript


@pytest.fixture
def audio(tmp_path):
    target = tmp_path / "example.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=400:duration=1",
                    "-ar", "16000", str(target)], check=True)
    return target


def test_audio_detection_ignores_extension_and_preserves_input(audio):
    renamed = audio.with_name("Пример input.bin")
    audio.rename(renamed)
    original = renamed.read_bytes()
    info = media.probe(renamed)
    assert not info["video"] and info["codec"] == "pcm_s16le"
    first, _ = media.convert(renamed)
    second, _ = media.convert(renamed)
    assert first != second and first.exists() and second.exists()
    assert renamed.read_bytes() == original
    assert media.probe(first)["codec"] == "pcm_s16le"


def test_video_with_audio_detected_and_copied(tmp_path, audio):
    target = tmp_path / "movie.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=32x32:d=1",
                    "-i", str(audio), "-c:v", "ffv1", "-c:a", "flac", "-shortest", str(target)], check=True)
    renamed = target.with_suffix(".data")
    target.rename(renamed)
    assert media.probe(renamed)["video"]
    converted, _ = media.convert(renamed)
    assert converted.suffix == ".flac"
    assert not media.probe(converted)["video"]


def test_video_without_audio_is_clear_error(tmp_path):
    target = tmp_path / "silent.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=32x32:d=1",
                    "-c:v", "ffv1", str(target)], check=True)
    with pytest.raises(ValueError, match="no audio stream"):
        media.probe(target)


def test_unsupported_copy_codec_falls_back_to_flac(tmp_path, audio):
    target = tmp_path / "voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-c:a", "pcm_mulaw", str(target)], check=True)
    converted, _ = media.convert(target)
    assert converted.suffix == ".flac" and media.probe(converted)["codec"] == "flac"


def test_run_collision_preserves_existing_files(tmp_path):
    requested = tmp_path / "output"
    requested.mkdir()
    marker = requested / "keep.txt"
    marker.write_text("keep")
    new = new_run(tmp_path / "input.wav", requested)
    assert new == tmp_path / "output-2"
    assert marker.read_text() == "keep"


@pytest.mark.parametrize("diarization", [True, False])
def test_pipeline_outputs_and_disabled_detection(audio, monkeypatch, diarization):
    monkeypatch.setattr(pipeline.models, "check", lambda *a, **k: [])
    monkeypatch.setattr(pipeline.inference, "recognize", lambda *a, **k: dict(language="en", segments=[dict(words=[
        dict(word=" Hello", start=.1, end=.4, probability=.9),
        dict(word=" world.", start=.4, end=.8, probability=.9)])]))
    calls = []
    monkeypatch.setattr(pipeline.inference, "automatic_turns", lambda *a: calls.append(True) or [dict(start=0,end=1,speaker=9)])
    arguments = ["transcribe", str(audio)] + ([] if diarization else ["--no-diarization"])
    run = pipeline.transcribe(parser().parse_args(arguments))
    assert bool(calls) == diarization
    manifest = read_json(run / "work/run.json")
    assert manifest["status"] == "awaiting_review"
    assert (run / "example.txt").exists() and (run / "example.srt").exists()
    assert (run / "work/review.template.json").exists()
    assert not list(run.glob("*.proofread.*"))
    assert not list(run.glob("*.summary.md"))
    if not diarization:
        assert "Speaker" not in (run / "example.txt").read_text()


def test_speaker_assignment_renumbers_by_first_voice_and_leaves_overlap_unknown():
    words = [dict(start=0,end=1), dict(start=1,end=2), dict(start=2,end=4)]
    turns = [dict(start=0,end=1,speaker=8), dict(start=1,end=4,speaker=3), dict(start=2,end=4,speaker=8)]
    inference.assign_speakers(words, turns, np.ones(4*16000,dtype=np.float32))
    assert [w["speaker"] for w in words] == ["Speaker 1", "Speaker 2", None]


def test_canonical_timing_is_bounded():
    recognition = dict(segments=[dict(words=[dict(word=" hi",start=0,end=1),dict(word=" there",start=.8,end=2)])])
    words = inference.make_words(recognition, 1.8)
    validate_transcript(dict(schema_version=1,duration=1.8,words=words))
    assert words[1]["start"] == 1 and words[1]["end"] == 1.8


def test_cli_rejects_conflicting_speaker_options():
    with pytest.raises(SystemExit):
        main(["transcribe", "any.wav", "--no-diarization", "--speakers", "2"])


def test_seconds_accepts_timestamps_and_rejects_nonfinite():
    assert seconds("01:02:03.5") == 3723.5
    for value in ("nan", "inf", "-1", "1:2:3:4"):
        with pytest.raises(ValueError):
            seconds(value)
