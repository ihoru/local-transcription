"""Explicit, checksum-verified setup. Inference never downloads models."""

import os
from pathlib import Path
import shutil
import tarfile
import urllib.request

from .common import sha256

REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"
WHISPER_URL = f"https://huggingface.co/Systran/faster-whisper-large-v3/resolve/{REVISION}/"
SEGMENT_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/"
               "speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2")
EMBEDDING_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/"
                 "speaker-recongition-models/wespeaker-voxceleb-resnet34.onnx")
WHISPER_HASHES = {
    "model.bin": "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1",
    "config.json": "a9306624f5ec14270a014b647e5c316b6e03a662c369758d1b90697a7b0655b9",
    "preprocessor_config.json": "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711",
    "tokenizer.json": "6d8cbd7cd0d8d5815e478dac67b85a26bbe77c1f5e0c6d76d1ce2abc0e5f21ca",
    "vocabulary.json": "c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1",
}
SEGMENT = "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
EMBEDDING = "wespeaker-voxceleb-resnet34.onnx"
HASHES = {**{f"whisper-large-v3/{n}": h for n, h in WHISPER_HASHES.items()},
          SEGMENT: "220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079",
          EMBEDDING: "e9848563da86f263117134dfd7ad63c92355b37de492b55e325400c9d9c39012"}
ARCHIVE_HASH = "24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488"


def model_dir(value=None):
    default = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "local-transcription/models"
    return Path(value or os.environ.get("LOCAL_TRANSCRIPTION_MODELS", default)).expanduser().resolve()


def check(root, diarization=True, verify=False):
    errors = []
    for name, digest in HASHES.items():
        if not diarization and not name.startswith("whisper-large-v3/"):
            continue
        path = root / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Missing model asset: {name}")
        elif verify and sha256(path) != digest:
            errors.append(f"Checksum mismatch: {name}")
    return errors


def download(url, target, digest):
    """Resume an interrupted transfer only when HTTP confirms the requested range."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset and sha256(partial) == digest:
        partial.replace(target)
        return
    request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
    with urllib.request.urlopen(request, timeout=60) as response:
        append = offset and response.status == 206
        if append and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
            raise ValueError("Server returned the wrong download range.")
        with partial.open("ab" if append else "wb") as output:
            shutil.copyfileobj(response, output, 1024 * 1024)
    if sha256(partial) != digest:
        partial.unlink()
        raise ValueError(f"Downloaded asset failed SHA-256 verification: {target.name}")
    partial.replace(target)


def install(root, source=None):
    root.mkdir(parents=True, exist_ok=True)
    source = Path(source).expanduser().resolve() if source else None
    for name, digest in HASHES.items():
        target = root / name
        if target.is_file() and sha256(target) == digest:
            print(f"Verified existing {name}", flush=True)
            continue
        if source and (source / name).is_file():
            original = source / name
            if sha256(original) != digest:
                raise ValueError(f"Import checksum mismatch: {original}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + ".importing")
            temp.unlink(missing_ok=True)
            try:
                os.link(original, temp)
            except OSError:
                shutil.copyfile(original, temp)
            temp.replace(target)
            print(f"Imported verified {name}", flush=True)
            continue
        print(f"Installing {name}", flush=True)
        if name == SEGMENT:
            archive = root / "segmentation.tar.bz2"
            download(SEGMENT_URL, archive, ARCHIVE_HASH)
            with tarfile.open(archive) as tar:
                member = next((m for m in tar.getmembers() if m.name.lstrip("./") == SEGMENT), None)
                if member is None or not member.isfile():
                    raise ValueError("Segmentation archive has no expected regular model file.")
                target.parent.mkdir(parents=True, exist_ok=True)
                temp = target.with_suffix(".importing")
                with tar.extractfile(member) as stream, temp.open("wb") as output:
                    shutil.copyfileobj(stream, output)
                if sha256(temp) != digest:
                    temp.unlink()
                    raise ValueError("Segmentation model checksum mismatch.")
                temp.replace(target)
            archive.unlink()
        else:
            url = EMBEDDING_URL if name == EMBEDDING else WHISPER_URL + Path(name).name
            download(url, target, digest)
