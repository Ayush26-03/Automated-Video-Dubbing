import json
from pathlib import Path
import threading
from typing import Optional

try:
    import torch
except ImportError:
    torch = None

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    try:
        import whisper  # type: ignore
    except ImportError:
        whisper = None
import subprocess


# --- Whisper model cache ----------------------------------------------------
# Loading the Whisper model costs ~500 MB–3 GB and ~30–60s. We memoise per
# (model_name, device, compute_type, cpu_threads) so back-to-back jobs reuse it.
_WHISPER_CACHE: dict = {}
_WHISPER_CACHE_LOCK = threading.Lock()


def _get_whisper_model(model_name: str, device: str, compute_type: str, cpu_threads: int):
    key = (model_name, device, compute_type, cpu_threads)
    with _WHISPER_CACHE_LOCK:
        if key in _WHISPER_CACHE:
            return _WHISPER_CACHE[key]
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
        _WHISPER_CACHE[key] = model
        return model


def clear_whisper_cache() -> None:
    """Drop cached Whisper models. Useful for tests and after device changes."""
    with _WHISPER_CACHE_LOCK:
        _WHISPER_CACHE.clear()


# --- Audio extraction -------------------------------------------------------

def extract_clean_audio(video_path: str) -> tuple[str, bool]:
    """
    Extract a clean 16kHz mono WAV for Whisper.
    Returns (audio_path, is_temporary).
    """
    vid_p = Path(video_path)
    if vid_p.suffix.lower() == ".wav":
        return str(vid_p.resolve()), False

    audio_out = vid_p.parent / f"{vid_p.stem}_whisper_16k.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(vid_p),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(audio_out)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and audio_out.exists() and audio_out.stat().st_size > 1024:
        return str(audio_out.resolve()), True

    # If extraction couldn't find audio, check error
    if "does not contain any stream" in res.stderr.lower():
        raise RuntimeError("Input video does not contain an audio track to transcribe.")

    return str(vid_p.resolve()), False


# --- Transcription ---------------------------------------------------------

def transcribe_video(
    video_path: str,
    model_name: str = "small",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> dict:
    """
    High-accuracy, high-speed transcription using faster-whisper with Silero VAD.
    Falls back gracefully to standard Whisper if faster-whisper is not available.

    Args:
        video_path: Path to the source media file.
        model_name: faster-whisper model size (tiny/base/small/medium/large).
        language: Force a language code, or None to auto-detect.
        initial_prompt: Optional context prompt. By default we use a neutral
            general-purpose prompt; callers can override per-content-type
            (e.g., a coding tutorial, a cooking video, etc.). The previous
            hard-coded "Hindi, English, Hinglish" prompt was removed because
            it biased transcription for non-Hindi source audio.
    """
    device = "cuda" if (torch is not None and torch.cuda.is_available()) else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    audio_path, _is_temp = extract_clean_audio(video_path)

    # Default prompt is intentionally language-neutral so it doesn't bias the
    # model toward any specific dialect or vocabulary.
    if initial_prompt is None:
        initial_prompt = "Clear narration, conversational speech."

    if HAS_FASTER_WHISPER:
        print(f"\n[2/6] Loading Faster-Whisper '{model_name}' on {device.upper()} ({compute_type})...")
        try:
            import os
            num_threads = min(8, max(2, (os.cpu_count() or 4) - 2))
            model = _get_whisper_model(
                model_name=model_name,
                device=device,
                compute_type=compute_type,
                cpu_threads=num_threads,
            )

            beam_size = 5
            print(f"[2/6] Transcribing with Silero VAD & beam_size={beam_size} ({num_threads} CPU threads)...")
            segments_generator, info = model.transcribe(
                audio_path,
                language=language if (language and str(language).lower() != "auto") else None,
                beam_size=beam_size,
                repetition_penalty=1.2,
                temperature=0.0,
                no_speech_threshold=0.6,
                hallucination_silence_threshold=2.0,
                initial_prompt=initial_prompt,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False
            )

            detected_lang = info.language
            segments = []
            full_text_parts = []

            for seg in segments_generator:
                text_clean = seg.text.strip()
                if not text_clean:
                    continue
                segments.append({
                    "id": len(segments),
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": text_clean,
                    "confidence": float(seg.avg_logprob) if hasattr(seg, "avg_logprob") else 0.0
                })
                full_text_parts.append(text_clean)

            print(f"Detected language : {detected_lang} (probability: {info.language_probability:.2f})")
            print(f"Number of segments: {len(segments)}")

            return {
                "text": " ".join(full_text_parts),
                "language": detected_lang,
                "segments": segments
            }
        except Exception as e:
            print(f"Warning: Faster-Whisper failed ({e}), falling back to standard Whisper...")

    # Fallback to standard OpenAI Whisper (only available if user installed it).
    print(f"\n[2/6] Loading Standard Whisper '{model_name}' on {device.upper()}...")
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "Neither 'faster-whisper' nor 'openai-whisper' is installed. "
            "Please install one of them (e.g. `pip install faster-whisper`)."
        )
    std_model = whisper.load_model(model_name, device=device)
    transcribe_options = {
        "verbose": False,
        "task": "transcribe",
        "beam_size": 5,
        "temperature": 0.0,
        "no_speech_threshold": 0.6,
        "initial_prompt": initial_prompt,
    }
    if language and str(language).lower() != "auto":
        transcribe_options["language"] = language.lower()

    result = std_model.transcribe(audio_path, **transcribe_options)
    return result


def save_transcript(
    result: dict,
    output_dir: str = "transcripts"
) -> str:
    """
    Save complete transcription result as JSON.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    transcript_file = output_path / "transcript.json"

    with open(transcript_file, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"Transcript saved to: {transcript_file}")
    return str(transcript_file)


if __name__ == "__main__":
    video_path = input("Enter path to video: ").strip()

    try:
        result = transcribe_video(video_path)
        print("\n--- FULL TRANSCRIPT ---")
        print(result.get("text", ""))

        print("\n--- FIRST 5 SEGMENTS ---")
        for segment in result.get("segments", [])[:5]:
            print(
                f"{segment['start']:.2f}s → {segment['end']:.2f}s : {segment['text'].strip()}"
            )

        save_transcript(result)
    except Exception as e:
        print(f"\nTranscription failed: {e}")