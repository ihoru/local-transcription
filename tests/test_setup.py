import sys
import types

import pytest

from local_transcription import inference, models
from local_transcription.common import sha256


def test_speaker_native_runtime_is_packaged():
    import sherpa_onnx
    assert callable(sherpa_onnx.OfflineSpeakerDiarization)


def test_whisper_load_is_local_and_explicit(monkeypatch, tmp_path):
    calls = []
    module = types.ModuleType("faster_whisper")
    module.WhisperModel = lambda *a, **k: calls.append((a, k))
    monkeypatch.setitem(sys.modules, "faster_whisper", module)
    inference.load_whisper(tmp_path, "cpu", 2)
    assert calls[0][0] == (str(tmp_path / "whisper-large-v3"),)
    assert calls[0][1]["local_files_only"] is True
    assert calls[0][1]["compute_type"] == "int8"


def test_imported_models_are_verified_without_network(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample").write_bytes(b"test model")
    monkeypatch.setattr(models, "HASHES", {"sample": sha256(source / "sample")})
    monkeypatch.setattr(models, "download", lambda *a: pytest.fail("Import attempted a download"))
    target = tmp_path / "target"
    models.install(target, source)
    assert (target / "sample").read_bytes() == b"test model"
    assert models.check(target, verify=True) == []


def test_corrupt_import_is_rejected(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample").write_bytes(b"corrupt")
    monkeypatch.setattr(models, "HASHES", {"sample": "0"*64})
    with pytest.raises(ValueError, match="Import checksum mismatch"):
        models.install(tmp_path / "target", source)
    assert not (tmp_path / "target/sample").exists()
