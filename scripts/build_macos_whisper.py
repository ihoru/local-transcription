"""Bundle a pinned static whisper.cpp CLI with embedded Metal shaders on Apple Silicon."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION = '1.9.3'
URL = f'https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v{VERSION}'
SHA256 = '1650f884effba487025143bd8facd2f9fb40a83b3737a732803c67a8d659d9c0'
OPTIONS = [
    '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_OSX_DEPLOYMENT_TARGET=13.0',
    '-DCMAKE_OSX_ARCHITECTURES=arm64', '-DBUILD_SHARED_LIBS=OFF',
    '-DGGML_METAL=ON', '-DGGML_METAL_EMBED_LIBRARY=ON',
    '-DGGML_NATIVE=OFF', '-DGGML_OPENMP=OFF', '-DWHISPER_BUILD_TESTS=OFF',
    '-DWHISPER_BUILD_SERVER=OFF', '-DWHISPER_CURL=OFF',
]


def build(root):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('Build the Metal runtime on a native Apple Silicon Mac.')
    output = Path(root) / 'build' / 'whisper-macos-arm64'
    manifest = dict(version=VERSION, source=URL, sha256=SHA256, cmake=OPTIONS,
                    builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    stamp = output / 'whisper-build.json'
    if (stamp.is_file() and json.loads(stamp.read_text()) == manifest
            and (output / 'whisper-cli').is_file()):
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        temp = Path(temp)
        archive = temp / 'source.tar.gz'
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open('wb') as target:
            shutil.copyfileobj(response, target)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError('whisper.cpp source checksum mismatch.')
        with tarfile.open(archive) as source_tar:
            source_tar.extractall(temp, filter='data')
        source = temp / f'whisper.cpp-{VERSION}'
        build_dir = temp / 'compile'
        env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET='13.0')
        subprocess.run(['cmake', '-S', str(source), '-B', str(build_dir), *OPTIONS],
                       env=env, check=True)
        subprocess.run(['cmake', '--build', str(build_dir), '--target', 'whisper-cli',
                        '-j', str(min(os.cpu_count() or 2, 4))], env=env, check=True)
        staged = temp / 'bundle'
        staged.mkdir()
        binary = staged / 'whisper-cli'
        shutil.copy2(build_dir / 'bin/whisper-cli', binary)
        subprocess.run(['strip', '-x', str(binary)], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(binary)], check=True)
        subprocess.run(['lipo', str(binary), '-verify_arch', 'arm64'], check=True)
        links = subprocess.check_output(['otool', '-L', str(binary)], text=True)
        if any(not line.strip().startswith(('/usr/lib/', '/System/Library/'))
               for line in links.splitlines()[1:]):
            raise RuntimeError(f'Non-system whisper.cpp dependency: {links}')
        subprocess.run([str(binary), '--help'], check=True)
        shutil.copy2(source / 'LICENSE', staged / 'whisper-LICENSE')
        shutil.copy2(__file__, staged / 'build_macos_whisper.py')
        (staged / 'whisper-build.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(staged, output)
    return output
