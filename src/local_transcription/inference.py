"""Offline recognition and speaker analysis; expensive imports stay behind commands."""

from dataclasses import asdict
import os
import time

from .common import read_json, save_json
from .models import EMBEDDING, SEGMENT


def load_whisper(root, device, threads):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from faster_whisper import WhisperModel
    return WhisperModel(str(root / "whisper-large-v3"), device=device,
                        compute_type="int8" if device == "cpu" else "float16",
                        cpu_threads=threads, local_files_only=True)


def recognize(audio, root, work, language=None, device="cpu", threads=8, batch_size=4):
    from faster_whisper import BatchedInferencePipeline
    model = load_whisper(root, device, threads)
    pipeline = BatchedInferencePipeline(model)
    generated, info = pipeline.transcribe(audio, language=language, task="transcribe",
        beam_size=5, batch_size=batch_size, word_timestamps=True, vad_filter=True,
        condition_on_previous_text=False)
    segments = []
    report = -30
    started = time.monotonic()
    for segment in generated:
        item = asdict(segment)
        segments.append(item)
        if item["end"] - report >= 30:
            report = item["end"]
            print(f"Transcribed {report / 60:.1f}/{len(audio) / 16000 / 60:.1f} min "
                  f"({(time.monotonic() - started) / 60:.1f} min elapsed)", flush=True)
            save_json(work / "recognition.partial.json", dict(segments=segments))
    # A separate short decode can recover speech trimmed at the beginning by VAD.
    first = next((w for s in segments for w in s["words"]), None)
    if first and first["start"] > 1:
        cutoff = min(first["start"], 30)
        checked, _ = model.transcribe(audio[:min(len(audio), 40 * 16000)], language=info.language,
                                      beam_size=5, word_timestamps=True, vad_filter=False,
                                      condition_on_previous_text=False)
        prefix = []
        for segment in checked:
            if segment.no_speech_prob > .6 or segment.avg_logprob < -1.2:
                continue
            item = asdict(segment)
            selected = [w for w in item["words"] if w["end"] <= cutoff]
            if selected:
                prefix.append(dict(item, words=selected, start=selected[0]["start"],
                                   end=selected[-1]["end"], text="".join(w["word"] for w in selected)))
        segments = prefix + segments
    result = dict(language=info.language, segments=segments,
                  elapsed_seconds=time.monotonic() - started)
    save_json(work / "recognition.json", result)
    return result


def automatic_turns(audio, root, speakers=None, threshold=.5):
    import sherpa_onnx
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(root / SEGMENT)),
            num_threads=4, provider="cpu"),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(root / EMBEDDING), num_threads=4, provider="cpu"),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=speakers or -1, threshold=threshold),
        min_duration_on=.3, min_duration_off=.5)
    if not config.validate():
        raise ValueError("Invalid speaker analysis configuration.")
    detector = sherpa_onnx.OfflineSpeakerDiarization(config)
    reported = [-10]

    def progress(done, total):
        percent = int(done * 100 / max(total, 1))
        if percent >= reported[0] + 10:
            print(f"Speaker analysis: {percent}%", flush=True)
            reported[0] = percent
        return 0

    result = detector.process(audio, callback=progress).sort_by_start_time()
    return [dict(start=max(0, t.start), end=min(len(audio)/16000, t.end), speaker=int(t.speaker))
            for t in result]


def reference_turns(audio, root, path):
    import numpy as np
    import sherpa_onnx
    groups = read_json(path).get("speakers", [])
    if not groups:
        raise ValueError("Reference file needs a nonempty speakers array.")
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(root / EMBEDDING), num_threads=2))

    def embedding(start, end):
        if not (0 <= start < end <= len(audio) / 16000) or end - start < 1:
            raise ValueError("Reference intervals must be at least one second and within the recording.")
        stream = extractor.create_stream()
        stream.accept_waveform(16000, audio[int(start * 16000):int(end * 16000)])
        stream.input_finished()
        vector = np.asarray(extractor.compute(stream), dtype=np.float64)
        return vector / max(np.linalg.norm(vector), 1e-12)

    prototypes = []
    for group in groups:
        if not group.get("intervals"):
            raise ValueError("Each reference speaker needs intervals.")
        vector = np.mean([embedding(*interval) for interval in group["intervals"]], axis=0)
        prototypes.append(vector / max(np.linalg.norm(vector), 1e-12))
    prototypes = np.stack(prototypes)
    turns = []
    duration = len(audio) / 16000
    if duration < 1:
        return turns
    for index, start in enumerate(np.arange(0, duration, .5)):
        end = min(duration, start + .5)
        lo, hi = max(0, start - 1.25), min(duration, start + 1.75)
        if hi-lo < 1:
            continue
        clip = audio[int(lo * 16000):int(hi * 16000)]
        if float(np.mean(clip ** 2)) < 1e-7:
            continue
        scores = prototypes @ embedding(lo, hi)
        order = np.argsort(scores)
        best = int(order[-1])
        margin = scores[best] - scores[order[-2]] if len(order) > 1 else 1
        if scores[best] >= .60 and margin >= .04:
            turns.append(dict(start=float(start), end=float(end), speaker=best))
        if index % 120 == 0:
            print(f"Reference matching: {start / 60:.1f}/{duration / 60:.1f} min", flush=True)
    return turns


def assign_speakers(words, turns, audio):
    import numpy as np
    energy = np.concatenate(([0.0], np.cumsum(audio.astype(np.float64) ** 2)))
    sorted_turns = sorted(turns, key=lambda t: t["start"])
    cursor = 0
    labels = {}
    for word in words:
        while cursor < len(sorted_turns) and sorted_turns[cursor]["end"] < word["start"]:
            cursor += 1
        scores = {}
        for turn in sorted_turns[cursor:]:
            if turn["start"] > word["end"]:
                break
            a, b = max(word["start"], turn["start"]), min(word["end"], turn["end"])
            if b <= a:
                continue
            first, last = int(a * 16000), min(len(audio), int(b * 16000))
            scores[turn["speaker"]] = scores.get(turn["speaker"], 0) + float(energy[last] - energy[first])
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        word["speaker"] = None
        if ranked and ranked[0][1] > 0 and (len(ranked) == 1 or ranked[1][1] < .6 * ranked[0][1]):
            winner = ranked[0][0]
            word["speaker"] = labels.setdefault(winner, f"Speaker {len(labels) + 1}")
    # Fill only very short uncertain gaps bounded by the same voice.
    i = 0
    while i < len(words):
        if words[i]["speaker"] is not None:
            i += 1
            continue
        j = i
        while j + 1 < len(words) and words[j + 1]["speaker"] is None:
            j += 1
        if i and j + 1 < len(words) and words[i-1]["speaker"] == words[j+1]["speaker"]:
            if (words[j]["end"] - words[i]["start"] <= 1
                and words[i]["start"] - words[i-1]["end"] <= .5
                and words[j+1]["start"] - words[j]["end"] <= .5):
                for word in words[i:j+1]:
                    word["speaker"] = words[i-1]["speaker"]
        i = j + 1


def make_words(recognition, duration):
    words = []
    previous = 0.0
    for paragraph, segment in enumerate(recognition["segments"]):
        for item in segment["words"]:
            text = item["word"].strip()
            if not text:
                continue
            start = min(duration, max(previous, float(item["start"])))
            end = min(duration, max(start, float(item["end"])))
            words.append(dict(id=f"w{len(words)+1:06}", text=text, start=start, end=end,
                              probability=item.get("probability"), speaker=None, paragraph=paragraph))
            previous = end
    return words
