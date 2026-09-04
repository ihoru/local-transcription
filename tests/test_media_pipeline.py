import numpy as np
import pytest

from local_transcription import inference, media, pipeline
from local_transcription.cli import parser, main
from local_transcription.common import new_run, read_json, seconds, validate_transcript


@pytest.fixture
def audio(tmp_path):
    target = tmp_path / "example.wav"
    media.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=400:duration=1",
                    "-ar", "16000", str(target)])
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
    media.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=32x32:d=1",
                    "-i", str(audio), "-c:v", "ffv1", "-c:a", "flac", "-shortest", str(target)])
    renamed = target.with_suffix(".data")
    target.rename(renamed)
    assert media.probe(renamed)["video"]
    converted, _ = media.convert(renamed)
    assert converted.suffix == ".flac"
    assert not media.probe(converted)["video"]


def test_video_without_audio_is_clear_error(tmp_path):
    target = tmp_path / "silent.mkv"
    media.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=32x32:d=1",
                    "-c:v", "ffv1", str(target)])
    with pytest.raises(ValueError, match="no audio stream"):
        media.probe(target)


def test_unsupported_copy_codec_falls_back_to_flac(tmp_path, audio):
    target = tmp_path / "voice.wav"
    media.run(["ffmpeg", "-v", "error", "-i", str(audio), "-c:a", "pcm_mulaw", str(target)])
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


@pytest.mark.parametrize('name', ['ffmpeg', 'ffprobe'])
def test_system_media_tool_takes_precedence(name, monkeypatch):
    monkeypatch.setattr(media.shutil, 'which', lambda requested: '/system/' + requested)
    monkeypatch.setattr(media, '_bundled_paths', lambda: pytest.fail('System tool was ignored'))
    assert media.executable(name) == '/system/' + name


def test_packaged_tools_handle_video_and_doctor_with_empty_path(tmp_path, monkeypatch, capsys):
    import json
    import socket
    import soundfile as sf

    monkeypatch.setenv('PATH', '')
    monkeypatch.setattr(socket.socket, 'connect',
                        lambda *a, **k: pytest.fail('Media processing tried to download a binary'))
    assert media.shutil.which('ffmpeg') is None
    assert media.shutil.which('ffprobe') is None
    assert all(media.executable(name) for name in ('ffmpeg', 'ffprobe'))
    video = tmp_path / 'video.mkv'
    media.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
               'color=blue:s=32x32:d=1', '-f', 'lavfi', '-i',
               'sine=frequency=400:duration=1', '-c:v', 'ffv1', '-c:a', 'flac',
               '-shortest', str(video)])
    disguised = video.with_name('Запись без расширения')
    video.rename(disguised)
    original = disguised.read_bytes()
    info = media.probe(disguised)
    assert info['video'] and info['codec'] == 'flac'
    extracted, _ = media.convert(disguised)
    assert media.probe(extracted)['codec'] == 'flac'
    decoded = tmp_path / 'decoded.wav'
    media.decode(disguised, decoded, info['audio_stream'])
    assert sf.info(decoded).samplerate == 16000
    assert sf.info(decoded).channels == 1
    assert disguised.read_bytes() == original
    monkeypatch.setattr(pipeline.models, 'check', lambda *a, **k: [])
    assert main(['doctor']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['ffmpeg'] == media.executable('ffmpeg')
    assert report['ffprobe'] == media.executable('ffprobe')
    assert report['errors'] == []


def test_missing_packaged_binary_has_actionable_error(monkeypatch):
    monkeypatch.setattr(media.shutil, 'which', lambda name: None)
    monkeypatch.setattr(media, '_bundled_paths', lambda: (None, None))
    with pytest.raises(ValueError, match='platform wheels'):
        media.executable('ffmpeg')


@pytest.mark.parametrize('codec,extension', [('aac', '.m4a'), ('opus', '.opus')])
def test_packaged_tools_decode_common_recording_codecs(tmp_path, monkeypatch, codec, extension):
    import soundfile as sf
    monkeypatch.setenv('PATH', '')
    source = tmp_path / ('Voice memo' + extension)
    media.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
               'sine=frequency=440:duration=1', '-ar', '48000', '-c:a', codec,
               '-strict', '-2', str(source)])
    info = media.probe(source)
    assert info['codec'] == codec
    output = tmp_path / 'decoded.wav'
    media.decode(source, output, info['audio_stream'])
    decoded, rate = sf.read(output)
    assert rate == 16000 and .9 < len(decoded) / rate < 1.1
    assert np.max(np.abs(decoded)) > .01


def test_doctor_rejects_an_executable_that_cannot_run(monkeypatch, capsys):
    import json
    monkeypatch.setattr(pipeline.models, 'check', lambda *a, **k: [])
    monkeypatch.setattr(media, 'executable', lambda name: '/broken/' + name)
    assert main(['doctor']) == 1
    errors = json.loads(capsys.readouterr().out)['errors']
    assert len(errors) == 2 and all('/broken/' in error for error in errors)
