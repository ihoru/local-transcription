"""Release-only real model smoke test using generated speech, never user recordings."""

import os
from pathlib import Path
import re
import subprocess
import sys

from local_transcription import media, pipeline, review
from local_transcription.cli import parser
from local_transcription.common import read_json, sha256


def check(folder):
    folder.mkdir(parents=True, exist_ok=False)
    source = folder / "speech.aiff"
    spoken = (
        "Hello. This recording checks local speech recognition on a Mac. "
        "Please write down the words and keep the original recording. "
        "We are testing the audio tools and speaker detection together. "
        "The meeting begins tomorrow morning. Thank you for listening."
    )
    subprocess.run(["/usr/bin/say", "-o", str(source), spoken], check=True)
    # Conversion and model inference must work without tools installed by the runner.
    os.environ["PATH"] = ""
    video = folder / "Meeting.mkv"
    media.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=blue:s=32x32",
               "-i", str(source), "-c:v", "ffv1", "-c:a", "flac", "-shortest", str(video)])
    original = sha256(video)
    args = parser().parse_args(["transcribe", str(video), "--language", "en",
                               "--threads", "2", "--batch-size", "1"])
    run = pipeline.transcribe(args)
    data = read_json(run / "work/transcript.json")
    text = " ".join(w["text"] for w in data["words"])
    expected = set(re.findall(r"[a-z]+", spoken.lower()))
    actual = set(re.findall(r"[a-z]+", text.lower()))
    assert len(expected & actual) / len(expected) >= .7, text
    turns = read_json(run / "work/speakers.json")
    assert turns["method"] == "automatic" and turns["turns"]
    assert any(w["speaker"] for w in data["words"])
    review.apply_review(run, run / "work/review.template.json")
    for suffix in (".txt", ".srt", ".proofread.txt", ".proofread.srt"):
        assert (run / (video.stem + suffix)).stat().st_size > 0
    assert sha256(video) == original
    print(f"Real large-v3 CPU int8 + automatic diarization passed: {len(data['words'])} words.")


if __name__ == "__main__":
    check(Path(sys.argv[1]).resolve())
