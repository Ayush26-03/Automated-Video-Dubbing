"""
Subtitle generator module.
Creates standard SRT and VTT subtitle files from transcription/translation segments.
"""

from pathlib import Path
from typing import List, Dict, Any


def format_timestamp_srt(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Convert seconds to WebVTT timestamp format: HH:MM:SS.mmm"""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def export_srt(segments: List[Dict[str, Any]], output_path: str, text_key: str = "translated_text") -> str:
    """
    Export segments to an SRT file.
    text_key can be 'translated_text' or 'text' or 'original_text'.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for idx, seg in enumerate(segments, start=1):
            text = seg.get(text_key, seg.get("text", "")).strip()
            if not text:
                continue
            start_time = format_timestamp_srt(float(seg["start"]))
            end_time = format_timestamp_srt(float(seg["end"]))

            f.write(f"{idx}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")

    print(f"SRT subtitle saved to: {path}")
    return str(path)


def export_vtt(segments: List[Dict[str, Any]], output_path: str, text_key: str = "translated_text") -> str:
    """
    Export segments to a WebVTT file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for idx, seg in enumerate(segments, start=1):
            text = seg.get(text_key, seg.get("text", "")).strip()
            if not text:
                continue
            start_time = format_timestamp_vtt(float(seg["start"]))
            end_time = format_timestamp_vtt(float(seg["end"]))

            f.write(f"{idx}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")

    print(f"VTT subtitle saved to: {path}")
    return str(path)
