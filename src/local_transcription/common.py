"""Filesystem, timestamp, and transcript invariants."""

import hashlib
import json
import math
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stamp(seconds, srt=False):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}{',' if srt else '.'}{ms:03}"


def seconds(value):
    parts = str(value).split(":")
    if len(parts) > 3:
        raise ValueError("Time must be seconds, MM:SS, or HH:MM:SS.")
    result = 0.0
    for part in parts:
        result = result * 60 + float(part)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Time must be finite and nonnegative.")
    return result


def new_run(input_path, output=None):
    base = Path(output) if output else input_path.with_name(input_path.stem + ".transcription")
    base.parent.mkdir(parents=True, exist_ok=True)
    for index in range(10000):
        candidate = base if index == 0 else base.with_name(f"{base.name}-{index + 1}")
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        (candidate / "work").mkdir()
        return candidate.resolve()
    raise ValueError("Too many existing output folders.")


def validate_transcript(data):
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported transcript schema.")
    duration = data["duration"]
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("Invalid recording duration.")
    previous = 0.0
    seen = set()
    for word in data["words"]:
        if word["id"] in seen:
            raise ValueError("Duplicate word ID.")
        seen.add(word["id"])
        if not (previous <= word["start"] <= word["end"] <= duration):
            raise ValueError(f"Invalid or overlapping word timing: {word['id']}")
        if not word["text"].strip() or "\n" in word["text"] or "\r" in word["text"]:
            raise ValueError(f"Invalid word text: {word['id']}")
        previous = word["end"]
