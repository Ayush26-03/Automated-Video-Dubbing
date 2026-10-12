"""Smoke tests for src/pipeline.py.

The full pipeline needs FFmpeg, Whisper, NLLB, Edge-TTS — none of which we
have in the test environment. These tests verify the plumbing (callback
contract, cancellation hook, return shape) and skip the heavy work.
"""

from pathlib import Path
from unittest.mock import patch

from src.pipeline import run_pipeline


def _stub_pipeline(monkeypatch_runner, *, cancelled_callback=None,
                   log_callback=None, return_extra=None):
    """Stub out every pipeline stage with a benign no-op."""
    pass


def test_run_pipeline_smoke_calls_callbacks_with_args(tmp_path):
    """Walk every callback path: log gets called, return dict has expected keys."""
    log_messages = []
    progress_updates = []

    def fake_log(msg, step, progress):
        log_messages.append((msg, step, progress))

    # Stub the heavy stages.
    def fake_download_video(source, output_dir=""):
        f = Path(output_dir) / "fake.mp4"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
        return str(f)

    def fake_transcribe_video(path, **kwargs):
        return {
            "language": "en",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}],
        }

    def fake_translate_segments(segments, **kwargs):
        return [{"start": 0.0, "end": 1.0,
                 "original_text": "Hello",
                 "translated_text": "Hola"}]

    def fake_synthesize_segments(**kwargs):
        return []

    def fake_create_aligned_audio(metadata_file, **kwargs):
        Path(kwargs["output_dir"]).mkdir(parents=True, exist_ok=True)
        out = Path(kwargs["output_dir"]) / kwargs["output_audio"]
        out.write_bytes(b"")
        return str(out)

    def fake_create_final_video(**kwargs):
        out_path = Path(kwargs["output_path"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"")
        return str(out_path)

    # 'translating_segments.json' must exist for downstream assertions
    def fake_save_translated_segments(segs, output_dir=""):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = Path(output_dir) / "translated_segments.json"
        out.write_text("[]", encoding="utf-8")
        return str(out)

    def fake_save_transcript(result, output_dir=""):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = Path(output_dir) / "transcript.json"
        out.write_text("{}", encoding="utf-8")
        return str(out)

    def fake_save_tts_metadata(segs, output_dir=""):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = Path(output_dir) / "tts_segments.json"
        out.write_text("[]", encoding="utf-8")
        return str(out)

    def fake_export_srt(segments, path, text_key="translated_text"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
        return path

    def fake_export_vtt(segments, path, text_key="translated_text"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("WEBVTT\n\n", encoding="utf-8")
        return path

    patches = {
        "src.pipeline.download_video": fake_download_video,
        "src.pipeline.transcribe_video": fake_transcribe_video,
        "src.pipeline.save_transcript": fake_save_transcript,
        "src.pipeline.translate_segments": fake_translate_segments,
        "src.pipeline.save_translated_segments": fake_save_translated_segments,
        "src.pipeline.synthesize_segments": fake_synthesize_segments,
        "src.pipeline.save_tts_metadata": fake_save_tts_metadata,
        "src.pipeline.create_aligned_audio": fake_create_aligned_audio,
        "src.pipeline.create_final_video": fake_create_final_video,
        "src.pipeline.export_srt": fake_export_srt,
        "src.pipeline.export_vtt": fake_export_vtt,
    }
    with __import__("contextlib").ExitStack() as stack:
        for target, fake in patches.items():
            stack.enter_context(patch(target, side_effect=fake))

        result = run_pipeline(
            source_input="ignored.mp4",
            target_lang="es",
            log=fake_log,
            run_dir=tmp_path,
        )

    # Pipeline returned the expected dict shape.
    for key in (
        "run_id", "video_path", "transcript", "translated_segments",
        "translated_srt_path", "translated_vtt_path",
        "dubbed_audio_path", "final_video_path", "segments_count",
    ):
        assert key in result, f"missing {key}"
    assert result["cancelled"] is False
    assert result["segments_count"] == 1
    assert result["source_language"] == "en"

    # Callbacks were invoked at least once.
    assert any(step == 6 for (_, step, _) in log_messages), "step 6 log never emitted"


def test_run_pipeline_respects_is_cancelled(tmp_path):
    """If is_cancelled returns True after step 1, pipeline returns cancelled=True."""

    def fake_download_video(source, output_dir=""):
        f = Path(output_dir) / "fake.mp4"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
        return str(f)

    def fake_transcribe_video(path, **kwargs):
        return {"language": "en",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Hi"}]}

    cancel_calls = {"n": 0}

    def fake_translate_segments(segments, **kwargs):
        cancel_calls["n"] += 1
        return [{"start": 0.0, "end": 1.0,
                 "original_text": "Hi", "translated_text": "Hola"}]

    def fake_export_srt(segments, path, text_key="translated_text"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
        return path

    def fake_export_vtt(segments, path, text_key="translated_text"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("WEBVTT\n\n", encoding="utf-8")
        return path

    def fake_save_transcript(result, output_dir=""):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = Path(output_dir) / "transcript.json"
        out.write_text("{}", encoding="utf-8")
        return str(out)

    def fake_save_translated_segments(segs, output_dir=""):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = Path(output_dir) / "translated_segments.json"
        out.write_text("[]", encoding="utf-8")
        return str(out)

    patches = {
        "src.pipeline.download_video": fake_download_video,
        "src.pipeline.transcribe_video": fake_transcribe_video,
        "src.pipeline.save_transcript": fake_save_transcript,
        "src.pipeline.translate_segments": fake_translate_segments,
        "src.pipeline.save_translated_segments": fake_save_translated_segments,
        "src.pipeline.export_srt": fake_export_srt,
        "src.pipeline.export_vtt": fake_export_vtt,
    }

    def cancelled():
        return True  # Always cancel — pipeline should bail after step 1.

    with __import__("contextlib").ExitStack() as stack:
        for target, fake in patches.items():
            stack.enter_context(patch(target, side_effect=fake))
        result = run_pipeline(
            source_input="ignored.mp4",
            target_lang="es",
            run_dir=tmp_path,
            is_cancelled=cancelled,
        )

    assert result["cancelled"] is True
    assert cancel_calls["n"] == 0, "translation must not run when cancelled after step 1"
