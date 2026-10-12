import asyncio
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import edge_tts
except ImportError:
    edge_tts = None
from src.config import get_default_voice


async def generate_single_speech(
    text: str,
    output_file: str,
    voice: str = "en-US-AriaNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    semaphore: Optional[asyncio.Semaphore] = None
):
    """
    Generate speech for a single text clip using Microsoft Edge-TTS with concurrency limiting.
    """
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed. Install it with: pip install edge-tts")
    if semaphore:
        async with semaphore:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
            await communicate.save(output_file)
    else:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(output_file)


def get_audio_duration(audio_file: str) -> float:
    """
    Get exact audio duration using FFprobe with fallback.
    """
    try:
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_file
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except Exception:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(audio_file)
            return float(audio.info.length)
        except Exception as e:
            raise RuntimeError(f"Could not determine audio duration for {audio_file}: {e}")


async def synthesize_all_parallel(
    tasks_data: List[Dict[str, Any]],
    voice: str,
    max_concurrency: int = 8
):
    """
    Synthesize all audio segments in parallel batches using asyncio.

    Failures in individual segments don't take down the whole batch — failed
    coros are collected and retried sequentially with reduced concurrency.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    coros = [
        generate_single_speech(
            text=item["text"],
            output_file=item["output_file"],
            voice=voice,
            semaphore=semaphore
        )
        for item in tasks_data
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    failures = []
    for item, result in zip(tasks_data, results):
        if isinstance(result, Exception):
            failures.append((item, result))

    if not failures:
        return

    # Retry the failed ones sequentially with a low concurrency cap.
    print(
        f"[TTS] {len(failures)} segment(s) failed in batch; retrying sequentially..."
    )
    retry_semaphore = asyncio.Semaphore(2)
    retry_coros = [
        generate_single_speech(
            text=item["text"],
            output_file=item["output_file"],
            voice=voice,
            semaphore=retry_semaphore
        )
        for item, _ in failures
    ]
    retry_results = await asyncio.gather(*retry_coros, return_exceptions=True)

    for (item, original_err), retry_result in zip(failures, retry_results):
        if isinstance(retry_result, Exception):
            print(
                f"[TTS] Segment {item['index']} failed after retry: "
                f"{type(retry_result).__name__}: {retry_result} "
                f"(original: {original_err})"
            )


def synthesize_segments(
    segments: Optional[List[Dict[str, Any]]] = None,
    translated_segments: Optional[List[Dict[str, Any]]] = None,
    target_language: str = "en",
    voice: Optional[str] = None,
    gender: str = "female",
    output_dir: str = "audio_segments",
    max_concurrency: int = 8
) -> List[Dict[str, Any]]:
    """
    High-speed parallel speech synthesis for all segments.
    """
    input_segments = segments if segments is not None else (translated_segments or [])
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    selected_voice = voice or get_default_voice(target_language, gender=gender)
    print(f"\n[4/6] Synthesizing {len(input_segments)} audio clips in parallel (Voice: {selected_voice})...")

    # Prepare parallel task metadata
    tasks_data = []
    valid_items = []

    for index, segment in enumerate(input_segments):
        text = segment.get("translated_text", "").strip()
        if not text:
            continue
        output_file = output_path / f"segment_{index:04d}.mp3"
        tasks_data.append({
            "index": index,
            "text": text,
            "output_file": str(output_file.resolve()),
            "segment": segment
        })
        valid_items.append((index, text, output_file, segment))

    # Run parallel batch download with per-segment retry
    if tasks_data:
        try:
            asyncio.run(
                synthesize_all_parallel(
                    tasks_data=tasks_data,
                    voice=selected_voice,
                    max_concurrency=max_concurrency
                )
            )
        except Exception as e:
            # Programmatic error (e.g., event loop failure) — surface it but keep
            # the partial progress that the gather/retry handles internally.
            print(f"[TTS] Parallel synthesis engine error: {e}")

    # Calculate audio durations for the segments that actually produced files.
    generated_segments = []
    for index, text, output_file, segment in valid_items:
        if not (output_file.exists() and output_file.stat().st_size > 0):
            print(f"[TTS] Segment {index} produced no audio; skipping alignment.")
            continue
        try:
            duration = get_audio_duration(str(output_file))
        except Exception as e:
            print(
                f"[TTS] Segment {index} duration probe failed ({e}); "
                "falling back to original slot length."
            )
            duration = max(0.5, float(segment["end"]) - float(segment["start"]))

        target_duration = float(segment["end"]) - float(segment["start"])

        generated_segments.append({
            "index": index,
            "start": float(segment["start"]),
            "end": float(segment["end"]),
            "target_duration": target_duration,
            "tts_duration": duration,
            "original_text": segment.get("original_text", ""),
            "translated_text": text,
            "audio_file": str(output_file.resolve()),
            "voice": selected_voice
        })

    print(f"\nSpeech synthesis complete: {len(generated_segments)} clips generated in parallel.")
    return generated_segments


def save_tts_metadata(
    segments: List[Dict[str, Any]],
    output_dir: str = "audio_segments"
) -> str:
    """Save metadata of all synthesized TTS segments to JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata_file = output_path / "tts_segments.json"

    with open(metadata_file, "w", encoding="utf-8") as file:
        json.dump(segments, file, ensure_ascii=False, indent=2)

    print(f"TTS metadata saved to: {metadata_file}")
    return str(metadata_file)


if __name__ == "__main__":
    print("Edge-TTS Parallel Speech Synthesizer")
    trans_file = input("Enter translated segments JSON path: ").strip()
    target_lang = input("Enter target language code (e.g., en, es, hi, fr): ").strip() or "en"

    try:
        with open(trans_file, "r", encoding="utf-8") as file:
            segments = json.load(file)

        tts_segs = synthesize_segments(segments=segments, target_language=target_lang)
        save_tts_metadata(tts_segs)
        print("\nTTS synthesis completed successfully.")
    except Exception as e:
        print(f"\nTTS failed: {e}")