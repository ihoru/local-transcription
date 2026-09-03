"""Render two views from the same timed units, without changing spoken content."""

import re

from .common import stamp


def terminal(text):
    return bool(re.search(r'[.!?…][}"\u00bb]*$', text.rstrip()))


def display(unit):
    return "{" + unit["text"] + "}" if unit.get("changed") else unit["text"]


def label(part, diarization):
    if not diarization:
        return ""
    value = part["speaker"] or "Unknown speaker"
    return "{" + value + "}" if part.get("speaker_changed") else value


def groups(units, subtitle=False):
    result = []
    for unit in units:
        text = display(unit)
        previous = result[-1] if result else None
        join = previous and previous["speaker"] == unit["speaker"]
        if join:
            gap = unit["start"] - previous["end"]
            if subtitle:
                join = (gap <= 1.5 and unit["end"] - previous["start"] <= 7
                        and len(previous["text"] + text) + 1 <= 100)
            else:
                join = (gap <= 1.5 and unit.get("paragraph") == previous.get("paragraph")) or (
                    gap <= 5 and not terminal(previous["text"]))
        if join:
            previous["text"] += " " + text
            previous["end"] = unit["end"]
            previous["paragraph"] = unit.get("paragraph")
            previous["speaker_changed"] |= unit.get("speaker_changed", False)
        else:
            result.append(dict(unit, text=text, speaker_changed=unit.get("speaker_changed", False)))
    return result


def content(parts):
    return re.sub(r"\s+", "", "".join(p["text"] for p in parts))


def render(data, units=None, proofread=False):
    units = data["words"] if units is None else units
    paragraphs, cues = groups(units), groups(units, True)
    if content(paragraphs) != content(cues):
        raise ValueError("TXT and SRT contents differ.")
    title = data["title"] + (" — proofread" if proofread else "")
    note = ("\n\nCurly braces mark substantive corrections and reviewed speaker labels. "
            "{unintelligible} marks a passage that could not be recovered confidently.") if proofread else ""
    blocks = []
    for p in paragraphs:
        speaker = label(p, data["diarization"])
        header = f"[{stamp(p['start'])} — {stamp(p['end'])}]"
        blocks.append(header + (f" {speaker}:" if speaker else "") + "\n" + p["text"])
    txt = title + note + "\n\n" + "\n\n".join(blocks) + "\n"
    subtitles = []
    for i, p in enumerate(cues, 1):
        speaker = label(p, data["diarization"])
        subtitles.append(f"{i}\n{stamp(p['start'], True)} --> {stamp(p['end'], True)}\n"
                         + (f"{speaker}: " if speaker else "") + p["text"])
    return txt, "\n\n".join(subtitles) + ("\n" if subtitles else "")
