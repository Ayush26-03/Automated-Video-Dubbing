"""Smoke tests for final_remixer — mainly subtitle path sandboxing.

ffmpeg itself is not exercised here (no video files in the test env); we
patch out the subprocess call so we can verify the path validation paths.
"""

import sys
from pathlib import Path
from unittest.mock import patch


import src.final_remixer as fr


def test_subtitle_outside_run_dir_rejected(tmp_path):
    """A subtitle file outside run_dir must be refused."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    other_dir = tmp_path / "outside"
    other_dir.mkdir()
    bad_sub = other_dir / "evil.srt"
    bad_sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    video = run_dir / "in.mp4"
    video.write_bytes(b"")
    audio = run_dir / "audio.wav"
    audio.write_bytes(b"")

    called = {"ffmpeg": False}

    def fake_run(cmd, *args, **kwargs):
        called["ffmpeg"] = True
        class R: returncode = 0; stderr = ""
        return R()

    with patch.object(fr.subprocess, "run", side_effect=fake_run):
        try:
            fr.create_final_video(
                video_path=str(video),
                dubbed_audio_path=str(audio),
                output_path=str(run_dir / "out.mp4"),
                subtitle_path=str(bad_sub),
                run_dir=run_dir,
            )
        except ValueError as e:
            assert "outside the run directory" in str(e)
        else:
            raise AssertionError("expected ValueError for subtitle outside run_dir")

    assert called["ffmpeg"] is False, "ffmpeg must not run when subtitle is rejected"


def test_subtitle_inside_run_dir_accepted(tmp_path):
    """A subtitle file inside run_dir is allowed."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    video = run_dir / "in.mp4"
    video.write_bytes(b"")
    audio = run_dir / "audio.wav"
    audio.write_bytes(b"")
    good_sub = run_dir / "good.srt"
    good_sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    out = run_dir / "out.mp4"

    def fake_run(cmd, *args, **kwargs):
        # Pretend ffmpeg succeeded by creating the output file.
        out.write_bytes(b"")
        class R: returncode = 0; stderr = ""
        return R()

    with patch.object(fr.subprocess, "run", side_effect=fake_run):
        result = fr.create_final_video(
            video_path=str(video),
            dubbed_audio_path=str(audio),
            output_path=str(out),
            subtitle_path=str(good_sub),
            run_dir=run_dir,
        )

    assert Path(result).exists()


def test_ffmpeg_missing_raises_friendly_error(tmp_path):
    """If ffmpeg is not on PATH we should raise FileNotFoundError, not crash."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    video = run_dir / "in.mp4"; video.write_bytes(b"")
    audio = run_dir / "audio.wav"; audio.write_bytes(b"")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("not found")

    with patch.object(fr.subprocess, "run", side_effect=fake_run):
        try:
            fr.create_final_video(
                video_path=str(video),
                dubbed_audio_path=str(audio),
                output_path=str(run_dir / "out.mp4"),
            )
        except FileNotFoundError as e:
            assert "ffmpeg" in str(e).lower()
        else:
            raise AssertionError("expected FileNotFoundError when ffmpeg is missing")
