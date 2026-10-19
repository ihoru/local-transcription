import json
from types import SimpleNamespace

import pytest

from local_transcription import cli, devices, inference, models


@pytest.fixture(autouse=True)
def linux_cuda_platform(monkeypatch):
    monkeypatch.setattr(devices, 'platform', SimpleNamespace(
        system=lambda: 'Linux', machine=lambda: 'x86_64'))


@pytest.mark.parametrize('failure', ['load', 'encode'])
def test_cuda_doctor_rejects_runtime_failure(monkeypatch, capsys, tmp_path, failure):
    monkeypatch.setattr(models, 'check', lambda *a, **k: [])
    def fail(*a, **k):
        raise RuntimeError('Library libcublas.so.12 is not found or cannot be loaded')
    def load(*a, **k):
        return SimpleNamespace(encode=fail)
    monkeypatch.setattr(inference, 'load_whisper', fail if failure == 'load' else load)
    assert cli.main(['doctor', '--device', 'cuda', '--models-dir', str(tmp_path)]) == 1
    errors = json.loads(capsys.readouterr().out)['errors']
    assert any('libcublas.so.12' in error for error in errors)


def test_cuda_doctor_executes_encoder(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(models, 'check', lambda *a, **k: [])
    calls = []
    def encode(features):
        assert features.dtype.name == 'float32'
        assert features.shape == (128, 3000)
        calls.append(True)
    monkeypatch.setattr(inference, 'load_whisper', lambda *a, **k: SimpleNamespace(encode=encode))
    assert cli.main(['doctor', '--device', 'cuda', '--models-dir', str(tmp_path)]) == 0
    assert calls == [True]
    assert json.loads(capsys.readouterr().out)['errors'] == []


def test_optional_cuda_wheel_is_loaded_before_inference(monkeypatch, tmp_path):
    import sys
    from local_transcription import cuda
    calls = []
    monkeypatch.setattr(cuda.sys, 'platform', 'linux')
    monkeypatch.setattr(cuda, 'import_module', lambda name: SimpleNamespace(__path__=[str(tmp_path)]))
    monkeypatch.setattr(cuda.ctypes, 'CDLL', lambda path, **kwargs: calls.append(path))
    def whisper(*args, **kwargs):
        assert calls == [str(tmp_path / 'lib/libcublasLt.so.12'),
                         str(tmp_path / 'lib/libcublas.so.12')]
        assert kwargs['device'] == 'cuda'
        return 'loaded'
    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=whisper))
    assert inference.load_whisper(tmp_path, 'cuda', 2) == 'loaded'


def test_system_cuda_remains_supported_without_wheel(monkeypatch):
    from local_transcription import cuda
    monkeypatch.setattr(cuda.sys, 'platform', 'linux')
    def missing(name):
        raise ModuleNotFoundError("No module named 'nvidia'", name='nvidia')
    monkeypatch.setattr(cuda, 'import_module', missing)
    monkeypatch.setattr(cuda.ctypes, 'CDLL', lambda *a, **k: pytest.fail('No wheel to preload'))
    cuda.prepare_runtime()
