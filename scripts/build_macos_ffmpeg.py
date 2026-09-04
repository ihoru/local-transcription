"""Build native, self-contained media tools during packaging, never at runtime."""

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


VERSION = "9.0.1"
URL = f"https://ffmpeg.org/releases/ffmpeg-{VERSION}.tar.xz"
SHA256 = "cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635"
MIN_MACOS = "13.0"
OPTIONS = [
    "--disable-autodetect", "--disable-shared", "--enable-static",
    "--disable-gpl", "--disable-nonfree", "--disable-version3",
    "--disable-doc", "--disable-debug", "--disable-ffplay",
    "--disable-network", "--disable-x86asm",
]


def build(root):
    if platform.system() != "Darwin" or platform.machine() not in ("arm64", "x86_64"):
        raise RuntimeError("Build macOS media tools on a native arm64 or x86_64 Mac.")
    arch = platform.machine()
    output = Path(root) / "build" / f"ffmpeg-macos-{arch}"
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest = dict(version=VERSION, source=URL, sha256=SHA256, architecture=arch,
                    deployment_target=MIN_MACOS, configure=OPTIONS, builder_sha256=script_hash)
    stamp = output / "build.json"
    if stamp.is_file() and json.loads(stamp.read_text()) == manifest:
        if all((output / name).is_file() for name in ("ffmpeg", "ffprobe", "source.tar.xz")):
            return output
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        temp = Path(temp)
        archive = temp / "source.tar.xz"
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open("wb") as target:
            shutil.copyfileobj(response, target)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError("FFmpeg source checksum mismatch.")
        with tarfile.open(archive) as source_tar:
            source_tar.extractall(temp, filter="data")
        source = temp / f"ffmpeg-{VERSION}"
        env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET=MIN_MACOS)
        subprocess.run(["./configure", *OPTIONS], cwd=source, env=env, check=True)
        subprocess.run(["make", f"-j{min(os.cpu_count() or 2, 4)}", "ffmpeg", "ffprobe"],
                       cwd=source, env=env, check=True)
        staged = temp / "bundle"
        staged.mkdir()
        for name in ("ffmpeg", "ffprobe"):
            binary = staged / name
            shutil.copy2(source / name, binary)
            subprocess.run(["strip", "-x", str(binary)], check=True)
            subprocess.run(["codesign", "--force", "--sign", "-", str(binary)], check=True)
            subprocess.run(["lipo", str(binary), "-verify_arch", arch], check=True)
            links = subprocess.check_output(["otool", "-L", str(binary)], text=True)
            for line in links.splitlines()[1:]:
                if not line.strip().startswith(("/usr/lib/", "/System/Library/")):
                    raise RuntimeError(f"Non-system dynamic dependency: {line}")
            subprocess.run([str(binary), "-version"], check=True)
        # Ship the exact unmodified sources, license, and recipe with the executables.
        shutil.copy2(archive, staged / "source.tar.xz")
        shutil.copy2(source / "COPYING.LGPLv2.1", staged / "COPYING.LGPLv2.1")
        shutil.copy2(__file__, staged / "build_macos_ffmpeg.py")
        (staged / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staged / "NOTICE.md").write_text(
            f"FFmpeg {VERSION}, Copyright the FFmpeg developers.\n\n"
            "These separate executables are built from unmodified FFmpeg sources under "
            "LGPL-2.1-or-later, without GPL, nonfree, or external libraries. "
            "See COPYING.LGPLv2.1, source.tar.xz, build.json and build_macos_ffmpeg.py. "
            "To rebuild, run the recipe on a Mac with Xcode command line tools; "
            "the recipe verifies the source archive against the pinned SHA-256.\n"
        )
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(staged, output)
    return output


if __name__ == "__main__":
    print(build(Path.cwd()))
