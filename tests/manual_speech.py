"""Opt-in real speech validation; paths and private results stay outside Git.

Supply known one-speaker and other-speaker intervals as validation expectations.
No sample recording paths or speaker timestamps are built into the checker.
"""

import json
import argparse
from pathlib import Path
import time

import soundfile as sf

from local_transcription.inference import automatic_turns, reference_turns


def totals(turns, start, end):
    result = {}
    for t in turns:
        duration = max(0, min(end, t["end"]) - max(start, t["start"]))
        if duration:
            key = str(t["speaker"])
            result[key] = result.get(key, 0) + duration
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("audio", "models", "references", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--single-interval", nargs=2, type=float, required=True)
    parser.add_argument("--other-interval", nargs=2, type=float, required=True)
    args = parser.parse_args()
    limit = max(args.single_interval[1], args.other_interval[1])
    audio, rate = sf.read(args.audio, frames=round(limit*16000), dtype="float32")
    assert rate == 16000 and audio.ndim == 1
    result = {}
    for name, call in [("automatic", lambda: automatic_turns(audio, args.models)),
                       ("references", lambda: reference_turns(audio, args.models, args.references))]:
        started = time.monotonic()
        turns = call()
        result[name] = dict(elapsed_seconds=time.monotonic()-started,
                            single_speaker_interval=totals(turns, *args.single_interval),
                            other_speaker_interval=totals(turns, *args.other_interval),
                            turn_count=len(turns))
        args.output.write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps({name: result[name]}), flush=True)


if __name__ == "__main__":
    main()
