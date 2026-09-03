"""Build portable release assets from the maintained checkout and uv lockfile."""

import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile


def build(output):
    root = Path(__file__).resolve().parents[1]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run(["uv", "build", "--wheel", "--out-dir", str(output)], cwd=root, check=True)
    subprocess.run([
        "uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes",
        "--no-header", "--no-annotate", "--output-file", str(output / "runtime-constraints.txt"),
    ], cwd=root, check=True, stdout=subprocess.DEVNULL)
    skill = root / "skills/local-transcription"
    with zipfile.ZipFile(output / "local-transcription-skill.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        # Explicit documentation allowlist keeps local recordings/caches out of releases.
        for path in [skill / "SKILL.md", *sorted((skill / "references").glob("*.md"))]:
            archive.write(path, Path(skill.name) / path.relative_to(skill))
    assets = [*output.glob("*.whl"), output / "runtime-constraints.txt",
              output / "local-transcription-skill.zip"]
    with (output / "SHA256SUMS").open("w") as checksums:
        for path in sorted(assets):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            checksums.write(f"{digest}  {path.name}\n")
    print(output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/build_release.py NEW_OUTPUT_DIRECTORY")
    build(Path(sys.argv[1]))
