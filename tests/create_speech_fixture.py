"""Generate optional synthetic skill-evaluation media outside the repository."""

import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    audio = args.output / "voice.wav"
    video = args.output / "video.mkv"
    if audio.exists() or video.exists():
        parser.error("Fixture outputs already exist; choose an empty folder.")
    text = ("We need clear priorities and a simple plan. First, identify the customer problem. "
            "Then assign an owner and agree on the deadline. Review the results together.")
    subprocess.run(["espeak", "-v", "en-us", "-s", "145", "-w", str(audio), text], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", "color=blue:s=64x64:r=5",
                    "-i", str(audio), "-shortest", "-c:v", "ffv1", "-c:a", "flac", str(video)], check=True)


if __name__ == "__main__":
    main()
