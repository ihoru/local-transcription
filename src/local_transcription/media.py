"""Probe content rather than trusting file extensions; never invoke a shell."""

import json
from pathlib import Path
import shutil
import subprocess


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip()[-3000:] or f"{command[0]} failed.")
    return result.stdout


def require_ffmpeg():
    for name in ("ffmpeg", "ffprobe"):
        if not shutil.which(name):
            raise ValueError(f"Missing {name}. Install FFmpeg using your system package manager.")


def probe(path, audio_stream=None):
    require_ffmpeg()
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Input is not a file: {path}")
    info = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(path)]))
    audio = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    if not audio:
        raise ValueError("The input contains no audio stream.")
    if audio_stream is None:
        selected = next((s for s in audio if s.get("disposition", {}).get("default")), audio[0])
    else:
        selected = next((s for s in audio if s["index"] == audio_stream), None)
        if selected is None:
            raise ValueError(f"Audio stream {audio_stream} does not exist.")
    return dict(path=str(path), audio_stream=selected["index"],
                codec=selected.get("codec_name"),
                video=any(s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")
                          for s in info["streams"]),
                channels=selected.get("channels"), format=info.get("format", {}).get("format_name"))


EXTENSIONS = {"opus": ".opus", "vorbis": ".ogg", "aac": ".m4a", "alac": ".m4a",
              "mp3": ".mp3", "flac": ".flac", "pcm_s16le": ".wav",
              "pcm_s24le": ".wav", "pcm_s32le": ".wav", "pcm_f32le": ".wav"}


def convert(path, output_dir=None, audio_stream=None):
    info = probe(path, audio_stream)
    source = Path(info["path"])
    folder = Path(output_dir).resolve() if output_dir else source.parent
    folder.mkdir(parents=True, exist_ok=True)
    extension = EXTENSIONS.get(info["codec"], ".flac")
    copy = info["codec"] in EXTENSIONS
    for index in range(10000):
        suffix = "" if index == 0 else f"-{index + 1}"
        target = folder / f"{source.stem}.audio{suffix}{extension}"
        try:
            # Reserve a unique path; FFmpeg may overwrite only this owned empty file.
            with target.open("xb"):
                pass
        except FileExistsError:
            continue
        try:
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(source), "-map",
                 f"0:{info['audio_stream']}", "-vn", "-c:a", "copy" if copy else "flac", str(target)])
        except ValueError:
            target.unlink(missing_ok=True)
            if copy:
                copy = False
                extension = ".flac"
                continue
            raise
        return target, info
    raise ValueError("Too many audio output collisions.")


def decode(path, target, stream):
    run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(path), "-map", f"0:{stream}",
         "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(target)])
