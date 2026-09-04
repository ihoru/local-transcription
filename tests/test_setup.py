import sys
import types

import pytest

from local_transcription import inference, models
from local_transcription.common import sha256


def test_speaker_native_runtime_is_packaged():
    import sherpa_onnx
    assert callable(sherpa_onnx.OfflineSpeakerDiarization)


def test_cpu_int8_runtime_is_available():
    import ctranslate2
    assert 'int8' in ctranslate2.get_supported_compute_types('cpu')


def test_packaged_macos_executables_match_native_python(monkeypatch):
    import os
    from pathlib import Path
    import platform
    import struct
    import subprocess
    from local_transcription import media

    if os.environ.get('EXPECTED_ARCH'):
        assert platform.machine() == os.environ['EXPECTED_ARCH']
    if sys.platform != 'darwin':
        pytest.skip('Mach-O validation runs on native Mac CI runners')
    expected_cpu = {'arm64': 0x0100000c, 'x86_64': 0x01000007}[platform.machine()]
    monkeypatch.setattr(media.shutil, 'which', lambda name: None)
    for name in ('ffmpeg', 'ffprobe'):
        path = Path(media.executable(name))
        assert path.parent.name == '_bin'
        with path.open('rb') as binary:
            magic, cpu = struct.unpack('<II', binary.read(8))
        assert magic == 0xfeedfacf and cpu == expected_cpu
        links = subprocess.check_output(['/usr/bin/otool', '-L', str(path)], text=True)
        assert all(line.strip().startswith(('/usr/lib/', '/System/Library/'))
                   for line in links.splitlines()[1:])
        assert 'ffmpeg' in media.run([name, '-version']).lower()


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
