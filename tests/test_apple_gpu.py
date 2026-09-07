import json
import platform
import sys

import numpy as np
import pytest

from local_transcription import cli, devices, inference, metal, models, pipeline
from local_transcription.common import read_json, save_json, sha256


def test_apple_silicon_default_selects_metal(monkeypatch):
    import platform
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(platform, 'machine', lambda: 'arm64')
    args = cli.parser().parse_args(['transcribe', 'speech.wav'])
    assert args.device == 'metal'


@pytest.fixture
def apple(monkeypatch):
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(platform, 'machine', lambda: 'arm64')


@pytest.mark.parametrize('system,machine', [('Linux', 'aarch64'), ('Darwin', 'x86_64')])
def test_other_platforms_keep_cpu_default(monkeypatch, system, machine):
    monkeypatch.setattr(platform, 'system', lambda: system)
    monkeypatch.setattr(platform, 'machine', lambda: machine)
    assert devices.default_device() == 'cpu'
    with pytest.raises(ValueError, match='native Apple Silicon'):
        devices.validate_device('metal')


def test_all_commands_select_the_same_apple_backend(apple):
    for command in (['transcribe', 'a.wav'], ['recheck', 'run', '--start', '0', '--end', '1'],
                    ['models', 'install'], ['doctor']):
        assert cli.parser().parse_args(command).device == 'metal'
        assert cli.parser().parse_args([*command, '--device', 'cpu']).device == 'cpu'
    with pytest.raises(ValueError, match='CUDA requires NVIDIA'):
        devices.validate_device('cuda')


@pytest.fixture
def raw():
    # Shape and units from the pinned whisper.cpp 1.9.3 output_json implementation.
    return dict(result=dict(language='en'), transcription=[dict(
        offsets=dict(**{'from': 0, 'to': 1500}), text=' Hello transcription.', tokens=[
            dict(id=50365, text='[_BEG_]', p=.9),
            dict(id=1, text=' Hello', p=.9, offsets={'from': 100, 'to': 400}),
            dict(id=2, text=' trans', p=.8, offsets={'from': 400, 'to': 700}),
            dict(id=3, text='cription', p=.7, offsets={'from': 700, 'to': 1200}),
            dict(id=4, text='.', p=.9, offsets={'from': 1200, 'to': 1500}),
            dict(id=50257, text='[_EOT_]', p=.9),
        ])])


def test_metal_merges_subwords_and_preserves_seconds(raw):
    result = metal.normalize(raw)
    words = inference.make_words(result, 1.5)
    assert [w['text'] for w in words] == ['Hello', 'transcription.']
    assert [(w['start'], w['end']) for w in words] == [(.1, .4), (.4, 1.5)]
    assert words[1]['probability'] == .7
    assert result['language'] == 'en'


@pytest.fixture
def native_cli(tmp_path, monkeypatch, apple, raw):
    binary = tmp_path / 'whisper-cli'
    def configure(log='whisper_backend_init_gpu: using MTL0 backend', exit_code=0):
        # Run a real subprocess to exercise argument passing, JSON handoff, and fallback handling.
        binary.write_text(f'''#!{sys.executable}
import json, pathlib, sys
args = sys.argv[1:]
assert '-ng' not in args and '-ojf' in args
assert pathlib.Path(args[args.index('-m') + 1]).is_file()
print({log!r}, file=sys.stderr, flush=True)
pathlib.Path(args[args.index('-of') + 1] + '.json').write_text({json.dumps(raw)!r})
sys.exit({exit_code})
''')
        binary.chmod(0o755)
    configure()
    monkeypatch.setattr(metal, 'executable', lambda: binary)
    model = tmp_path / models.METAL_MODEL
    model.parent.mkdir()
    model.write_bytes(b'model fixture')
    return configure


def test_recognition_routes_to_metal_without_ctranslate2(tmp_path, monkeypatch, native_cli):
    monkeypatch.setitem(sys.modules, 'faster_whisper', None)
    result = inference.recognize(np.zeros(24000, dtype=np.float32), tmp_path, tmp_path,
                                 device='metal')
    assert result['device'] == 'metal' and result['backend'] == 'whisper.cpp'
    assert read_json(tmp_path / 'recognition.json') == result
    assert not (tmp_path / 'metal-input.wav').exists()


@pytest.mark.parametrize('log,code,message', [
    ('whisper_backend_init_gpu: no GPU found', 0, 'CPU fallback was stopped'),
    ('whisper_backend_init_gpu: using MTL0 backend\n'
     'whisper_backend_init_gpu: failed to initialize MTL0 backend', 0, 'CPU fallback was stopped'),
    ('whisper_backend_init_gpu: using MTL0 backend', 1, 'exit 1'),
    ('CPU only', 0, 'GPU use was not confirmed'),
])
def test_gpu_failure_never_becomes_cpu_success(tmp_path, native_cli, log, code, message):
    native_cli(log, code)
    with pytest.raises(RuntimeError, match=message):
        inference.recognize(np.zeros(16000), tmp_path, tmp_path, device='metal')
    assert not (tmp_path / 'recognition.json').exists()
    assert not (tmp_path / 'metal-input.wav').exists()


def test_metal_setup_imports_only_its_own_verified_model(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    model = source / models.METAL_MODEL
    model.parent.mkdir(parents=True)
    model.write_bytes(b'metal fixture')
    monkeypatch.setattr(models, 'METAL_HASH', sha256(model))
    monkeypatch.setattr(models, 'HASHES', {'whisper-large-v3/model.bin': '0' * 64})
    monkeypatch.setattr(models, 'download', lambda *a: pytest.fail('Unexpected model download'))
    target = tmp_path / 'target'
    models.install(target, source, device='metal')
    assert models.check(target, device='metal', verify=True) == []
    assert not (target / 'whisper-large-v3').exists()
    (target / models.METAL_MODEL).write_bytes(b'corrupt')
    assert 'Checksum mismatch' in models.check(target, device='metal', verify=True)[0]


def test_metal_recheck_uses_clip_and_restores_absolute_times(tmp_path, monkeypatch, native_cli):
    import soundfile as sf
    work = tmp_path / 'work'
    work.mkdir()
    save_json(work / 'transcript.json', dict(duration=4, language='en'))
    sf.write(work / 'audio.wav', np.zeros(64000), 16000)
    monkeypatch.setattr(models, 'check', lambda *a, **k: [])
    args = cli.parser().parse_args(['recheck', str(tmp_path), '--start', '2', '--end', '4',
                                   '--models-dir', str(tmp_path)])
    result = read_json(pipeline.recheck(args))
    assert result['segments'] == [dict(start=2, end=3.5, text='Hello transcription.')]


def test_packaged_metal_binary_is_self_contained():
    import subprocess
    if not devices.apple_silicon():
        pytest.skip('Native executable check requires Apple Silicon')
    binary = metal.executable()
    subprocess.run([str(binary), '--help'], check=True, capture_output=True)
    links = subprocess.check_output(['otool', '-L', str(binary)], text=True)
    assert all(line.strip().startswith(('/usr/lib/', '/System/Library/'))
               for line in links.splitlines()[1:])


def test_doctor_reports_missing_metal_runtime(apple, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(models, 'check', lambda *a, **k: [])
    def missing():
        raise ValueError('Apple GPU runtime is missing')
    monkeypatch.setattr(metal, 'executable', missing)
    assert cli.main(['doctor', '--models-dir', str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['default_device'] == 'metal'
    assert report['recognition_backend'] == 'whisper.cpp'
    assert any('Apple GPU runtime is missing' in e for e in report['errors'])


def test_metal_pipeline_produces_raw_outputs_and_review_handoff(tmp_path, monkeypatch, native_cli):
    import soundfile as sf
    source = tmp_path / 'speech.wav'
    sf.write(source, np.zeros(24000), 16000)
    monkeypatch.setattr(models, 'check', lambda *a, **k: [])
    monkeypatch.setitem(sys.modules, 'faster_whisper', None)
    args = cli.parser().parse_args(['transcribe', str(source), '--no-diarization',
                                   '--models-dir', str(tmp_path)])
    run = pipeline.transcribe(args)
    assert read_json(run / 'work/run.json')['options']['device'] == 'metal'
    assert read_json(run / 'work/run.json')['status'] == 'awaiting_review'
    assert 'Hello transcription.' in (run / 'speech.txt').read_text()
    assert 'Hello transcription.' in (run / 'speech.srt').read_text()
    assert (run / 'work/review.template.json').is_file()
