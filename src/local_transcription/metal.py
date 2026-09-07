"""Offline whisper.cpp recognition using the packaged Apple Metal executable."""

import os
from pathlib import Path
import re
import subprocess
import time

from .common import read_json, save_json
from .devices import validate_device
from .models import METAL_MODEL


def executable():
    validate_device('metal')
    path = Path(__file__).parent / '_bin' / 'whisper-cli'
    if not path.is_file():
        raise ValueError('Apple GPU runtime is missing. Install the Apple Silicon platform wheel '
                         'with Metal support, or explicitly use --device cpu.')
    return path


def normalize(raw):
    """Merge Whisper subword tokens; whisper.cpp JSON offsets are milliseconds."""
    segments = []
    for segment in raw['transcription']:
        words = []
        for token in segment['tokens']:
            text = token['text']
            if token['id'] >= 50257:  # Multilingual Whisper special tokens.
                continue
            if not text:
                continue
            timing = token.get('offsets', segment['offsets'])
            start, end = timing['from'] / 1000, timing['to'] / 1000
            if words and not text[0].isspace():
                words[-1]['word'] += text
                words[-1]['end'] = max(words[-1]['end'], end)
                words[-1]['probability'] = min(words[-1]['probability'], token['p'])
            else:
                words.append(dict(word=text, start=start, end=end, probability=token['p']))
        words = [w for w in words if w['word'].strip()]
        if words:
            segments.append(dict(start=segment['offsets']['from'] / 1000,
                                 end=segment['offsets']['to'] / 1000,
                                 text=''.join(w['word'] for w in words), words=words))
    return dict(language=raw['result']['language'], segments=segments)


def recognize(audio, root, work, language=None, threads=8):
    import soundfile as sf

    binary = executable()
    model = root / METAL_MODEL
    if not model.is_file():
        raise ValueError('Missing Apple GPU model. Run local-transcription models install --device metal.')
    # Keep native output for diagnosis; never let inference trigger model downloads.
    wav = work / 'metal-input.wav'
    output = work / 'metal-output'
    log = work / 'metal.log'
    sf.write(wav, audio, 16000, subtype='PCM_16')
    command = [str(binary), '-m', str(model), '-f', str(wav), '-of', str(output),
               '-ojf', '-l', language or 'auto', '-t', str(threads), '-bs', '5', '-pp']
    env = dict(os.environ)
    # Metal 3 on Ventura cannot compile bfloat kernels (introduced in Metal 3.1).
    # The q5_0 model uses float16/float32, so these kernels are unnecessary.
    env['GGML_METAL_BF16_DISABLE'] = '1'
    started = time.monotonic()
    selected = False
    print('Recognizing with Apple GPU (Metal, Whisper large-v3 q5_0).', flush=True)
    try:
        with log.open('w', encoding='utf-8') as diagnostics:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8', errors='replace', env=env)
            try:
                for line in process.stderr:
                    diagnostics.write(line)
                    diagnostics.flush()
                    if re.search(r'whisper_backend_init_gpu: using MTL[0-9]+ backend', line):
                        selected = True
                    if ('whisper_backend_init_gpu: no GPU found' in line or
                            'whisper_backend_init_gpu: failed to initialize' in line):
                        raise RuntimeError('Apple GPU initialization failed; CPU fallback was stopped. '
                                           f'See {log}. Use --device cpu to run on CPU explicitly.')
                    if 'whisper_print_progress_callback:' in line:
                        print(line.strip().split(':', 1)[-1].strip(), flush=True)
                code = process.wait()
                if code:
                    raise RuntimeError(f'Apple GPU recognition failed (exit {code}); see {log}.')
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                process.stderr.close()
        if not selected:
            raise RuntimeError(f'Apple GPU use was not confirmed; see {log}.')
        result = normalize(read_json(output.with_suffix('.json')))
        result.update(backend='whisper.cpp', device='metal',
                      elapsed_seconds=time.monotonic() - started)
        save_json(work / 'recognition.json', result)
        return result
    finally:
        wav.unlink(missing_ok=True)
