"""Command-line entry point."""

import argparse
import json
from pathlib import Path
import shutil
import sys

from . import __version__, media, models, pipeline, review
from .common import seconds


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be positive.")
    return number


def runtime(parser):
    parser.add_argument("--models-dir", help="Model directory (or LOCAL_TRANSCRIPTION_MODELS).")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--threads", type=positive, default=8)


def parser():
    root = argparse.ArgumentParser(description="Local transcription and auditable agent proofreading.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="Extract audio; detect the actual media format.")
    convert.add_argument("input")
    convert.add_argument("--output-dir")
    convert.add_argument("--audio-stream", type=int, help="Absolute FFprobe audio stream index.")
    transcribe = commands.add_parser("transcribe", help="Create raw TXT/SRT and an agent review handoff.")
    transcribe.add_argument("input")
    transcribe.add_argument("--output-dir")
    transcribe.add_argument("--audio-stream", type=int)
    transcribe.add_argument("--language", help="Whisper language code; default: automatic detection.")
    transcribe.add_argument("--batch-size", type=positive, default=4)
    transcribe.add_argument("--no-diarization", action="store_true")
    count = transcribe.add_mutually_exclusive_group()
    count.add_argument("--speakers", type=positive, help="Known speaker count; default: automatic.")
    count.add_argument("--speaker-references", help="JSON containing one group of sample intervals per speaker.")
    transcribe.add_argument("--speaker-threshold", type=float, default=.5)
    runtime(transcribe)
    recheck = commands.add_parser("recheck", help="Locally recognize one difficult passage again.")
    recheck.add_argument("run")
    recheck.add_argument("--start", required=True, type=seconds)
    recheck.add_argument("--end", required=True, type=seconds)
    runtime(recheck)
    apply = commands.add_parser("apply-review", help="Create proofread TXT/SRT from an agent's edit file.")
    apply.add_argument("run")
    apply.add_argument("edits")
    model = commands.add_parser("models", help="Explicit model setup.")
    model_commands = model.add_subparsers(dest="model_command", required=True)
    install = model_commands.add_parser("install", help="Download or import SHA-256-verified models.")
    install.add_argument("--models-dir")
    install.add_argument("--from-dir", help="Reuse verified assets from an existing installation.")
    doctor = commands.add_parser("doctor", help="Check local tools, model assets, and hardware.")
    doctor.add_argument("--models-dir")
    doctor.add_argument("--verify", action="store_true", help="Hash all installed model files.")
    return root


def doctor(args):
    import ctranslate2
    import soundfile as sf
    root = models.model_dir(args.models_dir)
    errors = models.check(root, verify=args.verify)
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            errors.append(f"Missing {tool}.")
    try:
        import sherpa_onnx  # noqa: F401
    except (ImportError, OSError) as exc:
        errors.append(f"Speaker runtime cannot load: {exc}. Run uv sync --locked.")
    try:
        gpu_count = ctranslate2.get_cuda_device_count()
    except RuntimeError:
        gpu_count = 0
    print(json.dumps(dict(models_dir=str(root), ffmpeg=shutil.which("ffmpeg"),
                         ffprobe=shutil.which("ffprobe"), cuda_devices=gpu_count,
                         default_device="cpu", soundfile_version=sf.__version__, errors=errors), indent=2))
    return 1 if errors else 0


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "convert":
            target, info = media.convert(args.input, args.output_dir, args.audio_stream)
            print(json.dumps(dict(audio=str(target), source=info), indent=2))
        elif args.command == "transcribe":
            if args.no_diarization and (args.speakers or args.speaker_references):
                cli.error("--no-diarization cannot be combined with speaker options.")
            if not 0 < args.speaker_threshold < 2:
                cli.error("--speaker-threshold must be between 0 and 2.")
            pipeline.transcribe(args)
        elif args.command == "recheck":
            print(pipeline.recheck(args))
        elif args.command == "apply-review":
            for path in review.apply_review(Path(args.run).expanduser().resolve(), args.edits):
                print(path)
        elif args.command == "models":
            models.install(models.model_dir(args.models_dir), args.from_dir)
        else:
            return doctor(args)
    except (ValueError, OSError, RuntimeError, KeyError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
