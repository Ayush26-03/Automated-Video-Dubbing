"""Shared dubbing pipeline used by both the CLI and the web server.

Both entry points now call into `run_pipeline(...)` instead of duplicating the
6-step pipeline. The pipeline emits progress via callbacks; cancellation is
cooperative through an `is_cancelled` callback that the caller can flip at
any time (an interrupted response from the web UI, a Ctrl-C in CLI, etc.).
"""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .config import DEFAULT_WHISPER_MODEL
from .downloader import download_video
from .transcriber import transcribe_video, save_transcript
from .translator import translate_segments, save_translated_segments
from .tts import synthesize_segments, save_tts_metadata
from .audio_aligner import create_aligned_audio
from .final_remixer import create_final_video
from .subtitles import export_srt, export_vtt

LogFn = Callable[[str, Optional[int], Optional[int]], None]
CancelFn = Callable[[], bool]


def run_pipeline(
    source_input: str,
    target_lang: str,
    gender: str = "female",
    model_name: str = DEFAULT_WHISPER_MODEL,
    voice: Optional[str] = None,
    embed_subs: bool = False,
    source_lang: Optional[str] = None,
    run_dir: Optional[Path] = None,
    log: Optional[LogFn] = None,
    is_cancelled: Optional[CancelFn] = None,
    initial_prompt: Optional[str] = None,
) -> dict:
    """Run the full 6-step dubbing pipeline and return all artifacts.

    `log(message, step, progress)` is called at every progress checkpoint.
    `is_cancelled()` is polled between heavy steps; if it returns True the
    pipeline short-circuits and returns a partial result with `cancelled=True`.

    Returns a dict with all output paths and metadata. On error, the exception
    propagates with full context.
    """

    def emit(msg: str, step: Optional[int] = None, progress: Optional[int] = None) -> None:
        # Always print, even if the caller-supplied log fails.
        tag = ""
        if step is not None and progress is not None:
            tag = f"  [step {step}/6 · {progress:>3}%]  "
        elif step is not None:
            tag = f"  [step {step}/6]                "
        print(f"{tag}{msg}")
        if log is not None:
            try:
                log(msg, step, progress)
            except Exception as exc:  # pragma: no cover - last-ditch
                print(f"  (log callback raised: {exc})")

    def cancelled() -> bool:
        if is_cancelled is None:
            return False
        try:
            return bool(is_cancelled())
        except Exception:
            return False

    # --- Setup ---
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    if run_dir is None:
        run_dir = Path("outputs") / run_id
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    emit(f"Pipeline session: {run_id}", step=None, progress=0)

    # --- Step 1: Download / Ingestion ---
    emit("Step 1/6: Ingesting video source...", step=1, progress=10)
    download_dir = run_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    video_path = download_video(source_input, output_dir=str(download_dir))
    emit(f"Video ready: {Path(video_path).name}", step=1, progress=20)
    if cancelled():
        return _cancelled_result(run_id)

    # --- Step 2: Transcription ---
    emit(
        f"Step 2/6: Transcribing with Whisper '{model_name}'...",
        step=2,
        progress=25,
    )
    transcript = transcribe_video(
        video_path,
        model_name=model_name,
        language=source_lang,
        initial_prompt=initial_prompt,
    )
    transcript_dir = run_dir / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = save_transcript(transcript, output_dir=str(transcript_dir))
    source_language = transcript.get("language", "en")
    segments = transcript.get("segments", [])
    export_srt(
        segments,
        str(transcript_dir / "original_subtitles.srt"),
        text_key="text",
    )
    emit(
        f"Transcribed {len(segments)} segments (source language: {source_language})",
        step=2,
        progress=40,
    )
    if cancelled():
        return _cancelled_result(run_id, video_path=video_path, transcript=transcript)

    # --- Step 3: Translation ---
    emit(
        f"Step 3/6: Translating from '{source_language}' to '{target_lang}'...",
        step=3,
        progress=45,
    )
    translated_segments = translate_segments(
        segments=segments,
        source_language=source_language,
        target_language=target_lang,
    )
    translation_dir = run_dir / "translations"
    translation_dir.mkdir(parents=True, exist_ok=True)
    translated_path = save_translated_segments(
        translated_segments,
        output_dir=str(translation_dir),
    )
    sub_dir = run_dir / "subtitles"
    sub_dir.mkdir(parents=True, exist_ok=True)
    translated_srt_path = export_srt(
        translated_segments,
        str(sub_dir / f"dubbed_{target_lang}.srt"),
    )
    translated_vtt_path = export_vtt(
        translated_segments,
        str(sub_dir / f"dubbed_{target_lang}.vtt"),
    )
    emit(
        f"Translation complete ({len(translated_segments)} segments)",
        step=3,
        progress=60,
    )
    if cancelled():
        return _cancelled_result(
            run_id,
            video_path=video_path,
            transcript=transcript,
            translated_segments=translated_segments,
            translated_path=translated_path,
            translated_srt_path=translated_srt_path,
            translated_vtt_path=translated_vtt_path,
            source_language=source_language,
            transcript_path=transcript_path,
        )

    # --- Step 4: Text to Speech ---
    emit(f"Step 4/6: Synthesizing speech ({gender} voice)...", step=4, progress=65)
    tts_dir = run_dir / "audio_segments"
    tts_dir.mkdir(parents=True, exist_ok=True)
    tts_segments = synthesize_segments(
        segments=translated_segments,
        target_language=target_lang,
        voice=voice,
        gender=gender,
        output_dir=str(tts_dir),
    )
    tts_path = save_tts_metadata(tts_segments, output_dir=str(tts_dir))
    emit(f"Synthesized {len(tts_segments)} audio clips", step=4, progress=80)
    if cancelled():
        return _cancelled_result(
            run_id,
            video_path=video_path,
            transcript=transcript,
            translated_segments=translated_segments,
            translated_path=translated_path,
            translated_srt_path=translated_srt_path,
            translated_vtt_path=translated_vtt_path,
            source_language=source_language,
            transcript_path=transcript_path,
            tts_path=tts_path,
        )

    # --- Step 5: Audio Alignment ---
    emit("Step 5/6: Synchronizing audio timestamps and pacing...", step=5, progress=85)
    audio_output_dir = run_dir / "output"
    audio_output_dir.mkdir(parents=True, exist_ok=True)
    dubbed_audio_path = create_aligned_audio(
        metadata_file=tts_path,
        output_dir=str(audio_output_dir),
        output_audio=f"dubbed_{target_lang}_audio.wav",
    )
    emit("Dubbed master audio track generated.", step=5, progress=92)
    if cancelled():
        return _cancelled_result(
            run_id,
            video_path=video_path,
            transcript=transcript,
            translated_segments=translated_segments,
            translated_path=translated_path,
            translated_srt_path=translated_srt_path,
            translated_vtt_path=translated_vtt_path,
            source_language=source_language,
            transcript_path=transcript_path,
            tts_path=tts_path,
        )

    # --- Step 6: Final Remixing ---
    emit("Step 6/6: Multiplexing final dubbed video and subtitles...", step=6, progress=95)
    final_video_name = f"final_dubbed_{target_lang}.mp4"
    final_video_path = create_final_video(
        video_path=video_path,
        dubbed_audio_path=dubbed_audio_path,
        output_path=str(audio_output_dir / final_video_name),
        subtitle_path=translated_srt_path if embed_subs else None,
        run_dir=run_dir,
    )
    emit("All steps completed successfully.", step=6, progress=100)

    return {
        "run_id": run_id,
        "cancelled": False,
        "video_path": str(video_path),
        "transcript_path": str(transcript_path),
        "transcript": transcript,
        "source_language": source_language,
        "translated_segments": translated_segments,
        "translated_path": str(translated_path),
        "translated_srt_path": str(translated_srt_path),
        "translated_vtt_path": str(translated_vtt_path),
        "tts_path": str(tts_path),
        "dubbed_audio_path": str(dubbed_audio_path),
        "final_video_path": str(final_video_path),
        "segments_count": len(translated_segments),
    }


def _cancelled_result(run_id: str, **partial) -> dict:
    """Build a partial result dict when the pipeline is cancelled mid-run."""
    partial.setdefault("run_id", run_id)
    partial.setdefault("cancelled", True)
    partial.setdefault("segments_count", 0)
    return partial
